# -*- coding: utf-8 -*-

MIN_SURGE_AMOUNT = 21000
MIN_SURGE_VOL = 3000
SURGE_MIN_CHANGE_PERCENTAGE = 8  # at least 8% change for surge
TRADE_TIMEOUT = 5  # trading timeout in minutes
PENDING_ORDER_TIMEOUT = 10  # pending order timeout in seconds
HOLDING_ORDER_TIMEOUT = 180  # holding order timeout in seconds
REFRESH_LOGIN_INTERVAL = 10  # refresh login interval minutes
BUY_AMOUNT = 1000
MAX_GAP = 0.02


def start():
    import time
    from datetime import datetime, timedelta
    from sdk import webullsdk
    from scripts import utils

    global MIN_SURGE_AMOUNT
    global MIN_SURGE_VOL
    global SURGE_MIN_CHANGE_PERCENTAGE
    global TRADE_TIMEOUT
    global PENDING_ORDER_TIMEOUT
    global HOLDING_ORDER_TIMEOUT
    global REFRESH_LOGIN_INTERVAL
    global BUY_AMOUNT
    global MAX_GAP

    while not utils.is_after_market():
        print("[{}] wait for after market open...".format(utils.get_now()))
        time.sleep(10)

    print("[{}] after market trading started!".format(utils.get_now()))

    webullsdk.login(paper=True)
    print("[{}] webull logged in".format(utils.get_now()))
    last_login_refresh_time = datetime.now()

    tracking_tickers = {}

    def _check_buy_order_filled(ticker):
        symbol = ticker['symbol']
        ticker_id = ticker['ticker_id']
        print("[{}] checking buy order <{}>[{}] filled...".format(
            utils.get_now(), symbol, ticker_id))
        positions = webullsdk.get_positions()
        if positions == None:
            return
        order_filled = False
        for position in positions:
            if position['ticker']['symbol'] == symbol:
                order_filled = True
                quantity = int(position['position'])
                # update tracking_tickers
                tracking_tickers[symbol]['positions'] = quantity
                tracking_tickers[symbol]['pending_buy'] = False
                tracking_tickers[symbol]['pending_order_id'] = None
                tracking_tickers[symbol]['pending_order_time'] = None
                tracking_tickers[symbol]['order_filled_time'] = datetime.now()
                print("[{}] buy order <{}>[{}] filled!".format(
                    utils.get_now(), symbol, ticker_id))
                break
        if not order_filled:
            # check order timeout
            if (datetime.now() - ticker['pending_order_time']) >= timedelta(seconds=PENDING_ORDER_TIMEOUT):
                # cancel timeout order
                if webullsdk.cancel_order(ticker['pending_order_id']):
                    tracking_tickers[symbol]['pending_buy'] = False
                    tracking_tickers[symbol]['pending_order_id'] = None
                    tracking_tickers[symbol]['pending_order_time'] = None
                    print("[{}] buy order <{}>[{}] timeout, canceled!".format(
                        utils.get_now(), symbol, ticker_id))
                else:
                    print("[{}] failed to cancel timeout buy order <{}>[{}]!".format(
                        utils.get_now(), symbol, ticker_id))

    def _check_sell_order_filled(ticker):
        symbol = ticker['symbol']
        ticker_id = ticker['ticker_id']
        print("[{}] checking sell order <{}>[{}] filled...".format(
            utils.get_now(), symbol, ticker_id))
        positions = webullsdk.get_positions()
        if positions == None:
            return
        order_filled = True
        for position in positions:
            if position['ticker']['symbol'] == symbol:
                order_filled = False
        if order_filled:
            # update tracking_tickers
            tracking_tickers[symbol]['positions'] = 0
            tracking_tickers[symbol]['pending_sell'] = False
            tracking_tickers[symbol]['pending_order_id'] = None
            tracking_tickers[symbol]['pending_order_time'] = None
            print("[{}] sell order <{}>[{}] filled!".format(
                utils.get_now(), symbol, ticker_id))
            # remove from monitor
            del tracking_tickers[symbol]
        else:
            # check order timeout
            if (datetime.now() - ticker['pending_order_time']) >= timedelta(seconds=PENDING_ORDER_TIMEOUT):
                # cancel timeout order
                if webullsdk.cancel_order(ticker['pending_order_id']):
                    print("[{}] sell order <{}>[{}] timeout, canceled!".format(
                        utils.get_now(), symbol, ticker_id))
                    # resubmit sell order
                    quote = webullsdk.get_quote(ticker_id=ticker_id)
                    if quote == None:
                        return
                    bid_price = float(
                        quote['depth']['ntvAggBidList'][0]['price'])
                    holding_quantity = ticker['positions']
                    order_response = webullsdk.sell_limit_order(
                        ticker_id=ticker_id,
                        price=bid_price,
                        quant=holding_quantity)
                    print("[{}] resubmit sell order <{}>[{}], quant: {}, limit price: {}".format(
                        utils.get_now(), symbol, ticker_id, holding_quantity, bid_price))
                    if 'msg' in order_response:
                        print("[{}] {}".format(
                            utils.get_now(), order_response['msg']))
                    else:
                        # mark pending sell
                        tracking_tickers[symbol]['pending_sell'] = True
                        tracking_tickers[symbol]['pending_order_id'] = order_response['orderId']
                        tracking_tickers[symbol]['pending_order_time'] = datetime.now(
                        )
                else:
                    print("[{}] failed to cancel timeout sell order <{}>[{}]!".format(
                        utils.get_now(), symbol, ticker_id))

    def _do_trade(ticker):

        symbol = ticker['symbol']
        ticker_id = ticker['ticker_id']

        pending_buy = ticker['pending_buy']
        if pending_buy:
            _check_buy_order_filled(ticker)
            return

        pending_sell = ticker['pending_sell']
        if pending_sell:
            _check_sell_order_filled(ticker)
            return

        holding_quantity = ticker['positions']
        # check timeout, skip this ticker if no trade during last TRADE_TIMEOUT minutes
        if holding_quantity == 0 and (datetime.now() - ticker['start_time']) >= timedelta(minutes=TRADE_TIMEOUT):
            print("[{}] trading <{}>[{}] session timeout!".format(
                utils.get_now(), symbol, ticker_id))
            # remove from monitor
            del tracking_tickers[symbol]
            return

        if holding_quantity == 0:
            # fetch 1m bar charts
            bars = webullsdk.get_1m_bars(ticker_id, count=30)
            if bars.empty:
                return

            if not utils.check_bars_updated(bars):
                print("[{}] <{}>[{}] charts is not updated, stop trading!".format(
                    utils.get_now(), symbol, ticker_id))
                # remove from monitor
                del tracking_tickers[symbol]
                return

            # calculate and fill ema 9 data
            bars['ema9'] = bars['close'].ewm(span=9, adjust=False).mean()
            current_candle = bars.iloc[-1]
            prev_candle = bars.iloc[-2]

            # current price data
            current_low = current_candle['low']
            current_vwap = current_candle['vwap']
            current_ema9 = current_candle['ema9']
            current_volume = int(current_candle['volume'])
            print("[{}] trading <{}>[{}], low: {}, vwap: {}, ema9: {}, volume: {}".format(
                utils.get_now(), symbol, ticker_id, current_low, current_vwap, round(current_ema9, 3), current_volume))
            # check low price above vwap and ema 9
            if current_low > current_candle['vwap'] and current_low > current_candle['ema9']:
                # check first candle make new high
                if current_candle['high'] > prev_candle['high']:
                    quote = webullsdk.get_quote(ticker_id=ticker_id)
                    if quote == None:
                        return
                    ask_price = float(
                        quote['depth']['ntvAggAskList'][0]['price'])
                    bid_price = float(
                        quote['depth']['ntvAggBidList'][0]['price'])
                    gap = (ask_price - bid_price) / bid_price
                    if gap > MAX_GAP:
                        print("[{}] <{}>[{}] gap too large, ask: {}, bid: {}, stop trading!".format(
                            utils.get_now(), symbol, ticker_id, ask_price, bid_price))
                        # remove from monitor
                        del tracking_tickers[symbol]
                        return
                    buy_quant = (int)(BUY_AMOUNT / ask_price)
                    # submit limit order at ask price
                    order_response = webullsdk.buy_limit_order(
                        ticker_id=ticker_id,
                        price=ask_price,
                        quant=buy_quant)
                    print("[{}] submit buy order <{}>[{}], quant: {}, limit price: {}".format(
                        utils.get_now(), symbol, ticker_id, buy_quant, ask_price))
                    if 'msg' in order_response:
                        print("[{}] {}".format(
                            utils.get_now(), order_response['msg']))
                    else:
                        # mark pending buy
                        tracking_tickers[symbol]['pending_buy'] = True
                        tracking_tickers[symbol]['pending_order_id'] = order_response['orderId']
                        tracking_tickers[symbol]['pending_order_time'] = datetime.now(
                        )
        else:
            positions = webullsdk.get_positions()
            if positions == None:
                return
            ticker_position = None
            for position in positions:
                if position['ticker']['symbol'] == symbol:
                    ticker_position = position
                    break
            if not ticker_position:
                print("[{}] finding <{}>[{}] position error!".format(
                    utils.get_now(), symbol, ticker_id))
                return
            cost = float(ticker_position['cost'])
            last_price = float(ticker_position['lastPrice'])
            profit_loss_rate = float(
                ticker_position['unrealizedProfitLossRate'])
            # due to no stop trailing order in paper account, keep tracking of max P&L rate
            max_profit_loss_rate = tracking_tickers[symbol]['max_profit_loss_rate']
            if profit_loss_rate > max_profit_loss_rate:
                tracking_tickers[symbol]['max_profit_loss_rate'] = profit_loss_rate
            quantity = int(ticker_position['position'])
            print("[{}] checking <{}>[{}], cost: {}, last: {}, change: {}%".format(
                utils.get_now(), symbol, ticker_id, cost, last_price, round(profit_loss_rate * 100, 2)))
            trailing_stop = False
            # sell if drawdown 1% from max P&L rate
            if max_profit_loss_rate - profit_loss_rate >= 0.01:
                trailing_stop = True
            holding_timeout = False
            if (datetime.now() - ticker['order_filled_time']) >= timedelta(seconds=HOLDING_ORDER_TIMEOUT) and profit_loss_rate < 0.01:
                holding_timeout = True

            # sell if holding too long and no
            if trailing_stop or holding_timeout:
                quote = webullsdk.get_quote(ticker_id=ticker_id)
                if quote == None:
                    return
                bid_price = float(
                    quote['depth']['ntvAggBidList'][0]['price'])
                order_response = webullsdk.sell_limit_order(
                    ticker_id=ticker_id,
                    price=bid_price,
                    quant=quantity)
                print("[{}] submit sell order <{}>[{}], quant: {}, limit price: {}".format(
                    utils.get_now(), symbol, ticker_id, quantity, bid_price))
                if 'msg' in order_response:
                    print("[{}] {}".format(
                        utils.get_now(), order_response['msg']))
                else:
                    # mark pending sell
                    tracking_tickers[symbol]['pending_sell'] = True
                    tracking_tickers[symbol]['pending_order_id'] = order_response['orderId']
                    tracking_tickers[symbol]['pending_order_time'] = datetime.now(
                    )

        # TODO, buy after the first pull back

    # main loop
    while utils.is_after_market():
        # trading tickers
        for symbol in list(tracking_tickers):
            ticker = tracking_tickers[symbol]
            _do_trade(ticker)

        # find trading ticker in top gainers
        top_gainers = webullsdk.get_after_market_gainers()
        top_10_gainers = top_gainers[:10]

        # print("[{}] scanning top gainers [{}]...".format(
        #     utils.get_now(), ', '.join([gainer['symbol'] for gainer in top_10_gainers])))
        for gainer in top_10_gainers:
            symbol = gainer["symbol"]
            # check if ticker already in monitor
            if symbol in tracking_tickers:
                continue
            ticker_id = gainer["ticker_id"]
            # print("[{}] scanning <{}>[{}]...".format(
            #     utils.get_now(), symbol, ticker_id))
            change_percentage = gainer["change_percentage"]
            # check if change >= 8%
            if change_percentage * 100 >= SURGE_MIN_CHANGE_PERCENTAGE:
                bars = webullsdk.get_1m_bars(ticker_id, count=30)
                if bars.empty:
                    continue
                latest_bar = bars.iloc[-1]
                if utils.check_bars_updated(bars):
                    latest_close = latest_bar["close"]
                    volume = int(latest_bar["volume"])
                    # check if trasaction amount meets requirement
                    if latest_close * volume >= MIN_SURGE_AMOUNT and volume >= MIN_SURGE_VOL:
                        # found trading ticker
                        ticker = {
                            "symbol": symbol,
                            "ticker_id": ticker_id,
                            "pending_buy": False,
                            "pending_sell": False,
                            "pending_order_id": None,
                            "pending_order_time": None,
                            "order_filled_time": None,
                            "positions": 0,
                            "start_time": datetime.now(),
                            # paper trade do not have stop trailing order, this value keep track of max P&L
                            "max_profit_loss_rate": 0,
                        }
                        tracking_tickers[symbol] = ticker
                        print("[{}] found <{}>[{}] to trade!".format(
                            utils.get_now(), symbol, ticker_id))

        # refresh login
        if (datetime.now() - last_login_refresh_time) >= timedelta(minutes=REFRESH_LOGIN_INTERVAL):
            webullsdk.login(paper=True)
            print("[{}] refresh webull login".format(utils.get_now()))
            last_login_refresh_time = datetime.now()

        # at least slepp 1 sec
        time.sleep(1)

    webullsdk.logout()
    print("[{}] webull logged out".format(utils.get_now()))

    print("[{}] after market trading ended!".format(utils.get_now()))


if __name__ == "django.core.management.commands.shell":
    start()