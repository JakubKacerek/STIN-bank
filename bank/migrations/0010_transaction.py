# Generated by Django 4.2 on 2023-04-20 17:21

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('bank', '0009_alter_useraccount_primary_bank_account'),
    ]

    operations = [
        migrations.CreateModel(
            name='Transaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=15)),
                ('type', models.IntegerField(choices=[(0, 'deposit'), (1, 'withdrawal'), (2, 'transfer')])),
                ('currency', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='bank.bankaccount')),
                ('destination_account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='destination', to='bank.bankaccount')),
                ('source_account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='source', to='bank.bankaccount')),
            ],
        ),
    ]
