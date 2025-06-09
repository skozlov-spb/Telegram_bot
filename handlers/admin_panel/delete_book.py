from aiogram import F, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from keyboards.all_keyboards import main_kb, admin_panel_kb
from db_handler.db_utils import DBUtils
from db_handler.db_class import Database
import create_bot
from create_bot import bot
from handlers.admin_panel.states import AdminActions

admin_router = Router()
db_utils = DBUtils(db=Database(), bot=bot)


@admin_router.callback_query(F.data == "admin_delete_book")
async def start_delete_book(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if user_id not in create_bot.admins:
        await callback.message.answer("У вас нет доступа к админ-панели.")
        await callback.answer()
        return

    await state.set_state(AdminActions.waiting_book_name)
    await callback.message.delete()
    await callback.message.answer("📝Введите название книги для удаления:")
    await callback.answer()


@admin_router.message(AdminActions.waiting_book_name, F.from_user.id.in_(create_bot.admins))
async def process_book_name(message: Message, state: FSMContext):
    await state.update_data(book_name=message.text)

    confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Да", callback_data="confirm_delete"),
            InlineKeyboardButton(text="Нет", callback_data="cancel_delete")
        ]
    ])

    await message.answer(
        f"⚠️Вы уверены, что хотите удалить книгу?\nНазвание: {message.text}",
        reply_markup=confirm_keyboard
    )
    await state.set_state(AdminActions.waiting_book_delete_confirmation)


@admin_router.callback_query(
    AdminActions.waiting_book_delete_confirmation,
    F.data.in_(["confirm_delete", "cancel_delete"])
)
async def handle_delete_confirmation(callback: CallbackQuery, state: FSMContext):
    await db_utils.db.connect()
    try:
        data = await state.get_data()

        if callback.data == "confirm_delete":
            book_name = data['book_name']
            success = await db_utils.delete_book(book_name)

            if success:
                await callback.message.delete()
                await callback.message.answer(
                    f"✅Книга {book_name} успешно удалена!",
                    reply_markup=main_kb(callback.from_user.id)
                )
            else:
                await callback.message.delete()
                await callback.message.answer(
                    f"❌Не удалось удалить книгу {book_name}",
                    reply_markup=main_kb(callback.from_user.id)
                )
        else:
            await callback.message.delete()
            await callback.message.answer(
                "❌Удаление отменено",
                reply_markup=main_kb(callback.from_user.id)
            )

    except Exception as e:
        await callback.message.answer("⚠️Произошла ошибка при удалении", reply_markup=admin_panel_kb())

    finally:
        await state.clear()
        await callback.answer()
        await db_utils.db.close()
