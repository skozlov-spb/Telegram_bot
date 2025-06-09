from aiogram import F, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from keyboards.all_keyboards import main_kb
from db_handler.db_utils import DBUtils
from db_handler.db_class import Database
import create_bot
from create_bot import bot
from handlers.admin_panel.states import AdminActions

admin_router = Router()
db_utils = DBUtils(db=Database(), bot=bot)


@admin_router.callback_query(F.data == "admin_add_admin")
async def add_admin_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminActions.waiting_new_admin_id)
    await callback.message.delete()
    sent = await callback.message.answer(
        "Введите ID пользователя, которого хотите сделать администратором(узнать его можно тут: @getmyid_bot):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Отмена", callback_data="admin_cancel_add")]
        ])
    )
    await state.update_data(prompt_chat_id=sent.chat.id, prompt_msg_id=sent.message_id, user_id=callback.from_user.id)
    await callback.answer()


@admin_router.callback_query(F.data == "admin_cancel_add")
async def cancel_add_admin(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.message.answer(
        "❌Добавление администратора отменено",
        reply_markup=main_kb(callback.from_user.id)
    )
    await callback.answer()


@admin_router.message(AdminActions.waiting_new_admin_id, F.text)
async def process_admin_id(message: Message, state: FSMContext):
    data = await state.get_data()
    chat_id = data.get("prompt_chat_id")
    msg_id = data.get("prompt_msg_id")
    user_id = data.get("user_id")

    if chat_id and msg_id:
        try:
            await bot.edit_message_reply_markup(chat_id=chat_id, message_id=msg_id, reply_markup=None)
        except Exception:
            pass

    try:
        new_admin_id = int(message.text)

        try:
            user = await bot.get_chat(new_admin_id)
        except Exception:
            await message.answer("❌Пользователь с таким ID не найден",
                                 reply_markup=main_kb(user_id))
            await state.clear()
            return

        if new_admin_id not in create_bot.admins:
            await db_utils.db.connect()
            await db_utils.assign_admin_role(new_admin_id)
            await db_utils.db.close()
            create_bot.admins.append(new_admin_id)
            await message.answer(f"✅Пользователь {user.full_name} (@{user.username}) добавлен в администраторы",
                                 reply_markup=main_kb(user_id))
        else:
            await message.answer("⚠️Этот пользователь уже является администратором",
                                 reply_markup=main_kb(user_id))

        await state.clear()

    except ValueError:
        await message.answer("❌Неверный формат ID. Введите числовой идентификатор",
                             reply_markup=main_kb(user_id))

    finally:
        await db_utils.db.close()
