from aiogram import F, Router
from aiogram.types import CallbackQuery
from db_handler.db_utils import DBUtils
from db_handler.db_class import Database
from keyboards.all_keyboards import main_kb
import create_bot
from create_bot import bot

admin_router = Router()
db_utils = DBUtils(db=Database(), bot=bot)


@admin_router.callback_query(F.data == "admin_get_stats")
async def get_stats(callback: CallbackQuery):
    await db_utils.db.connect()
    user_id = callback.from_user.id

    if user_id not in create_bot.admins:
        await callback.message.answer("У вас нет доступа к админ-панели.")
        await callback.answer()
        await db_utils.db.close()
        return

    stats = await db_utils.get_statistic()
    response = (
        f"📊**Статистика**:\n"
        f"Всего пользователей: {stats['total_users']}\n"
        f"Неактивные пользователи: {stats['inactive_percent']}%\n"
        f"Пользователей удаливших бот: {stats['blocked_users']}\n"
        f"Процент повторных обращений (сессий): {stats['repeat_usage_percent']}%\n"
        f"Еженедельно активные пользователи (WAU): {stats['wau']}\n"
    )
    await callback.message.delete()
    await callback.message.answer(response, parse_mode="Markdown",
                                  reply_markup=main_kb(callback.from_user.id))
    await callback.answer()
    await db_utils.db.close()
