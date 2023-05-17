from celery import shared_task
from .models import CurrencyRate
from .views import getRates

@shared_task
def update_currency_rates():
    rates = getRates()
    for rate in rates:
        currency, created = CurrencyRate.objects.get_or_create(name=rate.name)
        currency.rate = rate.rate
        currency.save()