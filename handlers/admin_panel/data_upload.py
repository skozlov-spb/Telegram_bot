import os
from aiogram import F, Router
import shutil
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.utils.chat_action import ChatActionSender
from keyboards.all_keyboards import main_kb
from db_handler.db_utils import DBUtils
from db_handler.db_class import Database
import create_bot
from create_bot import bot
from handlers.admin_panel.states import AdminActions

admin_router = Router()
db_utils = DBUtils(db=Database(), bot=bot)

DATA_DIR = "db_handler/input_data"


@admin_router.callback_query(F.data == "admin_upload_data")
async def start_upload_data(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if user_id not in create_bot.admins:
        await callback.message.answer("У вас нет доступа к админ-панели.")
        await callback.answer()
        return

    await state.set_state(AdminActions.waiting_for_file)
    await callback.message.delete()
    await callback.message.answer(
        "📤Пожалуйста, отправьте Excel-файл с данными.",
        parse_mode="Markdown"
    )
    await callback.answer()


@admin_router.message(AdminActions.waiting_for_file, F.document, F.from_user.id.in_(create_bot.admins))
async def process_uploaded_file(message: Message, state: FSMContext):
    await db_utils.db.connect()
    document = message.document
    if not document.file_name.endswith(('.xlsx', '.xls')):
        await message.answer("❌Пожалуйста, отправьте файл в формате Excel (.xlsx или .xls).",
                             reply_markup=main_kb(message.from_user.id))
        await state.clear()
        await db_utils.db.close()
        return

    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    try:
        async with ChatActionSender.upload_document(bot=bot, chat_id=message.chat.id):
            file_path = os.path.join(DATA_DIR, document.file_name)
            file = await bot.get_file(document.file_id)
            await bot.download_file(file.file_path, file_path)

            success = await db_utils.upload_data(file_path)

            if success:
                await message.answer(f"✅Данные из файла «{document.file_name}» успешно загружены!",
                                     reply_markup=main_kb(message.from_user.id))
                os.remove(file_path)
            else:
                await message.answer(f"❌Ошибка при загрузке данных из файла «{document.file_name}»",
                                     reply_markup=main_kb(message.from_user.id))

            await state.clear()

    except Exception as exc:
        await message.answer(f"❌Ошибка при обработке файла: {str(exc)}", reply_markup=main_kb(message.from_user.id))
        await state.clear()
    finally:
        if os.path.exists(DATA_DIR):
            shutil.rmtree(DATA_DIR)
        await db_utils.db.close()


@admin_router.message(AdminActions.waiting_for_file)
async def invalid_file_type(message: Message, state: FSMContext):
    await state.clear()
    await message.delete()
    await message.answer("❌Пожалуйста, отправьте файл в формате Excel (.xlsx или .xls).",
                         reply_markup=main_kb(message.from_user.id))
