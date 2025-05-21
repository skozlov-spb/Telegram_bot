import os
from aiogram import F, Router
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.chat_action import ChatActionSender
from create_bot import admins, bot
from keyboards.all_keyboards import admin_panel_kb
from db_handler.db_utils import DBUtils  # Импортируем DBUtils для вызова upload_data
from db_handler.db_class import Database

db = Database()
db_utils = DBUtils(db=db, bot=bot)

admin_router = Router()

# Создаем папку data, если она не существует
DATA_DIR = "data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)


# Определяем состояния для загрузки файла
class UploadData(StatesGroup):
    waiting_for_file = State()


@admin_router.message((F.text.endswith("Админ панель")) & (F.from_user.id.in_(admins)))
async def admin_panel(message: Message):
    await message.answer(
        "**Выберите действие в админ-панели**:",
        reply_markup=admin_panel_kb(), parse_mode="Markdown"
    )


@admin_router.callback_query(F.data.in_(['admin_get_stats', 'admin_upload_data']))
async def process_admin_callback(callback: CallbackQuery, state: FSMContext):
    """
    Обработка callback-запросов админ-панели
    """
    await db_utils.db.connect()
    action = callback.data
    user_id = callback.from_user.id

    if user_id not in admins:
        await callback.message.answer("У вас нет доступа к админ-панели.")
        await callback.answer()
        return

    if action == "admin_get_stats":
        stats = await db_utils.get_statistic()
        response = (
            f"📊 **Статистика**:\n"
            f"Всего пользователей: {stats['total_users']}\n"
            f"Неактивные пользователи: {stats['inactive_percent']}%\n"
            f"Подписанные на рассылку: {stats['subscribed_users']}"
        )
        await callback.message.answer(response, parse_mode="Markdown")

    elif action == "admin_upload_data":
        # Переход в состояние ожидания файла
        print('upldt')
        await state.set_state(UploadData.waiting_for_file)
        await callback.message.answer(
            "📤 Пожалуйста, отправьте Excel-файл с данными.",
            parse_mode="Markdown"
        )

    await callback.answer()
    await db_utils.db.close()


@admin_router.message(UploadData.waiting_for_file, F.document, F.from_user.id.in_(admins))
async def process_uploaded_file(message: Message, state: FSMContext):
    """
    Обработка загруженного Excel-файла
    """
    await db_utils.db.connect()
    document = message.document
    if not document.file_name.endswith(('.xlsx', '.xls')):
        await message.answer("❌ Пожалуйста, отправьте файл в формате Excel (.xlsx или .xls).")
        await state.clear()
        return

    try:
        # Указываем, что бот загружает файл
        async with ChatActionSender.upload_document(bot=bot, chat_id=message.chat.id):
            # Формируем путь для сохранения файла
            file_path = os.path.join(DATA_DIR, document.file_name)

            # Скачиваем файл
            file = await bot.get_file(document.file_id)
            await bot.download_file(file.file_path, file_path)

            # Вызываем метод upload_data для обработки файла
            success = await db_utils.upload_data(file_path)

            if success:
                await message.answer(f"✅ Данные из файла {document.file_name} успешно загружены в базу данных!")
                # Удаляем файл после успешной загрузки
                os.remove(file_path)
            else:
                await message.answer(f"❌ Ошибка при загрузке данных из файла {document.file_name}")

            # Сбрасываем состояние
            await state.clear()

    except Exception as exc:
        await message.answer(f"❌ Произошла ошибка при обработке файла: {str(exc)}")
        await state.clear()
    await db_utils.db.close()


@admin_router.message(UploadData.waiting_for_file)
async def invalid_file_type(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Пожалуйста, отправьте файл в формате Excel (.xlsx или .xls).")
