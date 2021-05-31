# Generated by Django 3.1.7 on 2021-05-31 17:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('webull_trader', '0012_auto_20210530_1610'),
    ]

    operations = [
        migrations.CreateModel(
            name='EarningCalendar',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('symbol', models.CharField(max_length=64)),
                ('earning_date', models.DateField()),
                ('earning_time', models.CharField(max_length=32)),
                ('eps', models.FloatField(blank=True, default=None, null=True)),
                ('eps_estimated', models.FloatField(blank=True, default=None, null=True)),
                ('revenue', models.FloatField(default=0)),
                ('revenue_estimated', models.FloatField(default=0)),
                ('price', models.FloatField()),
                ('change', models.FloatField()),
                ('change_percentage', models.FloatField()),
                ('year_high', models.FloatField()),
                ('year_low', models.FloatField()),
                ('market_value', models.FloatField()),
                ('avg_price_50d', models.FloatField()),
                ('avg_price_200d', models.FloatField()),
                ('volume', models.FloatField()),
                ('avg_volume', models.FloatField()),
                ('exchange', models.CharField(max_length=64)),
                ('outstanding_shares', models.FloatField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.AlterField(
            model_name='swingtrade',
            name='setup',
            field=models.PositiveSmallIntegerField(choices=[(0, '[Day] First candle new high'), (1, '[Day] Gap and Go'), (2, '[Day] Bull Flag'), (3, '[Day] Reversal'), (4, '[Day] Red to Green'), (5, '[Day] 20 minutes new high'), (6, '[Day] Earning Gap'), (100, '[Swing] 20 days new high'), (101, '[Swing] 55 days new high')], default=100),
        ),
        migrations.AlterField(
            model_name='tradingsettings',
            name='algo_type',
            field=models.PositiveSmallIntegerField(choices=[(0, '[DAY (MOMO)] Momo day trade as much as possible, mainly for collect data.'), (1, '[DAY (MOMO REDUCE SIZE)] Momo day trade based on win rate, reduce size when win rate low.'), (3, '[DAY (MOMO NEW HIGH)] Momo day trade, no entry if the price not break max of last high price.'), (2, '[DAY (RED GREEN)] Day trade based on red to green strategy.'), (4, '[DAY (BREAKOUT)] Breakout day trade, entry if price reach 20 minutes new high.'), (5, '[DAY (EARNING)] Earning date day trade, entry if gap up.'), (100, '[SWING (TURTLE 20)] Swing trade based on turtle trading rules (20 days).'), (101, '[SWING (TURTLE 55)] Swing trade based on turtle trading rules (55 days).'), (201, '[DAY/SWING (RG/TURTLE)] Day/Swing trade with red to green and turtle (55 days) strategy.'), (202, '[DAY/SWING (BREAKOUT/TURTLE)] Day/Swing trade with breakout (20 minutes) and turtle (55 days) strategy.')], default=0),
        ),
        migrations.AlterField(
            model_name='webullordernote',
            name='setup',
            field=models.PositiveSmallIntegerField(choices=[(0, '[Day] First candle new high'), (1, '[Day] Gap and Go'), (2, '[Day] Bull Flag'), (3, '[Day] Reversal'), (4, '[Day] Red to Green'), (5, '[Day] 20 minutes new high'), (6, '[Day] Earning Gap'), (100, '[Swing] 20 days new high'), (101, '[Swing] 55 days new high')], default=0),
        ),
    ]