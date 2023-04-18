from django.contrib import admin

from bank.models import BankAccount


# Register your models here.

@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ('user','balance')