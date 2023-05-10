from django import forms
from bank.models import BankAccount


class ChangePrimaryBankAccountForm(forms.Form):
    bank_account = forms.ModelChoiceField(queryset=BankAccount.objects.none(), empty_label=None)

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['bank_account'].queryset = BankAccount.objects.filter(user_account__user=user)


class TransactionForm(forms.Form):
    target_account = forms.ModelChoiceField(queryset=BankAccount.objects.none(), empty_label=None)
    amount = forms.DecimalField(max_digits=15, decimal_places=2)

    def __init__(self, *args, target_accounts=None, **kwargs):
        super().__init__(*args, **kwargs)
        if target_accounts:
            self.fields['target_account'].queryset = target_accounts


class WithdrawalForm(forms.Form):
    amount = forms.DecimalField(max_digits=15, decimal_places=2)


class RechargeForm(forms.Form):
    amount = forms.DecimalField(max_digits=15, decimal_places=2)



