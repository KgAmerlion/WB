from __future__ import annotations

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

from apscheduler.schedulers.asyncio import AsyncIOScheduler

import sqlite3 as sq

from config import Config, load_config, load_config_debug

DEBUG = False

if DEBUG:
    config: Config = load_config_debug()
    BOT_TOKEN_DEBUG: str = config.tg_bot.token
    bot = Bot(token=BOT_TOKEN_DEBUG)
else:
    config: Config = load_config()
    BOT_TOKEN: str = config.tg_bot.token
    bot = Bot(token=BOT_TOKEN)

headers = CaseInsensitiveDict()

storage = MemoryStorage()

router = Router()
# Инициализируем билдер
kb_builder = ReplyKeyboardBuilder()

# Создаем список с кнопками
buttons: list[KeyboardButton] = [
    KeyboardButton(text="Добавить магазин")
    , KeyboardButton(text="Удалить магазин")
    , KeyboardButton(text="Отмена")
    , KeyboardButton(text="Список магазинов")
    , KeyboardButton(text="Рассылка")
]

# Распаковываем список с кнопками в билдер, указываем, что
# в одном ряду должно быть 3 кнопки
kb_builder.row(*buttons, width=3)

# Создаем "базу данных" пользователей
user_dict = {}
name = None
user = None
status = 1


class Add(StatesGroup):
    name = State()  # Will be represented in storage as 'Form:name
    wb_token = State()


class Delete(StatesGroup):
    name = State()  # Will be represented in storage as 'Form:name


@router.message(CommandStart(), StateFilter(default_state))
async def process_start_command(message: Message):
    db = sq.connect('my_bd.sql')
    cur = db.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS profiles (user_id int, name TEXT, wb_token TEXT)')
    db.commit()
    cur.close()
    db.close()

    await message.answer(text=f"Привет, <b>{message.from_user.full_name}</b>. Этот бот поможет сделить за продажами.",
                         reply_markup=kb_builder.as_markup(resize_keyboard=True)
                         )


@router.message(F.text == "Отмена")
async def cancel_states(message: Message, state: FSMContext):
    await state.clear()
    await message.reply('Выберите действие')


# добавление магазина
@router.message(F.text == "Добавить магазин")
async def process_fillform_command(message: Message, state: FSMContext):
    if status != 0:
        await (message.answer(text=f'Пожалуйста, введите название магазина'))
        # Устанавливаем состояние ожидания ввода имени
        await state.set_state(Add.name)
    else:
        await (message.answer(text=f'Повторите попытку'))


@router.message(StateFilter(Add.name), F.text)
async def process_name_sent(message: Message, state: FSMContext):
    global name
    # Cохраняем введенное имя в хранилище по ключу "name"
    await state.update_data(name=message.text)
    if message.text in ("Список магазинов", "Добавить магазин", "Удалить магазин", "Рассылка"):
        await message.answer(text='Некорректное название. Введите повторно')
    else:
        shop_to_add = await state.get_data()
        db = sq.connect('my_bd.sql')
        cur = db.cursor()
        cur.execute(
            "SELECT name FROM profiles WHERE name == '%s' AND user_id == '%i'" % (
                shop_to_add['name'], message.from_user.id))
        _to_add = cur.fetchall()
        db.commit()
        if len(_to_add) != 0:
            await message.answer(text='Магазин с таким названием уже есть')
            # Завершаем машину состояний
        else:
            await message.answer(text='Спасибо!\n\nА теперь введите API вашего магазина')
            # Устанавливаем состояние ожидания ввода API
            await state.set_state(Add.wb_token)
        cur.close()
        db.close()
        # Завершаем машину состояний
        await state.clear()


@router.message(StateFilter(Add.wb_token), F.text)
async def process_api(message: Message, state: FSMContext):
    # Cохраняем данные о API
    await state.update_data(wb_token=message.text)
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
    global status
    await message.answer(text='Пожалуйста, введите название магазина, который хотите удалить')
    status = 0
    # Устанавливаем состояние ожидания ввода имени
    await state.set_state(Delete.name)


@router.message(StateFilter(Delete.name), F.text)
async def delete_shop(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    if message.text in ("Список магазинов", "Удалить магазин", "Рассылка"):
        await message.answer(text='Некорректное название. Введите повторно')
    else:
        shop_to_delete = await state.get_data()
        db = sq.connect('my_bd.sql')
        cur = db.cursor()
        cur.execute(
            "SELECT name FROM profiles WHERE name == '%s' AND user_id == '%i'" % (
            shop_to_delete['name'], message.from_user.id))
        _to_delete = cur.fetchall()
        if len(_to_delete) == 0:
            await message.answer(text='Такого магазина нет в списке')
        else:
            cur.execute(
                "DELETE FROM profiles WHERE name == '%s' AND user_id == '%i'" % (
                shop_to_delete['name'], message.from_user.id))
            db.commit()
            await message.answer(text='Магазин удален')
        cur.close()
        db.close()
        # Завершаем машину состояний
        await state.clear()


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
    callback_data='dispatch_on'
)
button_2 = InlineKeyboardButton(
    text='Отключить рассылку',
    callback_data='dispatch_off'
)
keyboard_inline_sub = InlineKeyboardMarkup(
    inline_keyboard=[[button_1], [button_2]]
)

@router.message(F.text == 'Рассылка')
async def subs_name_shop(message: Message, bot: Bot, apscheduler: AsyncIOScheduler):
    global user
    user = message.from_user.id
    await message.answer(
            text='Что необходимо сделать?',
            reply_markup=keyboard_inline_sub
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


@router.callback_query(F.data == 'dispatch_on')
async def process_button_1_press(callback: CallbackQuery, bot: Bot, apscheduler: AsyncIOScheduler):
    db = sq.connect('my_bd.sql')
    cur = db.cursor()
    cur.execute(
        "SELECT wb_token FROM profiles WHERE user_id == '%i'" % user)
    info = cur.fetchall()
    cur.close()
    db.close()
    if len(info) != 0:
        await callback.message.answer(f'Рассылка включена. Отчет будет присылаться каждые 3 часа')
        apscheduler.add_job(report,
                            trigger='interval',
                            seconds=30,
                            kwargs={'bot': bot,
                                    'chat_id': user,
                                    'apscheduler': apscheduler},
                            id=f'subscription')

    else:
        await callback.message.answer(f'У вас еще нет магазинов')


@router.callback_query(F.data == 'dispatch_off')
async def process_button_1_press(callback: CallbackQuery, apscheduler: AsyncIOScheduler):
    jobs = apscheduler.print_jobs()
    print(jobs)
    if jobs is not None:
        await callback.message.answer(f'Рассылка отключена')
        apscheduler.remove_job('subscription')
    else:
        await callback.message.answer(f'Вы еще не подключили рассылку')

# ввод посторонних сообщений = возврат в начало
# @dp.message()
# async def echo_message(message: types.Message):
#     await message.answer(f"Введи /start",
#                          parse_mode=ParseMode.HTML,
#                          )
