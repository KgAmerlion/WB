from __future__ import annotations

import time

import requests
from requests.structures import CaseInsensitiveDict
from datetime import datetime, timedelta
import pandas as pd
import sqlite3 as sq

headers = CaseInsensitiveDict()


def report(user: tuple):
    db = sq.connect('my_bd.sql')
    cur = db.cursor()
    cur.execute(
        "SELECT name, wb_token FROM profiles WHERE user_id == '%i'" % user[0])
    info = cur.fetchall()
    cur.close()
    db.close()
    # выгрузка
    if len(info) != 0:
        for j in range(len(info)):
            api = info[j][1]
            headers["Authorization"] = api
            init = 'https://statistics-api.wildberries.ru/api/v1/supplier/'

            date_t = datetime.today()
            date_y = date_t - timedelta(days=1)

            date_t_now = date_t.strftime("%Y-%m-%dT%H:%M:%S")
            date_t = date_t.strftime("%Y-%m-%d")


            date_y_now =  date_y
            date_y = date_y.strftime("%Y-%m-%d")

            results = f'{init}orders?dateFrom={date_t}&flag=1'
            orders_t = pd.DataFrame(requests.get(results, headers=headers).json())  # заказы на текущую дату

            results = f'{init}orders?dateFrom={date_y}&flag=1'
            orders_y = pd.DataFrame(requests.get(results, headers=headers).json())  # заказы на вчера

            orders_t['date'] = pd.to_datetime(orders_t['date'])
            orders_t['day'] = orders_t['date'].dt.strftime('%Y-%m-%d')

            orders_y['date'] = pd.to_datetime(orders_y['date'])
            orders_y['day'] = orders_y['date'].dt.strftime('%Y-%m-%d')


            ttl_sum_orders_t = round(sum(orders_t.query('day == @date_t')['priceWithDisc'])) # сумма на текущую дату
            ttl_sum_orders_y_now = round(sum(orders_y.query('date <=  @date_y_now')['priceWithDisc'])) # сумма на вчера к текущему времени +
            ttl_sum_orders_y = round(sum(orders_y.query('day==@date_y')['priceWithDisc'])) # сумма на вчера
            return ttl_sum_orders_t, ttl_sum_orders_y_now, ttl_sum_orders_y, info[j][0]
