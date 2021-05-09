# Generated by Django 3.1.7 on 2021-05-09 02:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('old_ross', '0005_webullordernote_setup'),
    ]

    operations = [
        migrations.CreateModel(
            name='HistoricalDayTradePerformance',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('win_rate', models.FloatField()),
                ('profit_loss_ratio', models.FloatField()),
                ('day_profit_loss', models.FloatField()),
                ('trades', models.PositiveIntegerField()),
                ('top_gain_amount', models.FloatField()),
                ('top_gain_symbol', models.CharField(max_length=64)),
                ('top_loss_amount', models.FloatField()),
                ('top_loss_symbol', models.CharField(max_length=64)),
            ],
        ),
    ]
