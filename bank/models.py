from django.contrib.auth.models import User
from django.db import models


class CurrencyRate(models.Model):
    currency = models.CharField(max_length=3, unique=True)
    rate = models.FloatField()
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.currency}'


class UserAccount(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    secret_key = models.CharField(max_length=50, null=True, blank=True)
    otp_enabled = models.BooleanField(default=False)
    primary_bank_account = models.ForeignKey('BankAccount', on_delete=models.SET_NULL, null=True, blank=True,
                                             related_name='primary_account_of')

    def __str__(self):
        return f'{self.user.username}'

    def bank_accounts_summary(self):
        bank_accounts = self.bank_accounts.all()
        return ', '.join(str(bank_account) for bank_account in bank_accounts)

    bank_accounts_summary.short_description = 'Bank Accounts'


class BankAccount(models.Model):
    user_account = models.ForeignKey(UserAccount, on_delete=models.CASCADE, related_name="bank_accounts")
    balance = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.ForeignKey(CurrencyRate, models.CASCADE)
    account_number = models.CharField(max_length=11, unique=True, null=True, blank=True)

    def __str__(self):
        return f'{self.user_account} - {self.currency}'


class TypeOfTransaction(models.IntegerChoices):
    DEP = 0, "deposit"
    WIT = 1, "withdrawal"
    TRA = 2, "transfer"


class Transaction(models.Model):
    source_account = models.ForeignKey(BankAccount, on_delete=models.CASCADE, related_name="source")
    destination_account = models.ForeignKey(BankAccount, on_delete=models.CASCADE, related_name="destination")
    timestamp = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.ForeignKey(CurrencyRate, on_delete=models.CASCADE)
    type = models.IntegerField(choices=TypeOfTransaction.choices)
    overdraft_fee = models.DecimalField(max_digits=15, decimal_places=2, default=0)
