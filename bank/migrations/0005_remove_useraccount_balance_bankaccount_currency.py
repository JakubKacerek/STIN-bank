# Generated by Django 4.2 on 2023-04-19 05:59

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('bank', '0004_remove_useraccount_currency'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='useraccount',
            name='balance',
        ),
        migrations.AddField(
            model_name='bankaccount',
            name='currency',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='bank.currencyrate'),
            preserve_default=False,
        ),
    ]
