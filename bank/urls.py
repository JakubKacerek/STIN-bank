from django.urls import path, include
from .views import HomeView, ChangePrimaryBankAccountView
from . import views

app_name = 'bank'

urlpatterns = [
    path('', HomeView.as_view(), name='dashboard'),
    path('change_primary_bank_account/', views.ChangePrimaryBankAccountView.as_view(),
         name='change_primary_bank_account'),
]
