import os
from aiogram import F, Router
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.chat_action import ChatActionSender
from create_bot import admins, bot
from keyboards.all_keyboards import admin_panel_kb
from db_handler.db_utils import DBUtils
from db_handler.db_class import Database

db = Database()
db_utils = DBUtils(db=db, bot=bot)

admin_router = Router()

DATA_DIR = "data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)


class AdminActions(StatesGroup):
    waiting_for_file = State()
    waiting_book_name = State()
    waiting_theme_data = State()
    waiting_expert_data = State()


@admin_router.message((F.text.endswith("Админ панель")) & (F.from_user.id.in_(admins)))
async def admin_panel(message: Message):
    await message.answer(
        "**Выберите действие в админ-панели**:",
        reply_markup=admin_panel_kb(),
        parse_mode="Markdown"
    )


@admin_router.callback_query(F.data.in_(
    ['admin_get_stats', 'admin_upload_data', 'admin_delete_book', 'admin_delete_selection', 'admin_delete_expert']))
async def process_admin_callback(callback: CallbackQuery, state: FSMContext):
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
        await state.set_state(AdminActions.waiting_for_file)
        await callback.message.answer(
            "📤 Пожалуйста, отправьте Excel-файл с данными.",
            parse_mode="Markdown"
        )

    elif action == "admin_delete_book":
        await state.set_state(AdminActions.waiting_book_name)
        await callback.message.answer("📝 Введите название книги для удаления:")

    elif action == "admin_delete_selection":
        await state.set_state(AdminActions.waiting_theme_data)
        await callback.message.answer("📝 Введите тему и подтему через '|' (пример: Физика|Квантовая механика):")

    elif action == "admin_delete_expert":
        await state.set_state(AdminActions.waiting_expert_data)
        await callback.message.answer("📝 Введите имя эксперта и должность через '|' (пример: Иван Иванов|Профессор):")

    await callback.answer()
    await db_utils.db.close()


@admin_router.message(AdminActions.waiting_for_file, F.document, F.from_user.id.in_(admins))
async def process_uploaded_file(message: Message, state: FSMContext):
    await db_utils.db.connect()
    document = message.document
    if not document.file_name.endswith(('.xlsx', '.xls')):
        await message.answer("❌ Пожалуйста, отправьте файл в формате Excel (.xlsx или .xls).")
        await state.clear()
        return

    try:
        async with ChatActionSender.upload_document(bot=bot, chat_id=message.chat.id):
            file_path = os.path.join(DATA_DIR, document.file_name)
            file = await bot.get_file(document.file_id)
            await bot.download_file(file.file_path, file_path)

            success = await db_utils.upload_data(file_path)

            if success:
                await message.answer(f"✅ Данные из файла {document.file_name} успешно загружены!")
                os.remove(file_path)
            else:
                await message.answer(f"❌ Ошибка при загрузке данных из файла {document.file_name}")

            await state.clear()

    except Exception as exc:
        await message.answer(f"❌ Ошибка при обработке файла: {str(exc)}")
        await state.clear()
    await db_utils.db.close()


@admin_router.message(AdminActions.waiting_book_name, F.from_user.id.in_(admins))
async def process_book_name(message: Message, state: FSMContext):
    await db_utils.db.connect()
    book_name = message.text.strip()
    success = await db_utils.delete_book(book_name)
    if success:
        await message.answer(f"✅ Книга '{book_name}' успешно удалена!")
    else:
        await message.answer(f"❌ Не удалось удалить книгу '{book_name}'")
    await state.clear()
    await db_utils.close()


@admin_router.message(AdminActions.waiting_theme_data, F.from_user.id.in_(admins))
async def process_theme_data(message: Message, state: FSMContext):
    await db_utils.db.connect()
    try:
        theme_name, subtheme_name = message.text.split('|', 1)
        success = await db_utils.delete_selection(
            theme_name.strip(),
            subtheme_name.strip()
        )
        if success:
            await message.answer(f"✅ Подборка '{theme_name.strip()}/{subtheme_name.strip()}' удалена!")
        else:
            await message.answer("❌ Подборка не найдена или произошла ошибка")
    except ValueError:
        await message.answer("❌ Неверный формат. Пример: Физика|Квантовая механика")
    await state.clear()
    await db_utils.db.close()



@admin_router.message(AdminActions.waiting_expert_data, F.from_user.id.in_(admins))
async def process_expert_data(message: Message, state: FSMContext):
    await db_utils.db.connect()
    try:
        expert_name, expert_position = message.text.split('|', 1)
        success = await db_utils.delete_expert(
            expert_name.strip(),
            expert_position.strip()
        )
        if success:
            await message.answer(f"✅ Эксперт '{expert_name.strip}' удален!")
        else:
            await message.answer("❌ Эксперт не найден или произошла ошибка")
    except ValueError:
        await message.answer("❌ Неверный формат. Пример: Иван Иванов|Профессор")
    await state.clear()
    await db_utils.db.close()

@admin_router.message(AdminActions.waiting_for_file)
async def invalid_file_type(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Пожалуйста, отправьте файл в формате Excel (.xlsx или .xls).")