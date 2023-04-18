import time

import requests
import schedule as schedule


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
        # země|měna|množství|kód|kurz
        data = line.split('|')
        rates.append(Currency(data[0], data[1], int(data[2]), data[3], float(data[4].replace(',', '.'))))
    return tuple(rates)
