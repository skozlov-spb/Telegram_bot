import asyncio
import threading

from server import run_flask
from create_bot import (bot, dp, scheduler, create_backup, remove_menu,
                        update_admins, check_users_status_task, save_stats)

from handlers.main_panel import main_panel_router
from handlers.admin_panel import admin_panel_router

from db_handler.db_setup import init_db
from db_handler.db_utils import DBUtils
from db_handler.db_utils import Database


async def start_bot():
    if not scheduler.running:
        scheduler.start()


async def main():
    await init_db()  # Инициализируем БД
    db = Database()
    db_utils = DBUtils(db=db, bot=bot)
    await update_admins(db_utils)
    await remove_menu(bot)
    
    # Регистрация роутеров
    dp.include_router(main_panel_router)
    dp.include_router(admin_panel_router)
    dp.startup.register(start_bot)
    
    scheduler.add_job(
        save_stats,
        'cron',
        hour=4,
        minute=0,
        misfire_grace_time=60,
        args=[db_utils]
    )

    scheduler.add_job(
        check_users_status_task,
        'cron',
        hour=4,
        minute=1,
        misfire_grace_time=60,
        args=[db_utils]
    )
        
    scheduler.add_job(
        create_backup,  
        'cron',
        hour=4,
        minute=2,
        misfire_grace_time=60
    )
    
    # Запуск бота в режиме long polling при запуске бот очищает все обновления, которые были за его моменты бездействия
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        

if __name__ == "__main__":
    # Запускаем Flask-сервер
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Запускаем бота
    asyncio.run(main())
