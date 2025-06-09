from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from keyboards.all_keyboards import admin_panel_kb, main_kb
import create_bot
from aiogram.exceptions import TelegramBadRequest

admin_router = Router()


@admin_router.message((F.text.endswith("Админ панель")) & (F.from_user.id.in_(create_bot.admins)))
async def admin_panel(message: Message):
    await message.answer(
        "**Выберите действие в админ-панели**:",
        reply_markup=admin_panel_kb(),
        parse_mode="Markdown"
    )


@admin_router.callback_query(F.data == "admin_back_to_panel")
async def back_to_admin_panel(callback: CallbackQuery):
    await callback.message.edit_text(
        "**Выберите действие в админ-панели**:",
        reply_markup=admin_panel_kb(),
        parse_mode="Markdown"
    )
    await callback.answer()


@admin_router.callback_query(F.data == "admin_back_to_menu")
async def back_to_main_menu(callback: CallbackQuery):
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
    await callback.message.answer(
        "Главное меню:",
        reply_markup=main_kb(callback.from_user.id)
    )
    await callback.answer()
