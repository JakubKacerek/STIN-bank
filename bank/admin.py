from django.contrib import admin

from bank.models import BankAccount, CurrencyRate, UserAccount, Transaction


# Register your models here.

@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ('user_account','account_number', 'balance', 'currency')


@admin.register(CurrencyRate)
class CurrencyRateAdmin(admin.ModelAdmin):
    list_display = ('currency', 'rate', 'updated_at')


@admin.register(UserAccount)
class UserAccountAdmin(admin.ModelAdmin):
    list_display = ('user', 'otp_enabled', 'bank_accounts_summary', 'primary_bank_account')


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'amount', 'currency', 'type', 'source_account', 'destination_account')


