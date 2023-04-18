from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from bank.models import BankAccount
from bank.utils.cnbCurrencies import getRates


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = 'index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['balance'] = BankAccount.objects.get(user=self.request.user)
        context['rates'] = getRates()
        return context

