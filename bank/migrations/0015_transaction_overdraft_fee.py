# Generated by Django 4.2 on 2023-05-30 08:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bank', '0014_bankaccount_account_number'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='overdraft_fee',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=15),
        ),
    ]
