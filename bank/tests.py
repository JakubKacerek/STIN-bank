import unittest
from decimal import Decimal

from django.contrib import auth
from django.contrib.auth import get_user_model
import requests
from django.test import RequestFactory
from django.urls import reverse
from django.test import TestCase, Client
from django.test import TestCase
from django.contrib.auth.models import User
from bank.forms import ChangePrimaryBankAccountForm, WithdrawalForm, RechargeForm, NewUserForm
from bank.twoFactorMiddleWare import TwoFactorAuthMiddleware
from bank.views import is_valid_amount, calculate_overdraft_fee
from .models import CurrencyRate, UserAccount, BankAccount, TypeOfTransaction
import time
from unittest.mock import patch

from .utils.cnbCurrencies import Currency, getRates


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


class TypeOfTransactionTest(TestCase):
    def test_deposit(self):
        self.assertEqual(TypeOfTransaction.DEP, 0)

    def test_withdrawal(self):
        self.assertEqual(TypeOfTransaction.WIT, 1)

    def test_transfer(self):
        self.assertEqual(TypeOfTransaction.TRA, 2)


class BankAccountModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create(username='testuser')
        self.currency = CurrencyRate.objects.create(currency='USD', rate=1.0)
        self.user_account = UserAccount.objects.create(user=self.user)
        self.bank_account = BankAccount.objects.create(user_account=self.user_account, balance=Decimal('100.00'),
                                                       currency=self.currency)

    def test_str_representation(self):
        self.assertEqual(str(self.bank_account), f'{self.user_account} - {self.currency}')

    def test_negative_balance(self):
        self.bank_account.balance = Decimal('-10.00')


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


class RechargeFormTest(TestCase):
    def setUp(self):
        self.currency = CurrencyRate.objects.create(currency='USD', rate=1.0)

    def test_recharge_form(self):
        form = RechargeForm({
            'amount': '100.00',
            'currency': self.currency.pk,  # Assuming you have currency instance available here
        })

        self.assertTrue(form.is_valid())


class NewUserFormTest(TestCase):
    def test_new_user_form(self):
        form = NewUserForm({
            'username': 'testuser',
            'email': 'testuser@example.com',
            'password1': 'testpassword123',
            'password2': 'testpassword123',
        })

        self.assertTrue(form.is_valid())
        user = form.save()

        self.assertEqual(get_user_model().objects.count(), 1)
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, 'testuser@example.com')
        self.assertTrue(user.check_password('testpassword123'))
        self.assertIsNotNone(user.useraccount)


class BankLoginViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.login_url = reverse('accounts:login')
        self.UserModel = get_user_model()
        self.test_username = 'testuser'
        self.test_password = 'testpassword'
        self.test_user = self.UserModel.objects.create_user(username=self.test_username, password=self.test_password)

    def test_valid_login(self):
        response = self.client.post(self.login_url, {'username': self.test_username, 'password': self.test_password})
        user = auth.get_user(self.client)
        self.assertTrue(user.is_authenticated)
        self.assertEqual(response.status_code, 302)  # Successful login should redirect


if __name__ == '__main__':
    unittest.main()
