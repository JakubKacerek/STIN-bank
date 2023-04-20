import time

import requests
import schedule as schedule
from django.db import IntegrityError

from bank.models import CurrencyRate


class Currency:
    def __init__(self, country: str, currency: str, amount: int, code: str, rate: float):
        self.country = country
        self.currency = currency
        self.amount = amount
        self.code = code
        self.rate = rate

    def __str__(self) -> str:
        return f'{self.currency} ({self.code})'


def getRates():
    url = 'https://www.cnb.cz/cs/financni-trhy/devizovy-trh/kurzy-devizoveho-trhu/kurzy-devizoveho-trhu/denni_kurz.txt'
    response = requests.get(url)
    rates = []
    for line in response.text.split('\n')[2:-1]:
        data = line.split('|')
        rates.append(Currency(data[0], data[1], int(data[2]), data[3], float(data[4].replace(',', '.'))))
    return tuple(rates)


def saveRates():
    for data in getRates():
        currency = data.code
        rate = data.rate
        try:
            obj, created = CurrencyRate.objects.update_or_create(
                currency=currency,
                defaults={'rate': rate}
            )
        except IntegrityError as e:
            print(f"Error updating or creating CurrencyRate for currency {currency}: {e}")

