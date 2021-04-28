from datetime import datetime
from old_ross.models import WebullOrderNote


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
    # wait 30 second for webull get pre market data ready
    if now.hour == 4 and now.minute == 0 and now.second < 30:
        return False
    return True


def is_after_market_hour():
    """
    NY after market hour from 16:00 to 20:00
    """
    now = datetime.now()
    if now.hour < 16 or now.hour >= 20:
        return False
    # wait 30 second for webull get after market data ready
    if now.hour == 16 and now.minute == 0 and now.second < 30:
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
    if now.hour == 9 and now.minute < 30:
        return False
    # stop regular market earlier for 5 minutes
    if now.hour == 15 and now.minute >= 55:
        return False
    # wait 30 second for webull get regular market data ready
    if now.hour == 9 and now.minute == 30 and now.second < 30:
        return False
    return True


def check_since_last_sell_too_short(last_sell_time, bars):
    """
    check if last sell candle is same as currently candle
    """
    if last_sell_time == None:
        return False
    last_sell_timestamp = int(datetime.timestamp(last_sell_time))
    latest_index = bars.index[-1]
    latest_timestamp = int(datetime.timestamp(latest_index.to_pydatetime()))
    last_sell_minutes = int(last_sell_timestamp / 60)
    latest_minutes = int(latest_timestamp / 60)
    if latest_minutes == last_sell_minutes:
        return True
    return False


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


def save_webull_order_note(order_id, note):
    order_note = WebullOrderNote(
        order_id=str(order_id),
        note=note,
    )
    order_note.save()
