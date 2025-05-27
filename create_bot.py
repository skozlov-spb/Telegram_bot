import sys
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from decouple import config
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from db_handler.db_utils import get_admin_ids
from db_handler.db_class import Database
from datetime import datetime
import asyncio
import os


scheduler = AsyncIOScheduler(timezone='Europe/Moscow')



DB_CONFIG = {
    'user': config('PG_USER'),
    'password': config('PG_PASSWORD'),
    'database': config('PG_DB'),
    'host': config('PG_HOST')
}

async def create_backup():
    """Создание бэкапа базы данных"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"db_handler/data/backup_{timestamp}.sql"
    
    process = await asyncio.create_subprocess_exec(
        'pg_dump',
        '-h', DB_CONFIG['host'],
        '-U', DB_CONFIG['user'],
        '-d', DB_CONFIG['database'],
        '-f', backup_file,
        env={**os.environ, 'PGPASSWORD': DB_CONFIG['password']}
    )

    await process.wait()
    return backup_file


def schedule_jobs():
    """Функция для добавления заданий (может быть пустой)"""
    pass


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

bot = Bot(token=config('TOKEN'), default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

admins = get_admin_ids()
