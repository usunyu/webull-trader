from datetime import date
from django.shortcuts import render
from scripts import utils, config
from old_ross.enums import ActionType
from old_ross.models import WebullAccountStatistics, WebullOrder

# Create your views here.


def index(request):
    today = date.today()

    # account type data
    account_type = utils.get_account_type_for_render()

    # account statistics data
    net_account_value = {
        "value": "$0.0",
        "total_pl": "0.0",
        "total_pl_style": "badge-soft-dark",
        "total_pl_rate": "0.0%",
        "total_pl_rate_style": "badge-soft-dark",
    }
    day_profit_loss = {
        "value": "$0.0",
        "value_style": "",
        "day_pl_rate": "0.0%",
        "day_pl_rate_style": "badge-soft-dark",
    }

    last_acc_status = WebullAccountStatistics.objects.last()
    if last_acc_status:
        net_account_value["value"] = "${}".format(
            last_acc_status.net_liquidation)

        net_account_value["total_pl"] = "{}".format(
            last_acc_status.total_profit_loss)
        if last_acc_status.total_profit_loss > 0:
            net_account_value["total_pl"] = "+" + net_account_value["total_pl"]
            net_account_value["total_pl_style"] = "badge-soft-success"
        elif last_acc_status.total_profit_loss < 0:
            net_account_value["total_pl_style"] = "badge-soft-danger"

        net_account_value["total_pl_rate"] = "{}%".format(
            last_acc_status.total_profit_loss_rate * 100)
        if last_acc_status.total_profit_loss_rate > 0:
            net_account_value["total_pl_rate"] = "+" + \
                net_account_value["total_pl_rate"]
            net_account_value["total_pl_rate_style"] = "badge-soft-success"
        elif last_acc_status.total_profit_loss_rate < 0:
            net_account_value["total_pl_rate_style"] = "badge-soft-danger"

    today_acc_status = WebullAccountStatistics.objects.filter(
        date=today).first()
    if today_acc_status and last_acc_status:
        day_profit_loss["value"] = "${}".format(
            abs(today_acc_status.day_profit_loss))
        day_pl_rate = today_acc_status.day_profit_loss / \
            (last_acc_status.net_liquidation - today_acc_status.day_profit_loss)
        day_profit_loss["day_pl_rate"] = "{}%".format(
            round(day_pl_rate * 100, 2))
        if today_acc_status.day_profit_loss > 0:
            day_profit_loss["value"] = "+" + day_profit_loss["value"]
            day_profit_loss["value_style"] = "text-success"
            day_profit_loss["day_pl_rate"] = "+" + \
                day_profit_loss["day_pl_rate"]
            day_profit_loss["day_pl_rate_style"] = "badge-soft-success"
        elif today_acc_status.day_profit_loss < 0:
            day_profit_loss["value"] = "-" + day_profit_loss["value"]
            day_profit_loss["value_style"] = "text-danger"
            day_profit_loss["day_pl_rate"] = "-" + \
                day_profit_loss["day_pl_rate"]
            day_profit_loss["day_pl_rate_style"] = "badge-soft-danger"

    acc_status_list = WebullAccountStatistics.objects.all()
    # net assets chart
    net_assets_daily_values = []
    net_assets_daily_dates = []
    # profit loss chart
    profit_loss_daily_values = []
    profit_loss_daily_dates = []

    for acc_status in acc_status_list:
        net_assets_daily_values.append(acc_status.net_liquidation)
        net_assets_daily_dates.append(acc_status.date.strftime("%Y/%m/%d"))
        profit_loss_daily_values.append(
            utils.get_color_bar_chart_item_for_render(acc_status.day_profit_loss))
        profit_loss_daily_dates.append(acc_status.date.strftime("%Y/%m/%d"))

    net_assets = {
        'daily_values': net_assets_daily_values,
        'daily_dates': net_assets_daily_dates,
        'weekly_values': [],  # TODO
        'weekly_dates': [],  # TODO
        'monthly_values': [],  # TODO
        'monthly_dates': [],  # TODO
    }

    profit_loss = {
        'daily_values': profit_loss_daily_values,
        'daily_dates': profit_loss_daily_dates,
        'weekly_values': [],  # TODO
        'weekly_dates': [],  # TODO
        'monthly_values': [],  # TODO
        'monthly_dates': [],  # TODO
    }

    return render(request, 'old_ross/index.html', {
        "account_type": account_type,
        "net_account_value": net_account_value,
        "day_profit_loss": day_profit_loss,
        "net_assets": net_assets,
        "profit_loss": profit_loss,
    })


def calendar(request):
    today = date.today()

    profit_events = {
        "events": [],
        "color": config.PROFIT_COLOR,
    }

    loss_events = {
        "events": [],
        "color": config.LOSS_COLOR,
    }

    acc_status_list = WebullAccountStatistics.objects.all()

    for acc_status in acc_status_list:
        day_pl_rate = acc_status.day_profit_loss / \
            (acc_status.net_liquidation - acc_status.day_profit_loss)
        # count trades
        filled_orders = WebullOrder.objects.filter(filled_time__year=acc_status.date.year, filled_time__month=acc_status.date.month, filled_time__day=acc_status.date.day).filter(action=ActionType.BUY)
        trades_count = len(filled_orders)
        # events
        if acc_status.day_profit_loss < 0:
            loss_events['events'].append({
                "title": "-${} ({}%)".format(abs(acc_status.day_profit_loss), round(day_pl_rate * 100, 2)),
                "start": acc_status.date.strftime("%Y-%m-%d"),
                "url": "/",
            })
            loss_events['events'].append({
                "title": "{} trades".format(trades_count),
                "start": acc_status.date.strftime("%Y-%m-%d"),
                "url": "/",
            })
        else:
            profit_events['events'].append({
                "title": "+${} (+{}%)".format(abs(acc_status.day_profit_loss), round(day_pl_rate * 100, 2)),
                "start": acc_status.date.strftime("%Y-%m-%d"),
                "url": "/",
            })
            profit_events['events'].append({
                "title": "{} trades".format(trades_count),
                "start": acc_status.date.strftime("%Y-%m-%d"),
                "url": "/",
            })

    return render(request, 'old_ross/calendar.html', {
        "initial_date": today.strftime("%Y-%m-%d"),
        "profit_events": profit_events,
        "loss_events": loss_events,
    })
