from __future__ import annotations

from aiogram import F, types, Router, Bot
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state, State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message)
import requests
from requests.structures import CaseInsensitiveDict
from datetime import datetime, timedelta
import pandas as pd
import config
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import sqlite3 as sq

headers = CaseInsensitiveDict()

storage = MemoryStorage()

router = Router()
bot = Bot(token=config.BOT_TOKEN)
buttonlist = [
    types.KeyboardButton(text="Добавить магазин")
    , types.KeyboardButton(text="Удалить магазин")
    , types.KeyboardButton(text="Отмена")
    , types.KeyboardButton(text="Список магазинов")
    , types.KeyboardButton(text="Рассылка")
]
kb = [buttonlist]
kb = types.ReplyKeyboardMarkup(
    keyboard=kb,
    resize_keyboard=True,
    one_time_keyboard=False
)
# Создаем "базу данных" пользователей
user_dict = {}
name = None
user = []

class Form(StatesGroup):
    name = State()  # Will be represented in storage as 'Form:name
    wb_token = State()


@router.message(CommandStart(), StateFilter(default_state))
async def process_start_command(message: Message):
    db = sq.connect('my_bd.sql')
    cur = db.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS profiles (user_id int, name TEXT, wb_token TEXT)')
    db.commit()
    cur.close()
    db.close()

    await message.answer(text=f"Привет, <b>{message.from_user.full_name}</b>. Этот бот поможет сделить за продажами.",
                         reply_markup=kb
                         )


@router.message(F.text == "Отмена")
async def cancel_states(message: Message, state: FSMContext):
    await state.clear()
    await message.reply('Выберите действие')
    # Устанавливаем состояние ожидания ввода имени
    await state.set_state(Form.name)


# добавление магазина
@router.message(F.text == "Добавить магазин")
async def process_fillform_command(message: Message, state: FSMContext):
    await (message.answer(text=f'Пожалуйста, введите название магазина'))
    # Устанавливаем состояние ожидания ввода имени
    await state.set_state(Form.name)


@router.message(StateFilter(Form.name), F.text)
async def process_name_sent(message: Message, state: FSMContext):
    global name
    # Cохраняем введенное имя в хранилище по ключу "name"
    await state.update_data(name=message.text)
    if message.text in ("Список магазинов", "Добавить магазин", "Удалить магазин", "Рассылка"):
        await message.answer(text='Некорректное название. Введите повторно')
    else:
        await message.answer(text='Спасибо!\n\nА теперь введите API вашего магазина')
        # Устанавливаем состояние ожидания ввода API
        await state.set_state(Form.wb_token)

big_button_1 = InlineKeyboardButton(
    text='Включить рассылку',
    callback_data='big_button_1_pressed'
)
keyboard_inline = InlineKeyboardMarkup(
    inline_keyboard=[[big_button_1]]
)


@router.message(StateFilter(Form.wb_token), F.text)
async def process_api(message: Message, state: FSMContext):
    # Cохраняем данные о API
    await state.update_data(wb_token=message.text)
    #await message.answer(text='Спасибо!\n\n Сохраняем магазин')

    # Добавляем в "базу данных" анкету пользователя
    # по ключу id пользователя
    user_dict[message.from_user.id] = await state.get_data()

    db = sq.connect('my_bd.sql')
    cur = db.cursor()

    cur.execute(
            'INSERT INTO profiles VALUES (?, ?, ?)', (message.from_user.id,
                                                      user_dict[message.from_user.id]['name'],
                                                      user_dict[message.from_user.id]['wb_token']))
    db.commit()
    cur.close()
    db.close()

    # Завершаем машину состояний
    await state.clear()
    await message.answer(text='Магазин добавлен')
                         # reply_markup=keyboard_inline)


# удаление магазина
@router.message(F.text == "Удалить магазин")
async def delete_name_shop(message: Message, state: FSMContext):
    await message.answer(text='Пожалуйста, введите название магазина, который хотите удалить')
    # Устанавливаем состояние ожидания ввода имени
    await state.set_state(Form.name)


@router.message(StateFilter(Form.name), F.text)
async def delete_shop(message: Message, state: FSMContext):
    if message.text in ("Список магазинов", "Добавить магазин", "Удалить магазин", "Рассылка"):
        await message.answer(text='Некорректное название. Введите повторно')
    else:
        # Cохраняем название магазина для удаления
        await state.update_data(name=message.text)

    shop_to_delete = await state.get_data()
    db = sq.connect('my_bd.sql')
    cur = db.cursor()

    cur.execute(
            "DELETE FROM profiles WHERE name == '%s' AND user_id == '%i'" % (shop_to_delete['name'], message.from_user.id))
    db.commit()
    cur.close()
    db.close()
    # Завершаем машину состояний
    await state.clear()
    await message.answer(text='Магазин удален')


# список магазинов
@router.message(F.text == 'Список магазинов')
async def process_button_2_press(message: Message, state: FSMContext):
    db = sq.connect('my_bd.sql')
    cur = db.cursor()

    cur.execute(
        "SELECT name FROM profiles WHERE user_id == '%i'" % message.from_user.id)

    profiles = cur.fetchall()
    info = ''
    i = 1
    for el in profiles:
        info += f"{i}. {el[0]}\n"
        i += 1
    cur.close()
    db.close()

    if len(info) == 0:
        await message.answer(text='У вас еще нет магазинов')
    else:
        await message.answer(info)


# рассылка
button_1 = InlineKeyboardButton(
    text='Включить рассылку',
    callback_data='big_button_1_pressed'
)
button_2 = InlineKeyboardButton(
    text='Отключить рассылку',
    callback_data='big_button_1_pressed'
)
keyboard_inline_sub = InlineKeyboardMarkup(
    inline_keyboard=[[button_1], [button_2]]
)


async def report(bot, chat_id, apscheduler):
    db = sq.connect('my_bd.sql')
    cur = db.cursor()
    cur.execute(
        "SELECT name, wb_token FROM profiles WHERE user_id == '%i'" % chat_id)

    info = cur.fetchall()
    cur.close()
    db.close()
    # выгрузка
    if len(info) != 0:
        for j in range(len(info)):
            api = info[j][1]
            headers["Authorization"] = api
            init = 'https://statistics-api.wildberries.ru/api/v1/supplier/'

            date_from = datetime.today()

            results = {i: f'{init}{i}?dateFrom={date_from}&flag=1' for i in ['sales', 'orders']}
            sales = pd.DataFrame(requests.get(results['sales'], headers=headers).json())  # продажи
            orders = pd.DataFrame(requests.get(results['orders'], headers=headers).json())  # заказы

            sales['date_column'] = pd.to_datetime(sales['date']).dt.date
            orders['date_column'] = pd.to_datetime(orders['date']).dt.date

            ttl_sum_sales = sum(sales['priceWithDisc'])
            ttl_sum_orders = sum(orders['priceWithDisc'])
            await bot.send_message(chat_id, f"Магазин: {info[j][0]}\n"
                                            f"Выкупили: {ttl_sum_sales}\n"
                                            f"Заказали: {ttl_sum_orders}")
    else:
        await bot.send_message(chat_id, f'У вас еще нет магазинов')
        apscheduler.remove_job('subscription')


@router.message(F.text == 'Рассылка')
async def subs_name_shop(message: Message, bot: Bot, apscheduler: AsyncIOScheduler):
    user = message.from_user.id

    db = sq.connect('my_bd.sql')
    cur = db.cursor()
    cur.execute(
        "SELECT wb_token FROM profiles WHERE user_id == '%i'" %  user)
    info = cur.fetchall()
    cur.close()
    db.close()
    if len(info) != 0:
        await message.answer(f'Рассылка включена. Отчет будет присылаться каждые 3 часа')
        apscheduler.add_job(report,
                            trigger='interval',
                            seconds=30,
                            kwargs={'bot': bot,
                                    'chat_id': user,
                                    'apscheduler': apscheduler},
                            id=f'subscription')

    else:
        await message.answer(f'У вас еще нет магазинов')



# ввод посторонних сообщений = возврат в начало
# @dp.message()
# async def echo_message(message: types.Message):
#     await message.answer(f"Введи /start",
#                          parse_mode=ParseMode.HTML,
#                          )
