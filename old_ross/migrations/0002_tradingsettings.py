# Generated by Django 3.1.7 on 2021-05-01 23:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('old_ross', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='TradingSettings',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('paper', models.BooleanField(default=True)),
                ('order_amount_limit', models.FloatField()),
                ('min_surge_amount', models.FloatField()),
                ('min_surge_volume', models.FloatField()),
                ('min_surge_change_ratio', models.FloatField()),
                ('observe_timeout_in_sec', models.IntegerField()),
                ('pending_order_timeout_in_sec', models.IntegerField()),
                ('holding_order_timeout_in_sec', models.IntegerField()),
                ('max_bid_ask_gap_ratio', models.FloatField()),
                ('target_profit_ratio', models.FloatField()),
                ('stop_loss_ratio', models.FloatField()),
                ('refresh_login_interval_in_min', models.IntegerField()),
            ],
        ),
    ]