from __future__ import annotations

import asyncio

from aiogram import F,  Router, Bot
from aiogram.filters import  CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state, State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message, KeyboardButton)
from aiogram.utils.keyboard import ReplyKeyboardBuilder
import requests
from requests.structures import CaseInsensitiveDict
from datetime import datetime, timedelta
import pandas as pd

from apscheduler.schedulers.background import BackgroundScheduler

import sqlite3 as sq
headers = CaseInsensitiveDict()
from config import Config, load_config, load_config_debug
DEBUG = True

if DEBUG:
    config: Config = load_config_debug()
    BOT_TOKEN_DEBUG: str = config.tg_bot.token
    bot = Bot(token=BOT_TOKEN_DEBUG)
else:
    config: Config = load_config()
    BOT_TOKEN: str = config.tg_bot.token
    bot = Bot(token=BOT_TOKEN)
def report(user: tuple, bot: Bot, chat_id: int):
    print(f'{user[0]}')
    db = sq.connect('my_bd.sql')
    cur = db.cursor()
    cur.execute(
        "SELECT name, wb_token FROM profiles WHERE user_id == '%i'" % user[0])
    info = cur.fetchall()
    cur.close()
    db.close()
#await bot.send_message(chat_id, f'{info}')

    # выгрузка
    if len(info) != 0:
        for j in range(len(info)):
            api = info[j][1]
            headers["Authorization"] = api
            init = 'https://statistics-api.wildberries.ru/api/v1/supplier/'

            date_t = datetime.today()
            date_y = date_t - timedelta(days=1)

            date_y.strftime("%Y-%m-%d")
            date_t.strftime("%Y-%m-%dT%H:%M:%S")

            results = {i: f'{init}{i}?dateFrom={date_t}&flag=1' for i in ['orders']}
            orders_t = pd.DataFrame(requests.get(results['orders'], headers=headers).json())  # заказы на текущую дату

            results = {i: f'{init}{i}?dateFrom={date_y}&flag=1' for i in ['orders']}
            orders_y = pd.DataFrame(requests.get(results['orders'], headers=headers).json())  # заказы на вчера

            ttl_sum_orders_t = round(sum(orders_t['priceWithDisc']))
            ttl_sum_orders_y = round(sum(orders_y['priceWithDisc']))
            dif = ttl_sum_orders_t-ttl_sum_orders_y
            print('hurray')
            return  ttl_sum_orders_t, ttl_sum_orders_y
            # await bot.send_message(chat_id, f"Прогноз {info[j][0]}: {ttl_sum_orders_y+dif}\n"
            #                                 f"Сегодня: {ttl_sum_orders_t}\n"
            #                                 f"Вчера: {ttl_sum_orders_y}\n"
            #                                 f"Разница: {dif}")
    #else:
         #await bot.send_message(chat_id, f'У вас еще нет магазинов')
    #     apscheduler.remove_job('subscription_{user}')