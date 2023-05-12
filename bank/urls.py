from django.urls import path, include
from .views import HomeView, CustomLoginView, RegisterUserView
from . import views

app_name = 'bank'

urlpatterns = [
    path('login/', CustomLoginView.as_view(), name='login'),
    path('', HomeView.as_view(), name='dashboard'),
    path('change_primary_bank_account/', views.ChangePrimaryBankAccountView.as_view(),
         name='change_primary_bank_account'),
    path('transaction/', views.TransactionView.as_view(), name='transaction'),
    path('withdraw/', views.WithdrawalView.as_view(), name='withdraw'),
    path('recharge/', views.RechargeView.as_view(), name='recharge'),
    path('setup_otp/', views.setup_otp, name='setup_otp'),
    path('verify_otp/', views.verify_otp, name='verify_otp'),
    path('register/', RegisterUserView.as_view(), name='register'),
    path('check_otp_setup/', views.check_otp_setup, name='check_otp_setup'),
]
