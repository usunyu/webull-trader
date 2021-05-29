# Generated by Django 3.1.7 on 2021-05-29 00:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('webull_trader', '0010_tradingsettings_swing_position_amount_limit'),
    ]

    operations = [
        migrations.AddField(
            model_name='tradinglog',
            name='trading_hour',
            field=models.PositiveSmallIntegerField(choices=[(0, 'Regular Hour'), (1, 'Before Market Open'), (2, 'After Market Close')], default=0),
        ),
    ]
