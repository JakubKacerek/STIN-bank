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
from django_otp import login as otp_login
from django_otp.views import LoginView
from pyotp import TOTP

from bank.forms import ChangePrimaryBankAccountForm, TransactionForm, WithdrawalForm, RechargeForm, NewUserForm
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

        context['rates'] = getRates()
        saveRates()

        context['transactions'] = get_recent_transactions(user_account)

        return context


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
            amount = form.cleaned_data['amount']
            source_account = UserAccount.objects.get(user=request.user).primary_bank_account
            if source_account.balance < amount:
                return JsonResponse({"error": "Insufficient funds."})
            else:
                source_currency_rate = CurrencyRate.objects.get(currency=source_account.currency.currency)
                target_currency_rate = CurrencyRate.objects.get(currency=target_account.currency.currency)

                amount_in_czk = amount * Decimal(source_currency_rate.rate)
                amount_in_target_currency = amount_in_czk / Decimal(target_currency_rate.rate)

                source_account.balance -= amount
                source_account.save()
                target_account.balance += amount_in_target_currency
                target_account.save()

                transaction = Transaction(
                    source_account=source_account,
                    destination_account=target_account,
                    amount=amount,
                    currency=source_account.currency,  # Change this line
                    type=TypeOfTransaction.TRA
                )
                transaction.save()

                return JsonResponse({"success": "Transaction complete."})
        else:
            return JsonResponse({"error": "Failed to complete the transaction. Please try again."})


class WithdrawalView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        form = WithdrawalForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            user_account = UserAccount.objects.get(user=request.user)
            source_account = user_account.primary_bank_account

            if source_account.balance < amount:
                return JsonResponse({"error": "Insufficient funds."})
            else:
                source_account.balance -= amount
                source_account.save()

                transaction = Transaction(
                    source_account=source_account,
                    destination_account=source_account,
                    amount=amount,
                    currency=source_account.currency,
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
            amount = form.cleaned_data['amount']
            user_account = UserAccount.objects.get(user=request.user)
            source_account = user_account.primary_bank_account

            source_account.balance += amount
            source_account.save()

            transaction = Transaction(
                source_account=source_account,
                destination_account=source_account,
                amount=amount,
                currency=source_account.currency,
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

