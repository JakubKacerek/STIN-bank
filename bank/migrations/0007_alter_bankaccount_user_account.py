# Generated by Django 4.2 on 2023-04-19 08:38

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('bank', '0006_remove_bankaccount_user_remove_useraccount_account_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='bankaccount',
            name='user_account',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bank_accounts', to='bank.useraccount'),
        ),
    ]
