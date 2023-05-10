from django.urls import path, include
from .views import HomeView, ChangePrimaryBankAccountView
from . import views

app_name = 'bank'

urlpatterns = [
    path('', HomeView.as_view(), name='dashboard'),
    path('change_primary_bank_account/', views.ChangePrimaryBankAccountView.as_view(),
         name='change_primary_bank_account'),
    path('transaction/', views.TransactionView.as_view(), name='transaction'),
    path('withdraw/', views.WithdrawalView.as_view(), name='withdraw'),
    path('recharge/', views.RechargeView.as_view(), name='recharge'),
]
