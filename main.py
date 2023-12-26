import logging
from aiogram import Bot, Dispatcher
import db, notif
import asyncio
import schedule
import aioschedule
import time
from threading import Thread
from datetime import datetime
from middleware import SchedulerMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
# Инициализируем логгер
logger = logging.getLogger(__name__)
from config import Config, load_config

config: Config = load_config()
BOT_TOKEN: str = config.tg_bot.token

async def start():
    # Конфигурируем логирование
    logging.basicConfig(
        level=logging.INFO,
        format='%(filename)s:%(lineno)d #%(levelname)-8s '
               '[%(asctime)s] - %(name)s - %(message)s')

    # Выводим в консоль информацию о начале запуска бота
    logger.info('Starting bot')

    # Объект бота
    bot = Bot(token=BOT_TOKEN, parse_mode='HTML')
    #pool_connect = create_pool()
    # Диспетчер
    dp = Dispatcher()
    scheduler = AsyncIOScheduler(timezone='Europe/Moscow')

    scheduler.start()

    dp.update.middleware.register(SchedulerMiddleware(scheduler))
    # Регистриуем роутеры в диспетчере
    dp.include_router(db.router)
    #notif.include_router(db.router)



    # Пропускаем накопившиеся апдейты и запускаем polling
    await bot.delete_webhook(drop_pending_updates=True)
    try:
        await dp.start_polling(bot)
    finally:
        bot.session.close()


def schedule_checker():
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == '__main__':
    # schedule.every(5).minutes.do(notif.report_notif)
    # Thread(target=schedule_checker).start()
    asyncio.run(start())