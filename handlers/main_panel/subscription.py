from aiogram import Router, F
from aiogram.types import CallbackQuery

from keyboards.all_keyboards import main_kb
from db_handler.db_class import Database
from db_handler.db_utils import DBUtils
from create_bot import bot

router = Router()

db = Database()
db_utils = DBUtils(db=db, bot=bot)


@router.callback_query(F.data == "check_subscription")
async def check_subscription_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    await db_utils.db.connect()

    is_spbu_member = await db_utils.is_user_channel_member(user_id)

    if is_spbu_member:
        await callback.message.delete()  # Удаляем предыдущее сообщение с кнопкой
        await callback.message.answer(
            "🎉Спасибо за подписку! Теперь вы можете пользоваться ботом.",
            reply_markup=main_kb(user_id),
            parse_mode="Markdown"
        )
        await db_utils.log_user_activity(user_id, activity_type='subscribed_channels', theme_id=None)  # Логируем
    else:
        await callback.answer("Вы еще не подписались на канал.", show_alert=True)  # Покажем всплывающее уведомление

    await db_utils.db.close()
