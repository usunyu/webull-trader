# -*- coding: utf-8 -*-

# Base trading class

import json
from datetime import datetime
from sdk import webullsdk, fmpsdk
from common import utils, db, sms, constants, exceptions
from common.enums import ActionType, SetupType, TradingHourType
from logger import trading_logger
from trading.tracker.trading_tracker import TradingTracker
from trading.tracker.order_tracker import OrderTracker
from webull_trader.models import SwingPosition, SwingTrade, WebullOrder


class StrategyBase:

    import pandas as pd
    from common.enums import SetupType, TradingHourType
    from trading.tracker.trading_tracker import TrackingTicker

    def __init__(self, paper: bool = True, trading_hour: TradingHourType = TradingHourType.REGULAR):
        # init strategy variables
        self.paper: bool = paper
        self.trading_end: bool = False
        self.trading_hour: TradingHourType = trading_hour
        self.trading_tracker: TradingTracker = TradingTracker()
        self.order_tracker: OrderTracker = OrderTracker()

    def begin(self):
        pass

    def update(self):
        pass

    def end(self):
        pass

    def final(self):
        pass

    def get_tag(self) -> str:
        return "StrategyBase"

    def get_setup(self) -> SetupType:
        return SetupType.UNKNOWN

    # load settings
    def load_settings(self,
                      order_amount_limit: float,
                      extended_order_amount_limit: float,
                      target_profit_ratio: float,
                      stop_loss_ratio: float,
                      day_free_float_limit_in_million: float,
                      day_turnover_rate_limit_percentage: float,
                      day_sectors_limit: str,
                      swing_position_amount_limit: float,
                      day_trade_usable_cash_threshold: float):

        self.order_amount_limit: float = order_amount_limit
        trading_logger.log(
            "Buy order limit: {}".format(self.order_amount_limit))

        self.extended_order_amount_limit: float = extended_order_amount_limit
        trading_logger.log("Buy order limit (extended hour): {}".format(
            self.extended_order_amount_limit))

        self.target_profit_ratio: float = target_profit_ratio
        trading_logger.log("Target profit rate: {}%".format(
            round(self.target_profit_ratio * 100, 2)))

        self.stop_loss_ratio: float = stop_loss_ratio
        trading_logger.log("Stop loss rate: {}%".format(
            round(self.stop_loss_ratio * 100, 2)))

        self.day_free_float_limit_in_million: float = day_free_float_limit_in_million
        trading_logger.log("Day trading max free float (million): {}".format(
            self.day_free_float_limit_in_million))

        self.day_turnover_rate_limit_percentage: float = day_turnover_rate_limit_percentage
        trading_logger.log("Day trading min turnover rate: {}%".format(
            self.day_turnover_rate_limit_percentage))

        self.day_sectors_limit: str = day_sectors_limit
        trading_logger.log("Day trading sectors limit: {}".format(
            self.day_sectors_limit))

        self.swing_position_amount_limit: float = swing_position_amount_limit
        trading_logger.log("Swing position amount limit: {}".format(
            self.swing_position_amount_limit))

        self.day_trade_usable_cash_threshold: float = day_trade_usable_cash_threshold
        trading_logger.log("Usable cash threshold for day trade: {}".format(
            self.day_trade_usable_cash_threshold))

    def update_orders(self):
        # update order tracker
        self.order_tracker.update_orders()

    def update_account(self):
        account_data = webullsdk.get_account()
        db.save_webull_account(account_data, paper=self.paper)

    def build_error_short_ticker(self, symbol, ticker_id):
        return {
            "symbol": symbol,
            "ticker_id": ticker_id,
            # pending buy back order id
            "pending_order_id": None,
            # pending buy back order time
            "pending_order_time": None,
        }

    def is_regular_market_hour(self) -> bool:
        return self.trading_hour == TradingHourType.REGULAR

    def is_pre_market_hour(self) -> bool:
        return self.trading_hour == TradingHourType.BEFORE_MARKET_OPEN

    def is_after_market_hour(self) -> bool:
        return self.trading_hour == TradingHourType.AFTER_MARKET_CLOSE

    def is_extended_market_hour(self) -> bool:
        return self.is_pre_market_hour() or self.is_after_market_hour()

    def check_can_trade_ticker(self, ticker: TrackingTicker):
        symbol = ticker.get_symbol()
        ticker_id = ticker.get_id()
        settings = db.get_or_create_trading_settings()
        day_free_float_limit_in_million = settings.day_free_float_limit_in_million
        day_turnover_rate_limit_percentage = settings.day_turnover_rate_limit_percentage
        tracking_stat = self.trading_tracker.get_stat(symbol)
        # fetch data if not cached
        if day_free_float_limit_in_million > 0 or day_turnover_rate_limit_percentage > 0:
            if tracking_stat.get_free_float() == None or tracking_stat.get_turnover_rate() == None:
                quote = webullsdk.get_quote(ticker_id=ticker_id)
                tracking_stat.set_free_float(
                    utils.get_attr_to_float_or_none(quote, "outstandingShares"))
                tracking_stat.set_turnover_rate(
                    utils.get_attr_to_float_or_none(quote, "turnoverRate"))
        free_float_check = True
        if day_free_float_limit_in_million > 0:
            if tracking_stat.get_free_float() == None or \
                    tracking_stat.get_free_float() > day_free_float_limit_in_million * constants.ONE_MILLION:
                free_float_check = False
        turnover_rate_check = True
        if day_turnover_rate_limit_percentage > 0:
            if tracking_stat.get_turnover_rate() == None or \
                    tracking_stat.get_turnover_rate() * constants.ONE_HUNDRED < day_turnover_rate_limit_percentage:
                turnover_rate_check = False
        sectors_check = True
        day_sectors_limit = settings.day_sectors_limit
        if len(day_sectors_limit) > 0:
            # fetch sector if not cached
            if tracking_stat.get_sector() == None:
                profile = fmpsdk.get_profile(symbol)
                if profile and "sector" in profile:
                    tracking_stat.set_sector(profile["sector"])
            sectors_limit = day_sectors_limit.split(",")
            if tracking_stat.get_sector() == None or tracking_stat.get_sector() not in sectors_limit:
                sectors_check = False

        return (free_float_check or turnover_rate_check) and sectors_check

    # submit buy limit order, only use for day trade
    def submit_buy_limit_order(self, ticker: TrackingTicker, note: str = "Entry point.",
                               retry: bool = False, retry_limit: int = 0):
        symbol = ticker.get_symbol()
        ticker_id = ticker.get_id()
        usable_cash = webullsdk.get_usable_cash()
        db.save_webull_min_usable_cash(usable_cash)
        buy_position_amount = self.get_buy_order_limit(ticker)
        if usable_cash <= buy_position_amount:
            trading_logger.log(
                "Not enough cash to buy <{}>, cash left: {}!".format(symbol, usable_cash))
            return
        buy_price = self.get_buy_price(ticker)
        buy_quant = (int)(buy_position_amount / buy_price)
        if buy_quant > 0:
            # submit limit order at ask price
            order_response = webullsdk.buy_limit_order(
                ticker_id=ticker_id,
                price=buy_price,
                quant=buy_quant)
            order_id = utils.get_order_id_from_response(
                order_response, paper=self.paper)
            if order_id:
                trading_logger.log(
                    f"🟢 Submit buy order {order_id}, ticker: <{symbol}>, quant: {buy_quant}, limit price: {buy_price}")
                # tracking pending buy order
                self.start_tracking_pending_buy_order(
                    ticker, order_id, entry_note=note, retry=retry, retry_limit=retry_limit)
            else:
                trading_logger.log(
                    f"⚠️  Invalid buy order response: {order_response}")
        else:
            trading_logger.log(
                "Order amount limit not enough for <{}>, price: {}".format(symbol, buy_price))

    # submit sell limit order, only use for day trade
    def submit_sell_limit_order(self, ticker: TrackingTicker, note: str = "Exit point.",
                                retry: bool = True, retry_limit: int = 20):
        symbol = ticker.get_symbol()
        ticker_id = ticker.get_id()
        holding_quantity = ticker.get_positions()
        sell_price = self.get_sell_price(ticker)
        order_response = webullsdk.sell_limit_order(
            ticker_id=ticker_id,
            price=sell_price,
            quant=holding_quantity)
        order_id = utils.get_order_id_from_response(
            order_response, paper=self.paper)
        if order_id:
            trading_logger.log(
                f"🔴 Submit sell order {order_id}, ticker: <{symbol}>, quant: {holding_quantity}, limit price: {sell_price}")
            # tracking pending sell order
            self.start_tracking_pending_sell_order(
                ticker, order_id, exit_note=note, retry=retry, retry_limit=retry_limit)
        else:
            trading_logger.log(
                f"⚠️  Invalid sell order response: {order_response}")

    def check_pending_order_done(self, ticker: TrackingTicker):

        if ticker.is_pending_buy():
            self.check_buy_order_done(ticker)
            return

        if ticker.is_pending_sell():
            self.check_sell_order_done(ticker)
            return

        if ticker.is_pending_cancel():
            self.check_cancel_order_done(ticker)
            return

    def _on_buy_order_filled(self, ticker: TrackingTicker, order: WebullOrder,
                             stop_tracking_ticker_after_order_filled: bool = False):
        symbol = ticker.get_symbol()
        ticker_id = ticker.get_id()
        order_id = order.order_id
        if order.status == webullsdk.ORDER_STATUS_FILLED or order.status == webullsdk.ORDER_STATUS_PARTIALLY_FILLED:
            position_obj = ticker.get_position_obj()
            if position_obj:
                # update position obj
                position_obj.order_ids = f"{position_obj.order_ids},{order_id}"
                position_obj.quantity += order.filled_quantity
                position_obj.total_cost += round(
                    order.filled_quantity * order.avg_price, 2)
                position_obj.units += 1
                position_obj.require_adjustment = True
                position_obj.save()
            else:
                # create position obj
                position_obj = db.add_day_position(
                    symbol=symbol,
                    ticker_id=ticker_id,
                    order_id=order_id,
                    setup=self.get_setup(),
                    cost=order.avg_price,
                    quant=order.filled_quantity,
                    buy_time=order.filled_time,
                    stop_loss_price=ticker.get_stop_loss(),
                    target_units=ticker.get_target_units(),
                )
                # set position obj
                ticker.set_position_obj(position_obj)
                # set initial cost
                ticker.set_initial_cost(order.avg_price)
            ticker.inc_positions(order.filled_quantity)
            ticker.inc_units()
            ticker.reset_resubmit_order_count()
            # stop tracking buy order
            self.stop_tracking_pending_buy_order(ticker, order_id)
            # stop tracking ticker
            if stop_tracking_ticker_after_order_filled:
                self.trading_tracker.stop_tracking(ticker)

    def check_buy_order_done(self, ticker: TrackingTicker,
                             stop_tracking_ticker_after_order_filled: bool = False):
        symbol = ticker.get_symbol()
        order_id = ticker.get_pending_order_id()
        order = self.order_tracker.get_order(order_id)
        if order == None:
            trading_logger.log(
                f"Buy order <{symbol}> {webullsdk.ORDER_STATUS_NOT_FOUND}")
            if ticker.is_order_timeout():
                # cancel in case we did not catch the order
                webullsdk.cancel_order(order_id)
                # stop tracking buy order
                self.stop_tracking_pending_buy_order(ticker, order_id)
            return
        trading_logger.log(f"Buy order <{symbol}> {order.status}")
        # filled or partially filled
        if order.status == webullsdk.ORDER_STATUS_FILLED or order.status == webullsdk.ORDER_STATUS_PARTIALLY_FILLED:
            self._on_buy_order_filled(
                ticker, order, stop_tracking_ticker_after_order_filled)
            trading_logger.log(f"Filled price: ${order.avg_price}")
        # pending or working
        elif order.status == webullsdk.ORDER_STATUS_PENDING or order.status == webullsdk.ORDER_STATUS_WORKING:
            if ticker.is_order_timeout() or self.trading_end:
                # timeout, cancel order
                if webullsdk.cancel_order(order_id):
                    # start tracking cancel order
                    self.start_tracking_pending_cancel_order(
                        ticker, order_id, cancel_note="Buy order timeout, canceled!")
                else:
                    trading_logger.log(
                        f"Failed to cancel timeout buy <{symbol}> order: {order_id}!")
        # failed or canceled
        elif order.status == webullsdk.ORDER_STATUS_FAILED or order.status == webullsdk.ORDER_STATUS_CANCELED:
            # stop tracking buy order
            self.stop_tracking_pending_buy_order(ticker, order_id)
        # unknown status
        else:
            raise exceptions.WebullOrderStatusError(
                f"Unknown order status '{order.status}' for order: {order_id}!")

    def _on_sell_order_filled(self, ticker: TrackingTicker, order: WebullOrder,
                              stop_tracking_ticker_after_order_filled: bool = True):
        symbol = ticker.get_symbol()
        ticker_id = ticker.get_id()
        order_id = order.order_id
        if order.status == webullsdk.ORDER_STATUS_FILLED:
            position_obj = ticker.get_position_obj()
            # add trade object
            trade = db.add_day_trade(
                symbol=symbol,
                ticker_id=ticker_id,
                position=position_obj,
                order_id=order_id,
                sell_price=order.avg_price,
                sell_time=order.filled_time,
            )
            # remove position object
            position_obj.delete()
            ticker.reset_positions()
            ticker.reset_resubmit_order_count()
            # stop tracking sell order
            self.stop_tracking_pending_sell_order(ticker, order_id)
            # stop tracking ticker
            if stop_tracking_ticker_after_order_filled:
                self.trading_tracker.stop_tracking(ticker)
            # update trading stats
            tracking_stat = self.trading_tracker.get_stat(symbol)
            tracking_stat.update_by_trade(trade)
        # partially filled
        elif order.status == webullsdk.ORDER_STATUS_PARTIALLY_FILLED:
            position_obj = ticker.get_position_obj()
            # update position object
            position_obj.order_ids = f"{position_obj.order_ids},{order_id}"
            position_obj.require_adjustment = True
            position_obj.save()
            # update tracking ticker
            ticker.dec_positions(order.filled_quantity)
            ticker.reset_resubmit_order_count()
            retry_after_cancel, retry_limit = self.order_tracker.check_retry_after_cancel(
                order_id)
            # stop tracking sell order
            self.stop_tracking_pending_sell_order(ticker, order_id)
            # continue sell reset positions
            trading_logger.log(
                f"Continue sell rest <{symbol}> positions, quant: {ticker.get_positions()}")
            self.submit_sell_limit_order(
                ticker, note="Sell rest positions.", retry=retry_after_cancel, retry_limit=retry_limit)
        else:
            raise exceptions.WebullOrderStatusError(
                f"Unknown order status '{order.status}' for order: {order_id}!")
        # update account status
        self.update_account()

    def _on_sell_order_failed(self, ticker: TrackingTicker, order_status: str, stop_tracking_ticker_after_order_filled: bool = True):
        symbol = ticker.get_symbol()
        order_id = ticker.get_pending_order_id()
        if order_status in [webullsdk.ORDER_STATUS_FAILED, webullsdk.ORDER_STATUS_CANCELED, webullsdk.ORDER_STATUS_NOT_FOUND]:
            resubmit_count = ticker.get_resubmit_order_count()
            retry_after_cancel, retry_limit = self.order_tracker.check_retry_after_cancel(
                order_id)
            self.stop_tracking_pending_sell_order(ticker, order_id)
            if retry_after_cancel and resubmit_count < retry_limit and not self.trading_end:
                # retry sell order
                trading_logger.log(
                    f"Resubmitting sell order <{symbol}>...")
                self.submit_sell_limit_order(
                    ticker, note=f"Resubmit sell order ({resubmit_count}).", retry=retry_after_cancel, retry_limit=retry_limit)
                # increment resubmit order count
                ticker.inc_resubmit_order_count()
            else:
                position_obj = ticker.get_position_obj()
                # update setup
                position_obj.setup = SetupType.ERROR_FAILED_TO_SELL
                position_obj.save()
                trading_logger.log(
                    "Failed to sell position <{}>!".format(symbol))
                # send message
                sms.notify_message(
                    "Failed to sell <{}> position, please check now!".format(symbol))
                # stop tracking ticker
                if stop_tracking_ticker_after_order_filled:
                    self.trading_tracker.stop_tracking(ticker)
        else:
            raise exceptions.WebullOrderStatusError(
                f"Unknown order status '{order_status}' for order: {order_id}!")

    def check_sell_order_done(self, ticker: TrackingTicker,
                              stop_tracking_ticker_after_order_filled: bool = True):
        symbol = ticker.get_symbol()
        order_id = ticker.get_pending_order_id()
        order = self.order_tracker.get_order(order_id)
        if order == None:
            trading_logger.log(
                f"Sell order <{symbol}> {webullsdk.ORDER_STATUS_NOT_FOUND}")
            if ticker.is_order_timeout():
                # cancel in case we did not catch the order
                webullsdk.cancel_order(order_id)
                self._on_sell_order_failed(
                    ticker, webullsdk.ORDER_STATUS_NOT_FOUND, stop_tracking_ticker_after_order_filled)
            return
        trading_logger.log(f"Sell order <{symbol}> {order.status}")
        # filled or partially filled
        if order.status == webullsdk.ORDER_STATUS_FILLED or order.status == webullsdk.ORDER_STATUS_PARTIALLY_FILLED:
            self._on_sell_order_filled(
                ticker, order, stop_tracking_ticker_after_order_filled)
            trading_logger.log(f"Filled price: ${order.avg_price}")
        # pending or working
        elif order.status == webullsdk.ORDER_STATUS_PENDING or order.status == webullsdk.ORDER_STATUS_WORKING:
            if ticker.is_order_timeout():
                # timeout, cancel order
                if webullsdk.cancel_order(order_id):
                    # start tracking cancel order
                    self.start_tracking_pending_cancel_order(
                        ticker, order_id, cancel_note="Sell order timeout, canceled!")
                else:
                    trading_logger.log(
                        f"Failed to cancel timeout sell <{symbol}> order: {order_id}!")
        # failed or canceled
        elif order.status == webullsdk.ORDER_STATUS_FAILED or order.status == webullsdk.ORDER_STATUS_CANCELED:
            self._on_sell_order_failed(
                ticker, order.status, stop_tracking_ticker_after_order_filled)
        # unknown status
        else:
            raise exceptions.WebullOrderStatusError(
                f"Unknown order status '{order.status}' for order: {order_id}!")

    def check_cancel_order_done(self, ticker: TrackingTicker,
                                stop_tracking_ticker_after_order_canceled: bool = False):
        symbol = ticker.get_symbol()
        trading_logger.log(
            "Checking cancel order <{}> done...".format(symbol))
        order_id = ticker.get_pending_order_id()
        order = self.order_tracker.get_order(order_id)
        if not order:
            raise exceptions.WebullOrderNotFoundError()
        # failed or canceled
        if order.status == webullsdk.ORDER_STATUS_FAILED or order.status == webullsdk.ORDER_STATUS_CANCELED:
            # stop tracking cancel order
            self.stop_tracking_pending_cancel_order(ticker, order_id)
            resubmit_count = ticker.get_resubmit_order_count()
            retry_after_cancel, retry_limit = self.order_tracker.check_retry_after_cancel(
                order_id)
            # buy order
            if order.action == ActionType.BUY:
                if retry_after_cancel and resubmit_count < retry_limit and not self.trading_end:
                    # retry buy order
                    trading_logger.log(
                        f"Resubmitting buy order <{symbol}>...")
                    self.submit_buy_limit_order(
                        ticker, note=f"Resubmit buy order ({resubmit_count}).", retry=retry_after_cancel, retry_limit=retry_limit)
                    # increment resubmit order count
                    ticker.inc_resubmit_order_count()
                else:
                    if stop_tracking_ticker_after_order_canceled:
                        self.trading_tracker.stop_tracking(ticker)
            # sell order
            if order.action == ActionType.SELL:
                if retry_after_cancel and resubmit_count < retry_limit and not self.trading_end:
                    # retry sell order
                    trading_logger.log(
                        f"Resubmitting sell order <{symbol}>...")
                    self.submit_sell_limit_order(
                        ticker, note=f"Resubmit sell order ({resubmit_count}).", retry=retry_after_cancel, retry_limit=retry_limit)
                    # increment resubmit order count
                    ticker.inc_resubmit_order_count()
                else:
                    position_obj = ticker.get_position_obj()
                    # update setup
                    position_obj.setup = SetupType.ERROR_FAILED_TO_SELL
                    position_obj.save()
                    trading_logger.log(
                        "Failed to sell position <{}>!".format(symbol))
                    # send message
                    sms.notify_message(
                        "Failed to sell <{}> position, please check now!".format(symbol))
                    if stop_tracking_ticker_after_order_canceled:
                        self.trading_tracker.stop_tracking(ticker)
        elif order.status == webullsdk.ORDER_STATUS_FILLED or order.status == webullsdk.ORDER_STATUS_PARTIALLY_FILLED:
            # buy order
            if order.action == ActionType.BUY:
                self._on_buy_order_filled(ticker, order)
            # sell order
            if order.action == ActionType.SELL:
                self._on_sell_order_filled(ticker, order)
        elif ticker.is_order_timeout():
            raise exceptions.WebullOrderStatusError(
                f"Error cancel order status '{order.status}' for order {order_id}")

    def start_tracking_pending_buy_order(self, ticker: TrackingTicker, order_id: str, entry_note: str = "",
                                         retry: bool = False, retry_limit: int = 0):
        ticker.reset_pending_order()
        # mark pending buy
        ticker.set_pending_buy(True)
        ticker.set_pending_order_id(order_id)
        ticker.set_pending_order_time(datetime.now())
        # tracking order
        self.order_tracker.start_tracking(
            order_id, self.get_setup(), entry_note, retry, retry_limit)

    def stop_tracking_pending_buy_order(self, ticker: TrackingTicker, order_id: str):
        if ticker.get_pending_order_id() == order_id:
            ticker.reset_pending_order()
        ticker.set_last_buy_time(datetime.now())
        self.order_tracker.stop_tracking(order_id)

    def start_tracking_pending_sell_order(self, ticker: TrackingTicker, order_id: str, exit_note: str = "",
                                          retry: bool = True, retry_limit: int = 20):
        ticker.reset_pending_order()
        # mark pending sell
        ticker.set_pending_sell(True)
        ticker.set_pending_order_id(order_id)
        ticker.set_pending_order_time(datetime.now())
        # tracking order
        self.order_tracker.start_tracking(
            order_id, self.get_setup(), exit_note, retry, retry_limit)

    def stop_tracking_pending_sell_order(self, ticker: TrackingTicker, order_id: str):
        if ticker.get_pending_order_id() == order_id:
            ticker.reset_pending_order()
        ticker.set_last_sell_time(datetime.now())
        self.order_tracker.stop_tracking(order_id)

    def start_tracking_pending_cancel_order(self, ticker: TrackingTicker, order_id: str, cancel_note: str = ""):
        ticker.reset_pending_order()
        # mark pending sell
        ticker.set_pending_cancel(True)
        ticker.set_pending_order_id(order_id)
        ticker.set_pending_order_time(datetime.now())
        # tracking order
        self.order_tracker.start_tracking(
            order_id, self.get_setup(), cancel_note)

    def stop_tracking_pending_cancel_order(self, ticker: TrackingTicker, order_id: str):
        if ticker.get_pending_order_id() == order_id:
            ticker.reset_pending_order()
        self.order_tracker.stop_tracking(order_id)

    def update_pending_swing_position(self, symbol, order_response, position, cost, quant, buy_time, setup):
        order_id = utils.get_order_id_from_response(
            order_response, paper=self.paper)
        if order_id:
            if not position:
                # create swing position
                position = SwingPosition(
                    symbol=symbol,
                    order_ids=order_id,
                    total_cost=cost * quant,
                    quantity=quant,
                    units=1,
                    buy_time=buy_time,
                    buy_date=buy_time.date(),
                    setup=setup,
                    require_adjustment=True,
                )
            else:
                # update swing position for add unit
                position.order_ids = "{},{}".format(
                    position.order_ids, order_id)
                position.total_cost = position.total_cost + cost * quant
                position.quantity = position.quantity + quant
                position.units = position.units + 1
                # temp add unit, stop loss price
                position.add_unit_price = constants.MAX_SECURITY_PRICE
                position.stop_loss_price = 0
                position.require_adjustment = True
            position.save()
        else:
            trading_logger.log(
                "⚠️  Invalid swing buy order response: {}".format(order_response))

    def update_pending_swing_trade(self, symbol, order_response, position, price, sell_time, manual_request=None):
        order_id = utils.get_order_id_from_response(
            order_response, paper=self.paper)
        if order_id:
            order_ids = "{},{}".format(position.order_ids, order_id)
            # create swing position
            trade = SwingTrade(
                symbol=symbol,
                order_ids=order_ids,
                total_cost=position.total_cost,
                total_sold=price * position.quantity,
                quantity=position.quantity,
                units=position.units,
                buy_time=position.buy_time,
                buy_date=position.buy_date,
                sell_time=sell_time,
                sell_date=sell_time.date(),
                setup=position.setup,
                require_adjustment=True,
            )
            trade.save()
            # clear position
            position.delete()
            # clear manual request if exist
            if manual_request:
                manual_request.delete()
        else:
            trading_logger.log(
                "⚠️  Invalid swing sell order response: {}".format(order_response))

    def get_position(self, ticker: TrackingTicker):
        symbol = ticker.get_symbol()
        positions = webullsdk.get_positions()
        if positions == None:
            return None
        ticker_position = None
        for position in positions:
            if position['ticker']['symbol'] == symbol:
                ticker_position = position
                break
        return ticker_position

    # clear all positions
    def clear_positions(self):
        for ticker_id in self.trading_tracker.get_tickers():
            ticker = self.trading_tracker.get_ticker(ticker_id)
            self.clear_position(ticker)

    def clear_position(self, ticker: TrackingTicker):

        if ticker.is_pending_buy():
            self.check_buy_order_done(ticker)
            return

        if ticker.is_pending_sell():
            self.check_sell_order_done(ticker)
            return

        if ticker.is_pending_cancel():
            self.check_cancel_order_done(ticker)
            return

        holding_quantity = ticker.get_positions()
        if holding_quantity == 0:
            # remove from tracking
            self.trading_tracker.stop_tracking(ticker)
            return

        self.submit_sell_limit_order(
            ticker, note="Clear position.", retry=True, retry_limit=50)

    def track_rest_positions(self):
        for ticker_id in self.trading_tracker.get_tickers():
            ticker = self.trading_tracker.get_ticker(ticker_id)
            symbol = ticker.get_symbol()
            position_obj = ticker.get_position_obj()
            if position_obj:
                # update setup
                position_obj.setup = SetupType.ERROR_FAILED_TO_SELL
                position_obj.save()
                # send message
                sms.notify_message(
                    "Failed to clear <{}> position, please check now!".format(symbol))
            # remove from tracking
            self.trading_tracker.stop_tracking(ticker)

    def get_buy_order_limit(self, ticker: TrackingTicker) -> float:
        if self.is_regular_market_hour():
            return self.order_amount_limit
        return self.extended_order_amount_limit

    def get_buy_price(self, ticker: TrackingTicker) -> float:
        ticker_id = ticker.get_id()
        quote = webullsdk.get_quote(ticker_id=ticker_id)
        trading_logger.log_level2(quote)
        if self.is_regular_market_hour():
            last_price = utils.get_attr_to_float_or_none(quote, 'close')
        else:
            last_price = utils.get_attr_to_float_or_none(quote, 'pPrice')
        bid_price = webullsdk.get_bid_price_from_quote(quote) or 0.0
        buy_price = last_price
        if bid_price > last_price:
            ask_price = webullsdk.get_ask_price_from_quote(quote)
            if ask_price:
                buy_price = round((ask_price + bid_price) / 2, 2)
            else:
                buy_price = bid_price + 0.1
        # return min(ask_price, round(last_price * 1.01, 2))
        return buy_price

    def get_sell_price(self, ticker: TrackingTicker) -> float:
        ticker_id = ticker.get_id()
        symbol = ticker.get_symbol()
        quote = webullsdk.get_quote(ticker_id=ticker_id)
        trading_logger.log_level2(quote)
        # ask_price = webullsdk.get_ask_price_from_quote(quote)
        # if ask_price == None or bid_price == None:
        #     return None
        # sell_price = max(
        #     ask_price - 0.1, round((ask_price + bid_price) / 2, 2))
        # return sell_price
        if self.is_regular_market_hour():
            last_price = utils.get_attr_to_float_or_none(quote, 'close')
        else:
            last_price = utils.get_attr_to_float_or_none(quote, 'pPrice')
        bid_price = webullsdk.get_bid_price_from_quote(quote)
        if not bid_price:
            trading_logger.log(f"<{symbol}> bid price not existed!")
            trading_logger.log(json.dumps(quote))
        return bid_price or last_price

    def get_stop_loss_price(self, bars: pd.DataFrame) -> float:
        return 0.0

    def get_scale_stop_loss_price(self, bars: pd.DataFrame) -> float:
        return 0.0

    def get_dip_stop_loss_price(self, bars: pd.DataFrame) -> float:
        return 0.0