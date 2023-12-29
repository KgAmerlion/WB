import logging
import traceback
from datetime import datetime

from aiogram import Dispatcher
import asyncio
import threading
import schedule
from aiogram import F, Router, Bot
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state, State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message, KeyboardButton)
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from requests.structures import CaseInsensitiveDict
import time
import notifiers
import sqlite3 as sq
import report
from config import Config, load_config, load_config_debug

# Инициализируем логгер
logger = logging.getLogger(__name__)

tg = notifiers.get_notifier("telegram")

DEBUG = True

if DEBUG:
    config: Config = load_config_debug()
    BOT_TOKEN_DEBUG: str = config.tg_bot.token
    bot = Bot(token=BOT_TOKEN_DEBUG, parse_mode=ParseMode.HTML)
else:
    config: Config = load_config()
    BOT_TOKEN: str = config.tg_bot.token
    bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)

storage = MemoryStorage()
headers = CaseInsensitiveDict()

storage = MemoryStorage()
today = 0.
y_day = 0.


async def get_all_users():
    db = sq.connect('my_bd.sql')
    cur = db.cursor()
    cur.execute(
        "SELECT user_id FROM profiles WHERE dispatch != '%s'" % '0')
    data = cur.fetchall()
    return data


def dispatch_is_on(token):
    logger.info(f'Starting dispatch {datetime.now()}')
    global today, y_day
    db = sq.connect('my_bd.sql')
    cur = db.cursor()
    cur.execute(
        "SELECT DISTINCT user_id FROM profiles WHERE dispatch != '%s'" % '0')
    users = cur.fetchall()
    if len(users) != 0:
        for i in users:
            today, y_day, shop_name = report.report(i)
            dif = today - y_day
            text = f"Магазин : {shop_name}\n" \
                   f"Прогноз : {y_day + dif}\n" \
                   f"Сегодня: {today}\n"\
                   f"Вчера: {y_day}\n"\
                   f"Разница: {dif}"
            tg.notify(message=text, token=token, chat_id=i[0])
    logger.info('Dispatch is complete', {datetime.now()})
def not_change(token):
    db = sq.connect('my_bd.sql')
    cur = db.cursor()
    cur.execute(
        "SELECT DISTINCT user_id FROM profiles")
    text = "Собираем отчет. Не добавляйте и не удаляйте магазины до получения отчета."
    users = cur.fetchall()
    for i in users:
        tg.notify(message=text, token=token, chat_id=i[0])


router = Router()

# Инициализируем билдер
kb_builder = ReplyKeyboardBuilder()

# Создаем список с кнопками
buttons: list[KeyboardButton] = [
    KeyboardButton(text="Добавить магазин")
    , KeyboardButton(text="Удалить магазин")
    , KeyboardButton(text="Отмена")
    , KeyboardButton(text="Список магазинов")
    , KeyboardButton(text="Отчет $")
]

# Распаковываем список с кнопками в билдер, указываем, что
# в одном ряду должно быть 3 кнопки
kb_builder.row(*buttons, width=3)

# Создаем "базу данных" пользователей
user_dict = {}
name = None
user = None
status = 1  # флаг для регулировки нажатия кнопок удалить/добавить


class Add(StatesGroup):
    name = State()  # Will be represented in storage as 'Form:name
    wb_token = State()


class Delete(StatesGroup):
    name = State()  # Will be represented in storage as 'Form:name


@router.message(CommandStart(), StateFilter(default_state))
async def process_start_command(message: Message):
    logging.info(f'New start {datetime.now()}')
    db = sq.connect('my_bd.sql')
    cur = db.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS profiles (user_id int, name TEXT, wb_token TEXT, dispatch TEXT)')
    db.commit()
    cur.close()
    db.close()

    await message.answer(text=f"Привет, <b>{message.from_user.full_name}</b>. Этот бот поможет сделить за продажами.",
                         reply_markup=kb_builder.as_markup(resize_keyboard=True)
                         )


@router.message(F.text == "Отмена")
async def cancel_states(message: Message, state: FSMContext):
    logging.info(f'Cancel action {datetime.now()}')
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
    global name, status
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
            await state.clear()
        else:
            await message.answer(text='Спасибо!\n\nА теперь введите API вашего магазина')
            # Устанавливаем состояние ожидания ввода API
            await state.set_state(Add.wb_token)
        cur.close()
        db.close()
        status = 1


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
        'INSERT INTO profiles VALUES (?, ?, ?, ?)', (message.from_user.id,
                                                     user_dict[message.from_user.id]['name'],
                                                     user_dict[message.from_user.id]['wb_token'],
                                                     0))
    db.commit()
    cur.close()
    db.close()

    # Завершаем машину состояний
    await state.clear()
    await message.answer(text='Магазин добавлен. Включите рассылку для нового магазина')
    logging.info(f'Shop added {datetime.now()}')



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
    global status
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
        status = 1
    logging.info(f'Shop deleted {datetime.now()}')


# список магазинов
@router.message(F.text == 'Список магазинов')
async def shop_list(message: Message, state: FSMContext):
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
    logging.info(f'Shop list {datetime.now()}')


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


@router.message(F.text == 'Отчет $')
async def subs_name_shop(message: Message):
    global user
    user = message.from_user.id
    await message.answer(
        text='Что необходимо сделать?',
        reply_markup=keyboard_inline_sub
    )

@router.callback_query(F.data == 'dispatch_on')
async def subs_on(callback: CallbackQuery):
    logging.info(f'Subscription started {datetime.now()}')
    await callback.message.answer(f'Вы подключили рассылку. Отчет будет приходить каждые 3 часа.')
    db = sq.connect('my_bd.sql')
    cur = db.cursor()
    cur.execute(f"UPDATE profiles SET dispatch = {'1'} WHERE user_id = {user};")
    db.commit()
    cur.close()
    db.close()


@router.callback_query(F.data == 'dispatch_off')
async def subs_off(callback: CallbackQuery):
    await callback.message.answer(f'Рассылка отключена')
    db = sq.connect('my_bd.sql')
    cur = db.cursor()
    cur.execute(f"UPDATE profiles SET dispatch = {'0'} WHERE user_id = {user};")
    db.commit()
    cur.close()
    db.close()
    logging.info(f'Subscription canceled {datetime.now()}')

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)


scheduler_thread = threading.Thread(target=run_scheduler)

schedule.every(5).minutes.do(dispatch_is_on, config.tg_bot.token)
schedule.every(4).minutes.do(not_change, config.tg_bot.token)


async def main():

    # Конфигурируем логирование
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(message)s')

    # Выводим в консоль информацию о начале запуска бота
    logger.info(f'Starting bot {datetime.now()}')

    dp = Dispatcher(storage=storage)

    dp.include_router(router)

    await dp.start_polling(bot, skip_updates=True)


if __name__ == '__main__':
    try:
        scheduler_thread.start()
        asyncio.run(main())
    except Exception as err:
        logging.error((traceback.format_exc()))
        logging.error(err)
