from aiogram import Router, F

from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from keyboards.all_keyboards import main_kb

from db_handler.db_class import Database
from db_handler.db_utils import DBUtils
from create_bot import bot

router = Router()

db = Database()
db_utils = DBUtils(db=db, bot=bot)


# Обработчик кнопки "Подписка"
async def handle_broadcast(message: Message):
    await db_utils.db.connect()
    user_id = message.from_user.id
    is_sub = await db_utils.is_subscribed_newsletter(user_id)

    # Создаем инлайн-клавиатуру
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="Отписаться" if is_sub else "Подписаться",
            callback_data="unsubscribe" if is_sub else "subscribe"
        )
    ], [
        InlineKeyboardButton(
            text="Отмена",
            callback_data="cancel_unsubscription" if is_sub else "cancel_subscription"
        )
    ]])

    await message.answer(
        text=f"Нажмите кнопку для "
             f"{'подписки на рассылку' if not is_sub else 'отписки от рассылки'}:",
        reply_markup=keyboard
    )
    await db_utils.db.close()


@router.callback_query(F.data.in_(["cancel_subscription", "cancel_unsubscription"]))
async def process_subscription_callback(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer(
        f"❌{'Подписка на рассылку' if callback.data == 'cancel_subscription' else 'Отписка от рассылки'} "
        f"бота отменена.",
        reply_markup=main_kb(callback.from_user.id)
    )
    await callback.answer()


# Обработчик инлайн-кнопок подписки/отписки
@router.callback_query(F.data.in_(["subscribe", "unsubscribe"]))
async def process_subscription_callback(callback: CallbackQuery):
    await db_utils.db.connect()
    user_id = callback.from_user.id
    action = callback.data

    # Определяем новое состояние подписки

    # Логируем активность
    activity_type = "subscribe" if action == "subscribe" else "unsubscribe"
    await db_utils.log_user_activity(
        user_id=user_id,
        activity_type=activity_type,
        theme_id=None
    )

    response_text = "✅Вы подписались на рассылку." if action == "subscribe" else "✅Вы отписались от рассылки."

    try:
        await callback.message.delete()
    except TelegramBadRequest as _:
        pass

    await callback.message.answer(response_text, reply_markup=main_kb(user_id))
    await callback.answer()
    await db_utils.db.close()
