from django.contrib.auth.models import User
from django.test import TestCase
from .models import CurrencyRate, UserAccount, BankAccount
import time

from .utils.cnbCurrencies import Currency


class CurrencyRateModelTest(TestCase):
    def setUp(self):
        self.currency = 'USD'
        self.rate = 1.2
        self.currency_rate = CurrencyRate.objects.create(currency=self.currency, rate=self.rate)

    def test_model_creation(self):
        """Test the CurrencyRate model creation"""
        self.assertEqual(self.currency_rate.currency, self.currency)
        self.assertEqual(self.currency_rate.rate, self.rate)

    def test_auto_updated_at(self):
        """Test the auto update of updated_at field"""
        old_updated_at = self.currency_rate.updated_at
        time.sleep(1)  # wait for 1 second
        self.currency_rate.rate = 1.3
        self.currency_rate.save()
        self.currency_rate.refresh_from_db()  # refresh object from database
        self.assertNotEqual(self.currency_rate.updated_at, old_updated_at)

    def test_string_representation(self):
        """Test the string representation of the model"""
        self.assertEqual(str(self.currency_rate), self.currency)


class UserAccountModelTest(TestCase):
    counter = 0

    def setUp(self):
        UserAccountModelTest.counter += 1
        self.user = User.objects.create_user(username=f'testuser{UserAccountModelTest.counter}', password='12345')
        self.user_account = UserAccount.objects.create(user=self.user)
        self.currency_rate = CurrencyRate.objects.create(currency='USD', rate=1.0)


        self.bank_account = BankAccount.objects.create(
            user_account=self.user_account,
            balance=100.00,
            currency=self.currency_rate,
            account_number='12345678901'
        )

        self.user_account = UserAccount.objects.create(
            user=self.user,
            secret_key="secret",
            otp_enabled=True,
            primary_bank_account=self.bank_account
        )

    def test_user_account_creation(self):
        self.assertIsInstance(self.user_account, UserAccount)
        self.assertEqual(self.user_account.user.username, 'testuser')
        self.assertEqual(self.user_account.secret_key, 'secret')
        self.assertEqual(self.user_account.otp_enabled, True)
        self.assertEqual(self.user_account.primary_bank_account, self.bank_account)

    def test_user_account_update(self):
        self.user_account.secret_key = 'new_secret'
        self.user_account.otp_enabled = False
        self.user_account.save()

        self.assertEqual(self.user_account.secret_key, 'new_secret')
        self.assertEqual(self.user_account.otp_enabled, False)


from django.test import TestCase
from django.contrib.auth.models import User
from .models import UserAccount, CurrencyRate, BankAccount


class BankAccountModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.user_account = UserAccount.objects.create(user=self.user)
        self.currency_rate = CurrencyRate.objects.create(currency='USD', rate=1.0)

        self.bank_account = BankAccount.objects.create(
            user_account=self.user_account,
            balance=100.00,
            currency=self.currency_rate,
            account_number='12345678901'
        )

    def test_something(self):
        self.assertEqual(self.user_account.user.username, 'testuser')
        self.assertEqual(self.currency_rate.currency, 'USD')


def test_bank_account_creation(self):
    bank_account = BankAccount.objects.get(id=1)
    self.assertEqual(bank_account.user_account.user.username, 'testuser')
    self.assertEqual(bank_account.balance, 100.00)
    self.assertEqual(bank_account.currency.currency, 'USD')
    self.assertEqual(bank_account.account_number, '12345678901')


def test_balance_label(self):
    bank_account = BankAccount.objects.get(id=1)
    field_label = bank_account._meta.get_field('balance').verbose_name
    self.assertEqual(field_label, 'balance')


def test_account_number_max_length(self):
    bank_account = BankAccount.objects.get(id=1)
    max_length = bank_account._meta.get_field('account_number').max_length
    self.assertEqual(max_length, 11)


def test_object_name_is_user_account_currency(self):
    bank_account = BankAccount.objects.get(id=1)
    expected_object_name = f'{bank_account.user_account} - {bank_account.currency}'
    self.assertEqual(expected_object_name, str(bank_account))


def test_balance_value(self):
    bank_account = BankAccount.objects.get(id=1)
    self.assertEqual(bank_account.balance, 100.00)
