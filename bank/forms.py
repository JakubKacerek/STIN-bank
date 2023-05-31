import random

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from bank.models import BankAccount, UserAccount, CurrencyRate


class ChangePrimaryBankAccountForm(forms.Form):
    bank_account = forms.ModelChoiceField(queryset=BankAccount.objects.none(), empty_label=None)

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['bank_account'].queryset = BankAccount.objects.filter(user_account__user=user)


class TransactionForm(forms.Form):
    target_account = forms.ModelChoiceField(queryset=BankAccount.objects.none(), empty_label=None)
    amount = forms.DecimalField(max_digits=15, decimal_places=2)
    currency = forms.ModelChoiceField(queryset=CurrencyRate.objects.all())

    def __init__(self, *args, target_accounts=None, **kwargs):
        super().__init__(*args, **kwargs)
        if target_accounts:
            self.fields['target_account'].queryset = target_accounts


class WithdrawalForm(forms.Form):
    amount = forms.DecimalField(max_digits=15, decimal_places=2)
    currency = forms.ModelChoiceField(queryset=CurrencyRate.objects.all())


class RechargeForm(forms.Form):
    amount = forms.DecimalField(max_digits=15, decimal_places=2)
    currency = forms.ModelChoiceField(queryset=CurrencyRate.objects.all())


class NewUserForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def save(self, commit=True):
        user = super(NewUserForm, self).save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            UserAccount.objects.create(user=user)
        return user


class BankAccountForm(forms.ModelForm):
    class Meta:
        model = BankAccount
        fields = ('currency',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['currency'].queryset = CurrencyRate.objects.all()

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.balance = self.cleaned_data.get('starting_amount')
        instance.account_number = self.generate_account_number()
        if commit:
            instance.save()
        return instance

    @staticmethod
    def generate_account_number():
        while True:
            number = random.randint(10 ** 10, 10 ** 11 - 1)
            if not BankAccount.objects.filter(account_number=number).exists():
                return number

