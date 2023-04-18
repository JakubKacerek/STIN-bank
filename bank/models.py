from django.contrib.auth.models import User
from django.db import models


class BankAccount(models.Model):
    balance = models.DecimalField(max_digits=15, decimal_places=2)
    user = models.ForeignKey(User, models.CASCADE)

    def __str__(self):
        return f'{self.user} account - {self.balance}'


class CurrencyRate(models.Model):
    currency = models.CharField(max_length=3, unique=True)
    rate = models.FloatField()
    updated_at = models.DateTimeField(auto_now=True)
