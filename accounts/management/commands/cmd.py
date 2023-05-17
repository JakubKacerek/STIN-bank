from django.core.management import BaseCommand

from bank.utils.cnbCurrencies import getRates


class Command(BaseCommand):
    def handle(self, *args, **options):
        getRates()