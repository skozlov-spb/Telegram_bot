import asyncio
import threading

from aiogram.types import BotCommand, BotCommandScopeDefault

from server import run_flask
from create_bot import bot, dp, scheduler
from handlers.start import start_router
from db_handler.db_setup import init_db
from keyboards.all_keyboards import set_commands


async def start_bot():
    await set_commands()


async def main():

    await init_db()  # Инициализируем БД

    # Регистрация роутеров
    dp.include_router(start_router)
    dp.startup.register(start_bot)

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
