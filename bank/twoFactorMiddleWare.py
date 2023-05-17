from django.shortcuts import redirect
from django.urls import reverse


class TwoFactorAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        # Exclude the URLs that don't require 2FA
        exclude_urls = [
            reverse('bank:login'),
            reverse('bank:setup_otp'),
            reverse('bank:verify_otp'),
            reverse('bank:register'),
            reverse('bank:check_otp_setup'),
            reverse('accounts:login'),
            # Add more URLs to exclude as necessary
        ]

        if request.path not in exclude_urls:
            # If user is authenticated
            if request.user.is_authenticated:
                # If user hasn't setup 2FA
                if not request.user.useraccount.otp_enabled:
                    return redirect('bank:setup_otp')
