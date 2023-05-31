import unittest

from django.contrib.auth.models import User
import requests
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User
from .models import UserAccount, CurrencyRate, BankAccount
from bank.forms import ChangePrimaryBankAccountForm, WithdrawalForm
from bank.twoFactorMiddleWare import TwoFactorAuthMiddleware
from bank.views import get_recent_transactions, HomeView, calculate_overdraft_fee, is_valid_amount
from .models import CurrencyRate, UserAccount, BankAccount, Transaction, TypeOfTransaction
import time
from unittest.mock import patch, MagicMock
from django.test import TransactionTestCase

from .utils.cnbCurrencies import Currency, getRates, saveRates


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


class TestCurrency(unittest.TestCase):
    def setUp(self):
        self.currency = Currency("United States", "USD", 100, "usd", 1.0)

    def test_init(self):
        self.assertEqual(self.currency.country, "United States")
        self.assertEqual(self.currency.currency, "USD")
        self.assertEqual(self.currency.amount, 100)
        self.assertEqual(self.currency.code, "usd")
        self.assertEqual(self.currency.rate, 1.0)

    def test_str(self):
        self.assertEqual(str(self.currency), 'USD (usd)')


class TestGetRates(unittest.TestCase):
    @patch('bank.utils.cnbCurrencies.requests.get')
    def test_get_rates(self, mock_get):
        mock_response = mock_get.return_value
        mock_response.text = 'header1\nheader2\nUSA|USD|1|usd|1,234\n'

        rates = getRates()

        self.assertEqual(len(rates), 1)
        self.assertIsInstance(rates[0], Currency)
        self.assertEqual(rates[0].country, 'USA')
        self.assertEqual(rates[0].currency, 'USD')
        self.assertEqual(rates[0].amount, 1)
        self.assertEqual(rates[0].code, 'usd')
        self.assertEqual(rates[0].rate, 1.234)

    @patch('bank.utils.cnbCurrencies.requests.get')
    def test_get_rates_connection_error(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError

        rates = getRates()

        self.assertEqual(rates, tuple())


class MockRate:
    def __init__(self, code, rate):
        self.code = code
        self.rate = rate


def mock_getRates():
    return [MockRate('USD', 1.25), MockRate('CZK', 1)]


class TestSaveRates(TestCase):
    @patch('bank.utils.cnbCurrencies.getRates', side_effect=mock_getRates)
    def test_saveRates(self, mock_get):
        saveRates()

        usd_rate = CurrencyRate.objects.get(currency='USD')
        czk_rate = CurrencyRate.objects.get(currency='CZK')

        self.assertEqual(usd_rate.rate, 1.25)
        self.assertEqual(czk_rate.rate, 1)


class TwoFactorAuthMiddlewareTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_process_view_authenticated_user_without_2fa_setup(self):
        # Create a user without UserAccount
        user = User.objects.create_user(username='pepa', password='842653971lL/')
        UserAccount.objects.create(user=user, otp_enabled=False)  # Create UserAccount object

        # Set up the middleware
        middleware = TwoFactorAuthMiddleware(get_response=None)

        # Create a request to a protected URL
        url = reverse('bank:dashboard')
        request = self.factory.get(url)
        request.user = user

        # Process the view
        response = middleware.process_view(request, view_func=None, view_args=None, view_kwargs=None)

        # Assert that the response is a redirect to the setup_otp URL
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('bank:setup_otp'))

    def test_process_view_authenticated_user_with_2fa_setup(self):
        # Create a user with UserAccount and 2FA setup
        user = User.objects.create_user(username='pepa', password='842653971lL/')
        UserAccount.objects.create(user=user, otp_enabled=True)  # Create UserAccount object

        # Set up the middleware
        middleware = TwoFactorAuthMiddleware(get_response=None)

        # Create a request to a protected URL
        url = reverse('bank:dashboard')
        request = self.factory.get(url)
        request.user = user

        # Process the view
        response = middleware.process_view(request, view_func=None, view_args=None, view_kwargs=None)

        # Assert that the response is not a redirect
        self.assertEqual(response, None)


class TestChangePrimaryBankAccountForm(TestCase):
    def setUp(self):
        self.user = User.objects.create(username='testuser', password='12345')
        self.user_account = UserAccount.objects.create(user=self.user)
        self.currency = CurrencyRate.objects.create(currency='CZK', rate=1.0)  # Create a currency
        self.bank_account = BankAccount.objects.create(user_account=self.user_account, balance=1000,
                                                       currency=self.currency)  # Add balance and currency here

    def test_form(self):
        # Test form without user
        form = ChangePrimaryBankAccountForm()
        self.assertEqual(form.fields['bank_account'].queryset.count(), 0)

        # Test form with user
        form = ChangePrimaryBankAccountForm(user=self.user)
        self.assertEqual(form.fields['bank_account'].queryset.count(), 1)
        self.assertEqual(form.fields['bank_account'].queryset.first(), self.bank_account)

    def tearDown(self):
        self.bank_account.delete()
        self.user_account.delete()
        self.currency.delete()  # Delete currency here
        self.user.delete()


class GetRecentTransactionsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create(username='pepa')
        self.user_account = UserAccount.objects.create(user=self.user)
        self.currency = CurrencyRate.objects.create(currency='CZK', rate=1)
        self.primary_account = BankAccount.objects.create(user_account=self.user_account, balance=1000,
                                                          currency=self.currency)
        self.other_account = BankAccount.objects.create(user_account=self.user_account, balance=1000,
                                                        currency=self.currency)
        self.user_account.primary_bank_account = self.primary_account
        self.user_account.save()

        for i in range(20, 0, -1):  # Reverse the order of transaction creation
            Transaction.objects.create(
                source_account=self.primary_account,
                destination_account=self.other_account,
                amount=10,
                timestamp=timezone.now(),
                currency=self.currency,
                type=TypeOfTransaction.DEP
            )
            time.sleep(0.1)

    def test_get_recent_transactions(self):
        transactions = get_recent_transactions(self.user_account)
        self.assertEqual(len(transactions), 10)  # Ensure we only get 10 transactions
        for i in range(len(transactions) - 1):
            self.assertGreater(transactions[i].timestamp,
                               transactions[i + 1].timestamp)  # Ensure transactions are ordered by timestamp

    def test_get_recent_transactions_no_limit(self):
        transactions = get_recent_transactions(self.user_account, num_transactions=None)
        self.assertEqual(len(transactions), 20)  # Ensure we get all transactions

    def test_get_recent_transactions_empty(self):
        Transaction.objects.all().delete()  # Delete all transactions
        transactions = get_recent_transactions(self.user_account)
        self.assertEqual(list(transactions), [])  # Ensure we get an empty list


class CalculateOverdraftFeeTest(TestCase):
    def setUp(self):
        self.user = User.objects.create(username='testuser')
        self.currency = CurrencyRate.objects.create(currency='USD', rate=1.0)
        self.user_account = UserAccount.objects.create(user=self.user)
        self.bank_account = BankAccount.objects.create(user_account=self.user_account, balance=Decimal('100.00'),
                                                       currency=self.currency)

    def test_calculate_overdraft_fee_positive_balance(self):
        amount = Decimal('50.00')
        overdraft_fee = calculate_overdraft_fee(self.bank_account, amount)
        self.assertEqual(overdraft_fee, Decimal('0.00'))

    def test_calculate_overdraft_fee_zero_balance(self):
        amount = Decimal('100.00')
        overdraft_fee = calculate_overdraft_fee(self.bank_account, amount)
        self.assertEqual(overdraft_fee, Decimal('0.00'))

    def test_calculate_overdraft_fee_negative_balance(self):
        amount = Decimal('150.00')
        overdraft_fee = calculate_overdraft_fee(self.bank_account, amount)
        self.assertEqual(overdraft_fee, Decimal('5.00'))


class IsValidAmountTest(TestCase):
    def setUp(self):
        self.user = User.objects.create(username='testuser')
        self.currency = CurrencyRate.objects.create(currency='USD', rate=1.0)
        self.user_account = UserAccount.objects.create(user=self.user)
        self.bank_account = BankAccount.objects.create(user_account=self.user_account, balance=Decimal('100.00'),
                                                       currency=self.currency)

    def test_is_valid_amount_exact_balance(self):
        amount = Decimal('100.00')
        is_valid = is_valid_amount(self.bank_account, amount)
        self.assertTrue(is_valid)

    def test_is_valid_amount_within_overdraft_limit(self):
        amount = Decimal('110.00')
        is_valid = is_valid_amount(self.bank_account, amount)
        self.assertTrue(is_valid)

    def test_is_valid_amount_exceeds_overdraft_limit(self):
        amount = Decimal('111.00')
        is_valid = is_valid_amount(self.bank_account, amount)
        self.assertFalse(is_valid)

    def test_is_valid_amount_negative_amount(self):
        amount = Decimal('-10.00')
        is_valid = is_valid_amount(self.bank_account, amount)
        self.assertFalse(is_valid)


class TypeOfTransactionTest(TestCase):
    def test_deposit(self):
        self.assertEqual(TypeOfTransaction.DEP, 0)

    def test_withdrawal(self):
        self.assertEqual(TypeOfTransaction.WIT, 1)

    def test_transfer(self):
        self.assertEqual(TypeOfTransaction.TRA, 2)


class WithdrawalFormTest(TestCase):
    def setUp(self):
        self.currency = CurrencyRate.objects.create(currency='USD', rate=1.0)

    def test_withdrawal_form_valid(self):
        form_data = {'amount': Decimal('100.00'), 'currency': self.currency.pk}
        form = WithdrawalForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_withdrawal_form_amount_invalid(self):
        form_data = {'amount': 'invalid amount', 'currency': self.currency.pk}
        form = WithdrawalForm(data=form_data)
        self.assertFalse(form.is_valid())

    def test_withdrawal_form_currency_invalid(self):
        form_data = {'amount': Decimal('100.00'), 'currency': 'invalid currency'}
        form = WithdrawalForm(data=form_data)
        self.assertFalse(form.is_valid())


if __name__ == '__main__':
    unittest.main()
