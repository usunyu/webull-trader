# Generated by Django 3.1.7 on 2021-06-11 06:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('webull_trader', '0020_auto_20210610_1943'),
    ]

    operations = [
        migrations.AddField(
            model_name='tradingsettings',
            name='avg_confirm_amount',
            field=models.FloatField(default=30000),
            preserve_default=False,
        ),
    ]