from __future__ import annotations
import requests
from requests.structures import CaseInsensitiveDict
from datetime import datetime, timedelta
import pandas as pd
import sqlite3 as sq

headers = CaseInsensitiveDict()


def report(user: tuple):
    print(f'{user[0]}')
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

            date_y.strftime("%Y-%m-%d%H:%M:%S")
            date_t.strftime("%Y-%m-%dT%H:%M:%S")

            results = f'{init}orders?dateFrom={date_t}&flag=1'
            orders_t = pd.DataFrame(requests.get(results, headers=headers).json())  # заказы на текущую дату

            results = f'{init}orders?dateFrom={date_y}&flag=1'
            orders_y = pd.DataFrame(requests.get(results, headers=headers).json())  # заказы на вчера

            ttl_sum_orders_t = round(sum(orders_t['priceWithDisc']))
            ttl_sum_orders_y = round(sum(orders_y['priceWithDisc']))
            print('hurray')
            return ttl_sum_orders_t, ttl_sum_orders_y
