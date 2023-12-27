from typing import Dict, Any, Callable, Awaitable
from aiogram import BaseMiddleware
from aiogram.types.base import TelegramObject
from apscheduler.schedulers.background import BackgroundScheduler


class SchedulerMiddleware(BaseMiddleware):
    def __init__(self, scheduler: BackgroundScheduler):
        self.scheduler = scheduler

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        data['apscheduler'] = self.scheduler
        return await handler(event, data)