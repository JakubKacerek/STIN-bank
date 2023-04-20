from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView

from bank.forms import ChangePrimaryBankAccountForm
from bank.models import BankAccount, UserAccount
from bank.utils.cnbCurrencies import getRates, saveRates


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = 'index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
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

