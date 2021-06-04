# Generated by Django 3.1.7 on 2021-06-04 01:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('webull_trader', '0015_auto_20210603_0018'),
    ]

    operations = [
        migrations.AddField(
            model_name='webullorder',
            name='setup',
            field=models.PositiveSmallIntegerField(choices=[(0, '[Day] First candle new high'), (1, '[Day] Gap and Go'), (2, '[Day] Bull Flag'), (3, '[Day] Reversal'), (4, '[Day] Red to Green'), (5, '[Day] 20 minutes new high'), (6, '[Day] Earning Gap'), (100, '[Swing] 20 days new high'), (101, '[Swing] 55 days new high'), (999, 'Unknown')], default=999),
        ),
        migrations.AlterField(
            model_name='overnightposition',
            name='setup',
            field=models.PositiveSmallIntegerField(choices=[(0, '[Day] First candle new high'), (1, '[Day] Gap and Go'), (2, '[Day] Bull Flag'), (3, '[Day] Reversal'), (4, '[Day] Red to Green'), (5, '[Day] 20 minutes new high'), (6, '[Day] Earning Gap'), (100, '[Swing] 20 days new high'), (101, '[Swing] 55 days new high'), (999, 'Unknown')], default=6),
        ),
        migrations.AlterField(
            model_name='overnighttrade',
            name='setup',
            field=models.PositiveSmallIntegerField(choices=[(0, '[Day] First candle new high'), (1, '[Day] Gap and Go'), (2, '[Day] Bull Flag'), (3, '[Day] Reversal'), (4, '[Day] Red to Green'), (5, '[Day] 20 minutes new high'), (6, '[Day] Earning Gap'), (100, '[Swing] 20 days new high'), (101, '[Swing] 55 days new high'), (999, 'Unknown')], default=6),
        ),
        migrations.AlterField(
            model_name='swingposition',
            name='setup',
            field=models.PositiveSmallIntegerField(choices=[(0, '[Day] First candle new high'), (1, '[Day] Gap and Go'), (2, '[Day] Bull Flag'), (3, '[Day] Reversal'), (4, '[Day] Red to Green'), (5, '[Day] 20 minutes new high'), (6, '[Day] Earning Gap'), (100, '[Swing] 20 days new high'), (101, '[Swing] 55 days new high'), (999, 'Unknown')], default=100),
        ),
        migrations.AlterField(
            model_name='swingtrade',
            name='setup',
            field=models.PositiveSmallIntegerField(choices=[(0, '[Day] First candle new high'), (1, '[Day] Gap and Go'), (2, '[Day] Bull Flag'), (3, '[Day] Reversal'), (4, '[Day] Red to Green'), (5, '[Day] 20 minutes new high'), (6, '[Day] Earning Gap'), (100, '[Swing] 20 days new high'), (101, '[Swing] 55 days new high'), (999, 'Unknown')], default=100),
        ),
        migrations.AlterField(
            model_name='webullordernote',
            name='setup',
            field=models.PositiveSmallIntegerField(choices=[(0, '[Day] First candle new high'), (1, '[Day] Gap and Go'), (2, '[Day] Bull Flag'), (3, '[Day] Reversal'), (4, '[Day] Red to Green'), (5, '[Day] 20 minutes new high'), (6, '[Day] Earning Gap'), (100, '[Swing] 20 days new high'), (101, '[Swing] 55 days new high'), (999, 'Unknown')], default=0),
        ),
    ]
