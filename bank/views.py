from django.shortcuts import render

from bank.models import BankAccount


def home(request):
    return render(request, 'index.html',{
        'balance': BankAccount.objects.get(pk=request.user.pk)
    })