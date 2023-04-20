from django import forms
from bank.models import BankAccount


class ChangePrimaryBankAccountForm(forms.Form):
    bank_account = forms.ModelChoiceField(queryset=BankAccount.objects.none(), empty_label=None)

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['bank_account'].queryset = BankAccount.objects.filter(user_account__user=user)
