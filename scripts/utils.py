import pandas as pd
import numpy as np
import pytz
import math
from django.utils import timezone
from django.conf import settings
from datetime import datetime, date
from old_ross import enums
from scripts import config
from old_ross.models import HistoricalKeyStatistics, TradingSettings, WebullAccountStatistics, WebullCredentials, WebullNews, WebullOrder, WebullOrderNote, HistoricalMinuteBar, HistoricalDailyBar


MILLNAMES = ['', 'K', 'M', 'B', 'T']


def millify(n):
    n = float(n)
    millidx = max(0, min(len(MILLNAMES)-1,
                         int(math.floor(0 if n == 0 else math.log10(abs(n))/3))))
    return '{:.2f}{}'.format(n / 10**(3 * millidx), MILLNAMES[millidx])


def local_time_minute(t):
    utc = t.replace(tzinfo=pytz.UTC)
    localtz = utc.astimezone(timezone.get_current_timezone())
    format = '%H:%M'
    return localtz.strftime(format)

def local_time_minute_second(t):
    utc = t.replace(tzinfo=pytz.UTC)
    localtz = utc.astimezone(timezone.get_current_timezone())
    format = '%H:%M:%S'
    return localtz.strftime(format)


# hack to delay 1 minute


def local_time_minute_delay(t):
    utc = t.replace(tzinfo=pytz.UTC)
    localtz = utc.astimezone(timezone.get_current_timezone())
    hour = str(localtz.hour)
    minute = str(localtz.minute + 1)
    if minute == "60":
        minute = "00"
        hour = str(localtz.hour + 1)
    if len(hour) < 2:
        hour = "0{}".format(hour)
    if len(minute) < 2:
        minute = "0{}".format(minute)
    return "{}:{}".format(hour, minute)

# for 2 minute


def local_time_minute2(t):
    utc = t.replace(tzinfo=pytz.UTC)
    localtz = utc.astimezone(timezone.get_current_timezone())
    hour = str(localtz.hour)
    minute = localtz.minute
    if minute % 2 == 1:
        minute -= 1
    minute = str(minute + 2)
    if minute == "60":
        minute = "00"
        hour = str(localtz.hour + 1)
    if len(hour) < 2:
        hour = "0{}".format(hour)
    if len(minute) < 2:
        minute = "0{}".format(minute)
    return "{}:{}".format(hour, minute)


def get_now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def is_market_hour():
    return is_regular_market_hour() or is_extended_market_hour()


def is_extended_market_hour():
    return is_pre_market_hour() or is_after_market_hour()


def is_pre_market_hour():
    """
    NY pre market hour from 04:00 to 09:30
    """
    now = datetime.now()
    if now.hour < 4 or now.hour > 9:
        return False
    # stop pre market earlier for 5 minutes
    if now.hour == 9 and now.minute >= 25:
        return False
    # wait 3 min for webull get pre market data ready
    if now.hour == 4 and now.minute < 3:
        return False
    return True


def is_after_market_hour():
    """
    NY after market hour from 16:00 to 20:00
    """
    now = datetime.now()
    if now.hour < 16 or now.hour >= 20:
        return False
    # wait 3 min for webull get after market data ready
    if now.hour == 16 and now.minute < 3:
        return False
    # stop after market earlier for 5 minutes
    if now.hour == 19 and now.minute >= 55:
        return False
    return True


def is_regular_market_hour():
    """
    NY regular market hour from 09:30 to 16:00
    """
    now = datetime.now()
    if now.hour < 9 or now.hour >= 16:
        return False
    # wait 3 min for webull get regular market data ready
    if now.hour == 9 and now.minute < 33:
        return False
    # stop regular market earlier for 5 minutes
    if now.hour == 15 and now.minute >= 55:
        return False
    return True


def _open_resampler(series):
    if series.size > 0:
        return series[0]
    return 0


def _close_resampler(series):
    if series.size > 0:
        return series[-1]
    return 0


def _high_resampler(series):
    if series.size > 0:
        return np.max(series)
    return 0


def _low_resampler(series):
    if series.size > 0:
        return np.min(series)
    return 0


def _volume_resampler(series):
    if series.size > 0:
        return np.sum(series)
    return 0


def _vwap_resampler(series):
    if series.size > 0:
        return series[-1]
    return 0


def convert_2m_bars(bars):
    if not bars.empty:
        bars_2m = pd.DataFrame()
        bars_2m_open = bars['open'].resample(
            '2T', label="right", closed="right").apply(_open_resampler)
        bars_2m_close = bars['close'].resample(
            '2T', label="right", closed="right").apply(_close_resampler)
        bars_2m_high = bars['high'].resample(
            '2T', label="right", closed="right").apply(_high_resampler)
        bars_2m_low = bars['low'].resample(
            '2T', label="right", closed="right").apply(_low_resampler)
        bars_2m_volume = bars['volume'].resample(
            '2T', label="right", closed="right").apply(_volume_resampler)
        bars_2m_vwap = bars['vwap'].resample(
            '2T', label="right", closed="right").apply(_vwap_resampler)
        bars_2m['open'] = bars_2m_open
        bars_2m['close'] = bars_2m_close
        bars_2m['high'] = bars_2m_high
        bars_2m['low'] = bars_2m_low
        bars_2m['volume'] = bars_2m_volume
        bars_2m['vwap'] = bars_2m_vwap
        # filter zero row
        return bars_2m.loc[(bars_2m != 0).all(axis=1), :]
    return pd.DataFrame()


def check_bars_updated(bars):
    """
    check if have valid latest chart data, delay no more than 1 minute
    """
    latest_index = bars.index[-1]
    latest_timestamp = int(datetime.timestamp(latest_index.to_pydatetime()))
    current_timestamp = int(datetime.timestamp(datetime.now()))
    if current_timestamp - latest_timestamp <= 60:
        return True
    return False


def check_bars_current_low_less_than_prev_low(bars):
    """
    check if current low price less than prev low price
    """
    if not bars.empty:
        current_low = bars.iloc[-1]['low']
        prev_low = bars.iloc[-2]['low']
        if current_low < prev_low:
            return True
    return False


def check_bars_price_fixed(bars):
    """
    check if prev chart candlestick price is fixed
    """
    if not bars.empty:
        prev_close2 = bars.iloc[-2]['close']
        prev_close3 = bars.iloc[-3]['close']
        prev_close4 = bars.iloc[-4]['close']
        if prev_close2 == prev_close3 and prev_close3 == prev_close4:
            return True
    return False


def calculate_charts_ema9(charts):
    """
    https://school.stockcharts.com/doku.php?id=technical_indicators:moving_averages
    """
    multiplier = 2 / (9 + 1)
    charts_length = len(charts)
    for i in range(0, charts_length):
        candle = charts[charts_length - i - 1]
        if i < 8:
            candle['ema9'] = 0
        elif i == 8:
            # use sma for initial ema
            sum = 0.0
            for j in (0, 8):
                c = charts[charts_length - j - 1]
                sum += c['close']
            candle['ema9'] = round(sum / 9, 2)
        else:
            prev_candle = charts[charts_length - i]
            candle['ema9'] = round(
                (candle['close'] - prev_candle['ema9']) * multiplier + prev_candle['ema9'], 2)
    return charts


def get_order_action_enum(action_str):
    action = enums.ActionType.BUY
    if action_str == "SELL":
        action = enums.ActionType.SELL
    return action


def get_order_type_enum(type_str):
    order_type = enums.OrderType.LMT
    if type_str == "MKT":
        order_type = enums.OrderType.MKT
    elif type_str == "STP":
        order_type = enums.OrderType.STP
    elif type_str == "STP LMT":
        order_type = enums.OrderType.STP_LMT
    elif type_str == "STP TRAIL":
        order_type = enums.OrderType.STP_TRAIL
    return order_type


def get_time_in_force_enum(time_in_force_str):
    time_in_force = enums.TimeInForceType.GTC
    if time_in_force_str == "DAY":
        time_in_force = enums.TimeInForceType.DAY
    elif time_in_force_str == "IOC":
        time_in_force = enums.TimeInForceType.IOC
    return time_in_force


def check_paper():
    trading_settings = TradingSettings.objects.first()
    if not trading_settings:
        print(
            "[{}] Cannot find trading settings, default paper trading!".format(get_now()))
        return False
    return trading_settings.paper


def load_webull_credentials(cred_data, paper=True):
    credentials = WebullCredentials.objects.filter(paper=paper).first()
    if not credentials:
        credentials = WebullCredentials(
            cred=cred_data,
            paper=paper,
        )
    else:
        credentials.cred = cred_data
    credentials.save()


def save_webull_credentials(cred_data, paper=True):
    credentials = WebullCredentials.objects.filter(paper=paper).first()
    if not credentials:
        credentials = WebullCredentials(
            cred=cred_data,
            paper=paper,
        )
    else:
        credentials.cred = cred_data
    credentials.save()


def save_webull_account(acc_data):
    today = date.today()
    print("[{}] Importing daily account status ({})...".format(
        get_now(), today.strftime("%Y-%m-%d")))
    account_members = acc_data['accountMembers']
    day_profit_loss = 0
    for account_member in account_members:
        if account_member['key'] == 'dayProfitLoss':
            day_profit_loss = float(account_member['value'])
    acc_stat = WebullAccountStatistics.objects.filter(date=today).first()
    if not acc_stat:
        acc_stat = WebullAccountStatistics(date=today)
    acc_stat.net_liquidation = acc_data['netLiquidation']
    acc_stat.total_profit_loss = acc_data['totalProfitLoss']
    acc_stat.total_profit_loss_rate = acc_data['totalProfitLossRate']
    acc_stat.day_profit_loss = day_profit_loss
    acc_stat.save()


def save_webull_order(order_data, paper=True):
    if paper:
        order_id = str(order_data['orderId'])
        order = WebullOrder.objects.filter(order_id=order_id).first()
        symbol = order_data['ticker']['symbol']
        print("[{}] Importing order <{}> {} ({})...".format(
            get_now(), symbol, order_id, order_data['placedTime']))
        if order:
            print("[{}] Order <{}> {} ({}) already existed!".format(
                get_now(), symbol, order_id, order_data['placedTime']))
        else:
            ticker_id = str(order_data['ticker']['tickerId'])
            action = get_order_action_enum(order_data['action'])
            status = order_data['statusStr']
            order_type = get_order_type_enum(order_data['orderType'])
            total_quantity = int(order_data['totalQuantity'])
            filled_quantity = int(order_data['filledQuantity'])
            avg_price = 0
            if 'avgFilledPrice' in order_data:
                avg_price = float(order_data['avgFilledPrice'])
                price = avg_price
            if 'lmtPrice' in order_data:
                price = float(order_data['lmtPrice'])
            filled_time = None
            if 'filledTime' in order_data:
                filled_time = pytz.timezone(settings.TIME_ZONE).localize(
                    datetime.strptime(order_data['filledTime'], "%m/%d/%Y %H:%M:%S EDT"))
            placed_time = pytz.timezone(settings.TIME_ZONE).localize(
                datetime.strptime(order_data['placedTime'], "%m/%d/%Y %H:%M:%S EDT"))
            time_in_force = get_time_in_force_enum(order_data['timeInForce'])

            order = WebullOrder(
                order_id=order_id,
                ticker_id=ticker_id,
                symbol=symbol,
                action=action,
                status=status,
                total_quantity=total_quantity,
                filled_quantity=filled_quantity,
                price=price,
                avg_price=avg_price,
                order_type=order_type,
                filled_time=filled_time,
                placed_time=placed_time,
                time_in_force=time_in_force,
                paper=paper,
            )
            order.save()
    else:
        # TODO, support live trade orders
        pass


def save_webull_order_note(order_id, note):
    # TODO, support other setup
    order_note = WebullOrderNote(
        order_id=str(order_id),
        setup=enums.SetupType.DAY_FIRST_CANDLE_NEW_HIGH,
        note=note,
    )
    order_note.save()


def save_webull_news_list(news_list, symbol, date):
    print("[{}] Importing news for {}...".format(get_now(), symbol))
    for news_data in news_list:
        save_webull_news(news_data, symbol, date)


def save_webull_news(news_data, symbol, date):
    news = WebullNews.objects.filter(
        news_id=news_data['id'], symbol=symbol, date=date).first()
    if not news:
        news = WebullNews(
            news_id=news_data['id'],
            symbol=symbol,
            title=news_data['title'],
            source_name=news_data['sourceName'],
            collect_source=news_data['collectSource'],
            news_time=news_data['newsTime'],
            summary=news_data['summary'],
            news_url=news_data['newsUrl'],
            date=date,
        )
        news.save()


def save_hist_key_statistics(quote_data, date):
    symbol = quote_data['symbol']
    print("[{}] Importing key statistics for {}...".format(
        get_now(), symbol))
    key_statistics = HistoricalKeyStatistics.objects.filter(
        symbol=symbol, date=date)
    if not key_statistics:
        pe = None
        if 'pe' in quote_data:
            pe = float(quote_data['pe'])
        forward_pe = None
        if 'forwardPe' in quote_data:
            forward_pe = float(quote_data['forwardPe'])
        pe_ttm = None
        if 'peTtm' in quote_data:
            pe_ttm = float(quote_data['peTtm'])
        eps = None
        if 'eps' in quote_data:
            eps = float(quote_data['eps'])
        eps_ttm = None
        if 'epsTtm' in quote_data:
            eps_ttm = float(quote_data['epsTtm'])
        pb = None
        if 'pb' in quote_data:
            pb = float(quote_data['pb'])
        ps = None
        if 'ps' in quote_data:
            ps = float(quote_data['ps'])
        bps = None
        if 'bps' in quote_data:
            bps = float(quote_data['bps'])
        latest_earnings_date = ''
        if 'latestEarningsDate' in quote_data:
            latest_earnings_date = quote_data['latestEarningsDate']
        estimate_earnings_date = ''
        if 'estimateEarningsDate' in quote_data:
            estimate_earnings_date = quote_data['estimateEarningsDate']
        short_float = None
        if 'shortFloat' in quote_data and quote_data['shortFloat'] != "-" and quote_data['shortFloat'] != None:
            short_float = float(quote_data['shortFloat'])
        key_statistics = HistoricalKeyStatistics(
            symbol=symbol,
            open=float(quote_data['open']),
            high=float(quote_data['high']),
            low=float(quote_data['low']),
            close=float(quote_data['close']),
            change=float(quote_data['change']),
            change_ratio=float(quote_data['changeRatio']),
            market_value=float(quote_data['marketValue']),
            volume=float(quote_data['volume']),
            turnover_rate=float(quote_data['turnoverRate']),
            vibrate_ratio=float(quote_data['vibrateRatio']),
            avg_vol_10d=float(quote_data['avgVol10D']),
            avg_vol_3m=float(quote_data['avgVol3M']),
            pe=pe,
            forward_pe=forward_pe,
            pe_ttm=pe_ttm,
            eps=eps,
            eps_ttm=eps_ttm,
            pb=pb,
            ps=ps,
            bps=bps,
            short_float=short_float,
            total_shares=float(quote_data['totalShares']),
            outstanding_shares=float(quote_data['outstandingShares']),
            fifty_two_wk_high=float(quote_data['fiftyTwoWkHigh']),
            fifty_two_wk_low=float(quote_data['fiftyTwoWkLow']),
            latest_earnings_date=latest_earnings_date,
            estimate_earnings_date=estimate_earnings_date,
            date=date,
        )
        key_statistics.save()


def save_hist_minute_bar_list(bar_list):
    print("[{}] Importing minute bar for {}...".format(
        get_now(), bar_list[0]['symbol']))
    for bar_data in bar_list:
        save_hist_minute_bar(bar_data)


def save_hist_minute_bar(bar_data):
    bar = HistoricalMinuteBar.objects.filter(
        symbol=bar_data['symbol'], time=bar_data['time']).first()
    if not bar:
        bar = HistoricalMinuteBar(
            symbol=bar_data['symbol'],
            date=bar_data['date'],
            time=bar_data['time'],
            open=bar_data['open'],
            high=bar_data['high'],
            low=bar_data['low'],
            close=bar_data['close'],
            volume=bar_data['volume'],
            vwap=bar_data['vwap'],
        )
        bar.save()


def save_hist_daily_bar_list(bar_list):
    print("[{}] Importing daily bar for {}...".format(
        get_now(), bar_list[0]['symbol']))
    for bar_data in bar_list:
        save_hist_daily_bar(bar_data)


def save_hist_daily_bar(bar_data):
    bar = HistoricalDailyBar.objects.filter(
        symbol=bar_data['symbol'], date=bar_data['date']).first()
    if not bar:
        bar = HistoricalDailyBar(
            symbol=bar_data['symbol'],
            date=bar_data['date'],
            open=bar_data['open'],
            high=bar_data['high'],
            low=bar_data['low'],
            close=bar_data['close'],
            volume=bar_data['volume'],
        )
        bar.save()


def get_trades_from_orders(buy_orders, sell_orders):
    trades = []
    for buy_order in buy_orders:
        # fill buy side
        trades.append({
            "symbol": buy_order.symbol,
            "ticker_id": buy_order.ticker_id,
            "quantity": buy_order.filled_quantity,
            "buy_price": buy_order.avg_price,
            "buy_time": buy_order.filled_time,
            "buy_order_id": buy_order.order_id,
        })
    for sell_order in sell_orders:
        # fill sell side
        for trade in trades:
            if sell_order.symbol == trade["symbol"] and sell_order.filled_quantity == trade["quantity"] and "sell_price" not in trade:
                trade["sell_price"] = sell_order.avg_price
                trade["sell_time"] = sell_order.filled_time
                trade["sell_order_id"] = sell_order.order_id
                break
    return trades


def get_market_hourly_interval_empty():
    empty_list = []
    for i in range(0, 32):
        empty_list.append({
            "trades": 0,
            "win_trades": 0,
            "loss_trades": 0,
            "total_profit": 0.0,
            "total_loss": 0.0,
            "profit_loss": 0.0,
        })
    return empty_list


def get_market_hourly_interval_labels():
    return [
        "04:00-04:30",  # 0
        "04:30-05:00",  # 1
        "05:00-05:30",  # 2
        "05:30-06:00",  # 3
        "06:00-06:30",  # 4
        "06:30-07:00",  # 5
        "07:00-07:30",  # 6
        "07:30-08:00",  # 7
        "08:00-08:30",  # 8
        "08:30-09:00",  # 9
        "09:00-09:30",  # 10
        "09:30-10:00",  # 11
        "10:00-10:30",  # 12
        "10:30-11:00",  # 13
        "11:00-11:30",  # 14
        "11:30-12:00",  # 15
        "12:00-12:30",  # 16
        "12:30-13:00",  # 17
        "13:00-13:30",  # 18
        "13:30-14:00",  # 19
        "14:00-14:30",  # 20
        "14:30-15:00",  # 21
        "15:00-15:30",  # 22
        "15:30-16:00",  # 23
        "16:00-16:30",  # 24
        "16:30-17:00",  # 25
        "17:00-17:30",  # 26
        "17:30-18:00",  # 27
        "18:00-18:30",  # 28
        "18:30-19:00",  # 29
        "19:00-19:30",  # 30
        "19:30-20:00",  # 31
    ]


def get_market_hourly_interval_index(t):
    index = -1
    if t.hour == 4:
        if t.minute < 30:
            index = 0
        else:
            index = 1
    elif t.hour == 5:
        if t.minute < 30:
            index = 2
        else:
            index = 3
    elif t.hour == 6:
        if t.minute < 30:
            index = 4
        else:
            index = 5
    elif t.hour == 7:
        if t.minute < 30:
            index = 6
        else:
            index = 7
    elif t.hour == 8:
        if t.minute < 30:
            index = 8
        else:
            index = 9
    elif t.hour == 9:
        if t.minute < 30:
            index = 10
        else:
            index = 11
    elif t.hour == 10:
        if t.minute < 30:
            index = 12
        else:
            index = 13
    elif t.hour == 11:
        if t.minute < 30:
            index = 14
        else:
            index = 15
    elif t.hour == 12:
        if t.minute < 30:
            index = 16
        else:
            index = 17
    elif t.hour == 13:
        if t.minute < 30:
            index = 18
        else:
            index = 19
    elif t.hour == 14:
        if t.minute < 30:
            index = 20
        else:
            index = 21
    elif t.hour == 15:
        if t.minute < 30:
            index = 22
        else:
            index = 23
    elif t.hour == 16:
        if t.minute < 30:
            index = 24
        else:
            index = 25
    elif t.hour == 17:
        if t.minute < 30:
            index = 26
        else:
            index = 27
    elif t.hour == 18:
        if t.minute < 30:
            index = 28
        else:
            index = 29
    elif t.hour == 19:
        if t.minute < 30:
            index = 30
        else:
            index = 31
    return index


# utils for render UI

def get_account_type_for_render():
    account_type = {
        "value": "LIVE",
        "value_style": "bg-success",
    }
    if check_paper():
        account_type["value"] = "PAPER"
        account_type["value_style"] = "bg-warning"
    return account_type


def get_color_bar_chart_item_for_render(value):
    if value >= 0:
        return {
            'value': value,
            'itemStyle': {'color': config.PROFIT_COLOR},
        }
    return {
        'value': value,
        'itemStyle': {'color': config.LOSS_COLOR},
    }


def get_day_profit_loss_for_render(acc_stat):
    day_profit_loss = {
        "value": "$0.0",
        "value_style": "",
        "day_pl_rate": "0.0%",
        "day_pl_rate_style": "badge-soft-dark",
    }
    if acc_stat:
        day_profit_loss["value"] = "${}".format(
            abs(acc_stat.day_profit_loss))
        day_pl_rate = acc_stat.day_profit_loss / \
            (acc_stat.net_liquidation - acc_stat.day_profit_loss)
        day_profit_loss["day_pl_rate"] = "{}%".format(
            round(day_pl_rate * 100, 2))
        if acc_stat.day_profit_loss > 0:
            day_profit_loss["value"] = "+" + day_profit_loss["value"]
            day_profit_loss["value_style"] = "text-success"
            day_profit_loss["day_pl_rate"] = "+" + \
                day_profit_loss["day_pl_rate"]
            day_profit_loss["day_pl_rate_style"] = "badge-soft-success"
        elif acc_stat.day_profit_loss < 0:
            day_profit_loss["value"] = "-" + day_profit_loss["value"]
            day_profit_loss["value_style"] = "text-danger"
            day_profit_loss["day_pl_rate_style"] = "badge-soft-danger"
    return day_profit_loss


def get_minute_candle_data_for_render(bars):
    candle_data = {
        "times": [],
        "candles": [],
        "volumes": [],
        "vwaps": [],
        "ema9s": [],
    }
    for timestamp, candle in bars.iterrows():
        candle_data['times'].append(local_time_minute(timestamp))
        # open, close, low, high
        candle_data['candles'].append(
            [candle['open'], candle['close'], candle['low'], candle['high']])
        if candle['close'] < candle['open']:
            candle_data['volumes'].append({
                'value': candle['volume'],
                'itemStyle': {'color': config.LOSS_COLOR},
            })
        else:
            candle_data['volumes'].append({
                'value': candle['volume'],
                'itemStyle': {'color': config.PROFIT_COLOR},
            })
        candle_data['vwaps'].append(candle['vwap'])
        candle_data['ema9s'].append(round(candle['ema9'], 2))
    return candle_data


def get_last_60d_daily_candle_data_for_render(symbol, date):
    candle_data = {
        "times": [],
        "candles": [],
        "volumes": [],
    }
    daily_bars = HistoricalDailyBar.objects.filter(symbol=symbol)
    end_idx = -1
    for i in range(0, len(daily_bars)):
        if daily_bars[i].date == date:
            end_idx = i + 1
            break
    start_idx = max(end_idx - 60, 0)
    candle_data = {
        "times": [],
        "candles": [],
        "volumes": [],
    }
    for i in range(start_idx, end_idx):
        candle = daily_bars[i]
        candle_data["times"].append(candle.date.strftime("%m/%d"))
        # open, close, low, high
        candle_data["candles"].append(
            [candle.open, candle.close, candle.low, candle.high])
        if candle.close < candle.open:
            candle_data['volumes'].append({
                'value': candle.volume,
                'itemStyle': {'color': config.LOSS_COLOR},
            })
        else:
            candle_data['volumes'].append({
                'value': candle.volume,
                'itemStyle': {'color': config.PROFIT_COLOR},
            })
    return candle_data
