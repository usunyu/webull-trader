# Generated by Django 3.1.7 on 2021-09-24 23:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('webull_trader', '0038_auto_20210920_2216'),
    ]

    operations = [
        migrations.AddField(
            model_name='webullaccountstatistics',
            name='min_usable_cash',
            field=models.FloatField(default=30000.0),
        ),
    ]
