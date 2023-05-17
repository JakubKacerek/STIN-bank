# Generated by Django 4.2 on 2023-04-19 08:35

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('bank', '0005_remove_useraccount_balance_bankaccount_currency'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='bankaccount',
            name='user',
        ),
        migrations.RemoveField(
            model_name='useraccount',
            name='account',
        ),
        migrations.AddField(
            model_name='bankaccount',
            name='user_account',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='bank_accounts', to='bank.useraccount'),
        ),
        migrations.AlterField(
            model_name='useraccount',
            name='user',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
    ]
