from django.urls import path, include
from webull_trader import views

urlpatterns = [
    path('', views.index, name='dashboard'),
    path('day-analytics', views.day_analytics, name='day_analytics'),
    path('day-analytics/<str:date>', views.day_analytics_date, name='day_analytics_date'),
    path('day-analytics/<str:date>/<str:symbol>',
         views.day_analytics_date_symbol, name='day_analytics_date_symbol'),
    path('day-reports/price', views.day_reports_price, name='day_reports_price'),
    path('day-reports/mktcap', views.day_reports_mktcap, name='day_reports_mktcap'),
    path('day-reports/float', views.day_reports_float, name='day_reports_float'),
    path('day-reports/turnover', views.day_reports_turnover, name='day_reports_turnover'),
    path('day-reports/short', views.day_reports_short, name='day_reports_short'),
    path('day-reports/hourly', views.day_reports_hourly, name='day_reports_hourly'),
]
