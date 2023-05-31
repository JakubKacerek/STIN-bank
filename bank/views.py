from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import authenticate
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import TemplateView, CreateView
import pyotp
from django.contrib.auth import login as auth_login
from django_otp.views import LoginView
from pyotp import TOTP
from bank.forms import ChangePrimaryBankAccountForm, TransactionForm, WithdrawalForm, RechargeForm, NewUserForm, \
    BankAccountForm
from bank.models import BankAccount, UserAccount, TypeOfTransaction, Transaction, CurrencyRate
from bank.utils.cnbCurrencies import getRates, saveRates
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
import qrcode
import io
import base64


def get_recent_transactions(user_account, num_transactions=10):
    primary_account = user_account.primary_bank_account
    transactions = Transaction.objects.filter(
        source_account=primary_account
    ).union(
        Transaction.objects.filter(destination_account=primary_account)
    ).order_by('-timestamp')[:num_transactions]  # Change this line
    return transactions


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = "index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_account = UserAccount.objects.get(user=self.request.user)
        target_accounts = BankAccount.objects.exclude(user_account=user_account)

        # Generate a secret key if the user doesn't have one yet
        if not user_account.secret_key:
            user_account.secret_key = pyotp.random_base32()
            user_account.save()

        context['form_tr'] = TransactionForm(target_accounts=target_accounts)
        context['form_withdrawal'] = WithdrawalForm()
        context['form_recharge'] = RechargeForm()
        bank_accounts = BankAccount.objects.filter(user_account__user=self.request.user)

        if bank_accounts.exists():
            context['bank_accounts'] = bank_accounts
        else:
            context['bank_accounts'] = None
        try:
            context['account'] = UserAccount.objects.get(user=self.request.user).primary_bank_account
        except ObjectDoesNotExist:
            context['account'] = None

        form = ChangePrimaryBankAccountForm()
        form.fields['bank_account'].choices = [(account.id, f'{account.user_account} - {account.currency}') for account
                                               in bank_accounts]
        context['form'] = form

        # Add BankAccountForm to the context
        context['form_bank_account'] = BankAccountForm()

        context['rates'] = getRates()
        saveRates()

        context['transactions'] = get_recent_transactions(user_account)

        return context

    def post(self, request, *args, **kwargs):
        form = BankAccountForm(request.POST)
        if form.is_valid():
            currency = form.cleaned_data['currency']
            user_account = request.user.useraccount
            if BankAccount.objects.filter(user_account=user_account, currency=currency).exists():
                messages.error(request, 'A bank account with this currency already exists.')
                return self.get(request, *args, **kwargs)
            else:
                bank_account = form.save(commit=False)
                bank_account.user_account = user_account
                bank_account.balance = 0  # Set the initial balance to 0
                bank_account.save()
                messages.success(request, 'Bank account created successfully.')
                return redirect('bank:dashboard')
        else:
            # If the form isn't valid, still return the page with the same context data
            return self.get(request, *args, **kwargs)


class ChangePrimaryBankAccountView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        form = ChangePrimaryBankAccountForm(request.POST, user=request.user)
        if form.is_valid():
            bank_account_id = form.cleaned_data['bank_account'].id
            user_account = UserAccount.objects.get(user=self.request.user)
            user_account.primary_bank_account_id = bank_account_id
            user_account.save()
        else:
            messages.error(request, 'Failed to change the primary bank account. Please try again.')

        return HttpResponseRedirect(reverse('bank:dashboard'))


def is_valid_amount(account, amount):
    return Decimal('0') <= amount <= account.balance + account.balance * Decimal('0.1')


def calculate_overdraft_fee(account, amount):
    return max(Decimal('0'), amount - account.balance) * Decimal('0.1')


class TransactionView(LoginRequiredMixin, TemplateView):
    template_name = "transaction.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_account = UserAccount.objects.get(user=self.request.user)
        context['form'] = TransactionForm(user=user_account)
        return context

    def post(self, request, *args, **kwargs):
        user_account = UserAccount.objects.get(user=request.user)
        target_accounts = BankAccount.objects.exclude(user_account=user_account)
        form = TransactionForm(request.POST, target_accounts=target_accounts)

        if form.is_valid():
            target_account = form.cleaned_data['target_account']
            amount_in_chosen_currency = form.cleaned_data['amount']
            chosen_currency = form.cleaned_data['currency']

            source_account_in_chosen_currency = BankAccount.objects.filter(user_account=user_account,
                                                                           currency=chosen_currency).first()

            if source_account_in_chosen_currency and source_account_in_chosen_currency.balance >= amount_in_chosen_currency:
                source_account = source_account_in_chosen_currency
                amount_to_deduct = amount_in_chosen_currency
            else:
                source_account = user_account.primary_bank_account

                source_currency_rate = CurrencyRate.objects.get(currency=source_account.currency.currency)
                chosen_currency_rate = CurrencyRate.objects.get(currency=chosen_currency.currency)

                amount_in_czk = amount_in_chosen_currency * Decimal(chosen_currency_rate.rate)
                amount_to_deduct = amount_in_czk / Decimal(source_currency_rate.rate)

                if not is_valid_amount(source_account, amount_to_deduct):
                    return JsonResponse({"error": "Insufficient funds."})

            overdraft_fee = calculate_overdraft_fee(source_account, amount_to_deduct)

            source_account.balance -= amount_to_deduct + overdraft_fee
            source_account.save()

            target_account.balance += amount_in_chosen_currency
            target_account.save()

            transaction = Transaction(
                source_account=source_account,
                destination_account=target_account,
                amount=amount_in_chosen_currency,
                currency=chosen_currency,
                type=TypeOfTransaction.TRA,
                overdraft_fee=overdraft_fee
            )
            transaction.save()

            return JsonResponse({"success": "Transaction complete."})

        else:
            return JsonResponse({"error": "Failed to complete the transaction. Please try again."})


class WithdrawalView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        form = WithdrawalForm(request.POST)
        if form.is_valid():
            amount_in_chosen_currency = form.cleaned_data['amount']
            chosen_currency = form.cleaned_data['currency']
            user_account = UserAccount.objects.get(user=request.user)
            source_account = user_account.primary_bank_account

            chosen_currency_rate = CurrencyRate.objects.get(currency=chosen_currency.currency)
            source_currency_rate = CurrencyRate.objects.get(currency=source_account.currency.currency)

            amount_in_czk = amount_in_chosen_currency * Decimal(chosen_currency_rate.rate)
            amount_to_deduct = amount_in_czk / Decimal(source_currency_rate.rate)

            if source_account.balance < amount_to_deduct:
                return JsonResponse({"error": "Insufficient funds."})
            else:
                source_account.balance -= amount_to_deduct
                source_account.save()

                transaction = Transaction(
                    source_account=source_account,
                    destination_account=source_account,
                    amount=amount_in_chosen_currency,
                    currency=chosen_currency,
                    type=TypeOfTransaction.WIT
                )
                transaction.save()
        else:
            return JsonResponse({"error": "Failed to complete the withdrawal. Please try again."})
        return JsonResponse({"success": "Withdrawal was successful."})


class RechargeView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        form = RechargeForm(request.POST)
        if form.is_valid():
            amount_in_chosen_currency = form.cleaned_data['amount']
            chosen_currency = form.cleaned_data['currency']
            user_account = UserAccount.objects.get(user=request.user)
            source_account = user_account.primary_bank_account

            chosen_currency_rate = CurrencyRate.objects.get(currency=chosen_currency.currency)
            source_currency_rate = CurrencyRate.objects.get(currency=source_account.currency.currency)

            amount_in_czk = amount_in_chosen_currency * Decimal(chosen_currency_rate.rate)
            amount_to_add = amount_in_czk / Decimal(source_currency_rate.rate)

            source_account.balance += amount_to_add
            source_account.save()

            transaction = Transaction(
                source_account=source_account,
                destination_account=source_account,
                amount=amount_in_chosen_currency,
                currency=chosen_currency,
                type=TypeOfTransaction.DEP
            )
            transaction.save()

            return JsonResponse({"success": "Recharge successful."})
        else:
            return JsonResponse({"error": "Failed to complete the recharge. Please try again."})


class CustomLoginView(LoginView):
    @property
    def authentication_form(self):
        """
        Return the default authentication form, bypassing the OTP check.
        """
        return self.form_class

    def form_valid(self, form):
        """If the form is valid, redirect to the supplied URL."""
        username = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password')
        user = authenticate(self.request, username=username, password=password)

        if user is not None:
            auth_login(self.request, user)
            if not user.useraccount.secret_key:
                # Generate a new secret key and save it to the user's account
                secret_key = pyotp.random_base32()
                user.useraccount.secret_key = secret_key
                user.useraccount.save()

            if user.useraccount.otp_enabled:
                return redirect('bank:verify_otp')
            else:
                return redirect('bank:setup_otp')
        else:
            return self.form_invalid(form)


@login_required
def setup_otp(request):
    if request.method == 'POST':
        otp_attempt = request.POST.get('otp')
        otp = pyotp.TOTP(request.user.useraccount.secret_key)
        if otp.verify(otp_attempt):
            request.user.useraccount.otp_enabled = True
            request.user.useraccount.save()
            messages.success(request, '2FA is set up successfully.')
            return redirect('bank:dashboard')
        else:
            messages.error(request, 'Invalid OTP. Please try again.')
            return redirect('bank:setup_otp')
    else:
        # Generate provisioning URI for use with the OTP authenticator app:
        otp_auth_url = pyotp.totp.TOTP(request.user.useraccount.secret_key).provisioning_uri(
            name=request.user.email,
            issuer_name='YourAppName'  # your app name
        )

        # Generate QR code
        qr_img = qrcode.make(otp_auth_url)
        img = io.BytesIO()

        # Save the qr_img (which is already a PIL Image object) directly as PNG
        qr_img.save(img, 'PNG')

        img.seek(0)
        img_b64 = base64.b64encode(img.read()).decode()

        context = {'qr_code': img_b64}

        return render(request, 'registration/setup_otp.html', context)


@login_required
def verify_otp(request):
    if request.method == 'POST':
        otp_attempt = request.POST.get('otp')
        otp = TOTP(request.user.useraccount.secret_key)

        if otp.verify(otp_attempt):
            return redirect('bank:dashboard')
        else:
            return redirect('accounts:login')

    return render(request, 'registration/verify_otp.html')


class RegisterUserView(CreateView):
    form_class = NewUserForm
    success_url = reverse_lazy('bank:login')
    template_name = 'registration/registration.html'


@login_required
def check_otp_setup(request):
    if request.user.useraccount.otp_enabled:
        return redirect('bank:verify_otp')
    else:
        return redirect('bank:setup_otp')


@login_required
def create_bank_account(request):
    if request.method == 'POST':
        form = BankAccountForm(request.POST)
        if form.is_valid():
            bank_account = form.save(commit=False)
            bank_account.user = request.user
            bank_account.save()
            return redirect('bank:dashboard')
    else:
        form = BankAccountForm()
    return render(request, 'bank/create_bank_account.html', {'form': form})
