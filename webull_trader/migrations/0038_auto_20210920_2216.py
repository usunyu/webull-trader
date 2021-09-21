# Generated by Django 3.1.7 on 2021-09-21 02:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('webull_trader', '0037_auto_20210907_1550'),
    ]

    operations = [
        migrations.AddField(
            model_name='daytrade',
            name='units',
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddField(
            model_name='swingtrade',
            name='units',
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AlterField(
            model_name='tradingsettings',
            name='algo_type',
            field=models.PositiveSmallIntegerField(choices=[(0, '[DAY (MOMO)] Momo day trade as much as possible, mainly for collect data.'), (1, '[DAY (MOMO REDUCE SIZE)] Momo day trade based on win rate, reduce size when win rate low.'), (3, '[DAY (MOMO NEW HIGH)] Momo day trade, no entry if the price not break max of last high trade price.'), (2, '[DAY (RED GREEN)] Day trade based on red to green strategy.'), (10, '[DAY (BREAKOUT 10)] Breakout day trade, entry if price reach 10 candles new high.'), (4, '[DAY (BREAKOUT 20)] Breakout day trade, entry if price reach 20 candles new high.'), (5, '[DAY (BREAKOUT 30)] Breakout day trade, entry if price reach 30 candles new high.'), (6, '[DAY (BREAKOUT EARNINGS)] Breakout and earning day trade, entry if price reach period new high.'), (11, '[DAY (BREAKOUT NEW HIGH)] Breakout day trade, no entry if the price not break max of last high trade price.'), (12, '[DAY (BREAKOUT 10-5)] Breakout day trade, entry if price reach 10 candles new high in 5 minute chart.'), (13, '[DAY (BREAKOUT PRE LOSERS)] Breakout day trade, find pre-market losers and aim for reversal.'), (14, '[DAY (BREAKOUT 55)] Breakout day trade, entry if price reach 55 candles new high.'), (7, '[DAY (EARNINGS)] Earning date day trade, entry if gap up and exit trade intraday.'), (8, '[DAY (EARNINGS OVERNIGHT)] Earning date day trade, entry if gap up and may hold position overnight.'), (9, '[DAY (EARNINGS BREAKOUT)] Earning date day trade, entry if gap up and do breakout trade if no earning event.'), (15, '[DAY (VWAP LARGE CAP)] VWAP reclaim day trade, entry if price reclaim vwap for large cap tickers.'), (16, '[DAY (GRINDING LARGE CAP)] Grinding day trading with large cap and major news.'), (17, '[DAY (GRINDING SYMBOLS)] Grinding day trading with specific symbols.'), (18, '[DAY (BREAKOUT ASK)] Breakout day trade, entry with ask price limit order.'), (19, '[DAY (BREAKOUT 20,11)] Breakout day trade, entry if price reach 20 candles new high, exit if price reach 11 candles new low.'), (20, '[DAY (BREAKOUT 20,9)] Breakout day trade, entry if price reach 20 candles new high, exit if price reach 9 candles new low.'), (21, '[DAY (BREAKOUT 20,8)] Breakout day trade, entry if price reach 20 candles new high, exit if price reach 8 candles new low.'), (24, '[DAY (BREAKOUT 20,1)] Breakout day trade, entry if price reach 20 candles new high, exit if price reach 1 candles new low.'), (22, '[DAY (BREAKOUT SCALE)] Breakout day trade, entry if price reach 20 candles new high, scale in if reach add unit price.'), (23, '[DAY (BREAKOUT PERIOD)] Breakout day trade, entry if price reach 20 candles new high, exit if period time exceed.'), (25, '[DAY (BREAKOUT DYN EXIT)] Breakout day trade, entry if price reach 20 candles new high, dynamic adjust exit period based on profit loss rate.'), (26, '[DAY (BREAKOUT SCALE MAX LOSS)] Breakout day trade, entry if price reach 20 candles new high, scale in if reach add unit price and with max stop loss.'), (27, '[DAY (BREAKOUT SCALE ATR LOSS)] Breakout day trade, entry if price reach 20 candles new high, scale in if reach add unit price and use ATR as stop loss.'), (28, '[DAY (BREAKOUT SCALE PERIOD ROC)] Breakout day trade, entry if price reach 20 candles new high, scale in if reach add check period high for ROC.'), (100, '[SWING (TURTLE 20)] Swing trade based on turtle trading rules (20 days).'), (101, '[SWING (TURTLE 55)] Swing trade based on turtle trading rules (55 days).'), (201, '[DAY (RED GREEN) / SWING (TURTLE 55)] Day trade based on red to green strategy. / Swing trade based on turtle trading rules (55 days).'), (202, '[DAY (BREAKOUT 10) / SWING (TURTLE 55)] Breakout day trade, entry if price reach 10 candles new high. / Swing trade based on turtle trading rules (55 days).'), (203, '[DAY (EARNINGS) / SWING (TURTLE 55)] Earning date day trade, entry if gap up and exit trade intraday. / Swing trade based on turtle trading rules (55 days).')], default=0),
        ),
    ]
