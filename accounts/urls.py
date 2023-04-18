from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path

from accounts.views import BankLoginView

app_name = 'accounts'

urlpatterns = [
    path("login/", BankLoginView.as_view(), name="login"),
    path('logout/', LogoutView.as_view(), name='logout')
]