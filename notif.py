from __future__ import annotations

from aiogram.enums import ParseMode
from aiogram import F, types, Router
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state, State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message, PhotoSize)
import requests
from requests.structures import CaseInsensitiveDict
import datetime
import asyncio
import aioschedule
import pandas as pd
from notifiers import get_notifier
import time
import schedule
import sqlite3 as sq

headers = CaseInsensitiveDict()
