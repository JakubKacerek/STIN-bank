# Generated by Django 4.2 on 2023-04-20 08:59

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('bank', '0007_alter_bankaccount_user_account'),
    ]

    operations = [
        migrations.AddField(
            model_name='useraccount',
            name='primary_bank_account',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='primary_account_of', to='bank.bankaccount'),
        ),
    ]