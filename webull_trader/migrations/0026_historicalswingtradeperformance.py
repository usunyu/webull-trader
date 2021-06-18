# Generated by Django 3.1.7 on 2021-06-18 21:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('webull_trader', '0025_manualtraderequest'),
    ]

    operations = [
        migrations.CreateModel(
            name='HistoricalSwingTradePerformance',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('day_profit_loss', models.FloatField()),
                ('trades', models.PositiveIntegerField()),
                ('total_buy_amount', models.FloatField()),
                ('total_sell_amount', models.FloatField()),
            ],
        ),
    ]
