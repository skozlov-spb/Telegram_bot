import sys
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from decouple import config
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
import asyncio
import os
import csv
from aiogram.types import MenuButtonDefault

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



async def check_users_status_task(db_utils):
    """Проверяет статус всех пользователей."""
    logger.info("Запуск ежедневной проверки статуса пользователей")
    try:
        await db_utils.check_users_status()
        logger.info("Проверка статуса пользователей завершена")
    except Exception as e:
        logger.error(f"Ошибка при проверке статуса пользователей: {e}")


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

bot = Bot(token="7543327903:AAGhzCID6Q9cjsRS87Yb504pkEqMESIk-HY", default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

try:
    admins = [int(admin_id) for admin_id in config('ADMINS').split(',')]
except (ValueError, KeyError) as e:
    logger.error(f"Ошибка при загрузке ADMINS из .env: {e}")
    admins = []

async def remove_menu(bot):
    await bot.delete_my_commands()
    await bot.set_chat_menu_button(menu_button=MenuButtonDefault())

async def update_admins(db_utils):
    """Обновляет список администраторов из базы данных."""
    global admins
    try:
        await db_utils.db.connect()
        admins = await db_utils.get_admin_ids()
        await db_utils.db.close()
        logger.info(f"Список администраторов обновлён: {admins}")
    except Exception as e:
        logger.error(f"Ошибка при обновлении списка администраторов: {e}")


async def save_stats(db_utils):
    """Получает статистику и записывает в stats.csv"""
    logger.info("Запуск задачи по расписанию: сохранение статистики")

    try:
        await db_utils.db.connect()
        stats = await db_utils.get_statistic()
        await db_utils.db.close()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        stats_row = {
            "timestamp": timestamp,
            "total_users": stats["total_users"],
            "inactive_percent": stats["inactive_percent"],
            "subscribed_users": stats["subscribed_users"],
            "blocked_users": stats["blocked_users"],
            "wau": stats["wau"],
            "repeat_usage_percent": stats["repeat_usage_percent"]
        }

        try:
            with open("db_handler/data/stats.csv", mode="a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "timestamp",
                        "total_users",
                        "inactive_percent",
                        "subscribed_users",
                        "blocked_users",
                        "wau",
                        "repeat_usage_percent"
                    ]
                )
                if f.tell() == 0:
                    writer.writeheader()
                writer.writerow(stats_row)
            logger.info(f"Статистика записана в stats.csv: {stats_row}")
        except Exception as exc:
            logger.error(f"Ошибка записи в stats.csv: {exc}")

    except Exception as exc:
        logger.error(f"Ошибка получения статистики: {exc}")
