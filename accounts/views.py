from django.contrib import messages
from django.contrib.auth.views import LoginView
from django.shortcuts import render

# Create your views here.

class BankLoginView(LoginView):
    template_name = 'registration/login.html'

    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def form_invalid(self, form):
        messages.error(self.request, 'Invalid username or password')
        return super().form_invalid(form)





