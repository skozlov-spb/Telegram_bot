import os
from aiogram import F, Router
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.chat_action import ChatActionSender
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
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


@admin_router.message((F.text.endswith("Админ панель")) & (F.from_user.id.in_(admins)))
async def admin_panel(message: Message):
    await message.answer(
        "**Выберите действие в админ-панели**:",
        reply_markup=admin_panel_kb(),
        parse_mode="Markdown"
    )


@admin_router.callback_query(F.data.in_(
    ['admin_get_stats', 'admin_upload_data', 'admin_delete_book']))
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

    await callback.answer()
    await db_utils.db.close()


@admin_router.callback_query(F.data.in_(['admin_select_theme']) |
                            F.data.regexp(r'^(admin_themes_page|admin_theme|admin_subthemes|admin_delete_subtheme)_'))
async def process_theme_selection(callback: CallbackQuery):
    await db_utils.db.connect()
    user_id = callback.from_user.id

    if user_id not in admins:
        await callback.message.answer("У вас нет доступа к админ-панели.")
        await callback.answer()
        await db_utils.db.close()
        return

    action = callback.data

    if action == "admin_select_theme" or action.startswith("admin_themes_page_"):
        # Пагинация тем
        if action == "admin_select_theme":
            page = 0
        else:
            page = int(action.split("_")[-1])
        items_per_page = 5

        themes = await db_utils.get_available_themes()
        if not themes:
            await callback.message.answer("⚠️ *Темы отсутствуют.*", parse_mode="Markdown")
            await callback.answer()
            await db_utils.db.close()
            return

        total_pages = (len(themes) + items_per_page - 1) // items_per_page
        start_idx = page * items_per_page
        end_idx = min(start_idx + items_per_page, len(themes))
        current_themes = themes[start_idx:end_idx]

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"📖 {theme}", callback_data=f"admin_theme_{current_themes.index(theme) + start_idx}")]
            for theme in current_themes
        ])

        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(text="◄ Назад", callback_data=f"admin_themes_page_{page - 1}"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton(text="Вперёд ►", callback_data=f"admin_themes_page_{page + 1}"))
        if nav_buttons:
            keyboard.inline_keyboard.append(nav_buttons)
        keyboard.inline_keyboard.append(
            [InlineKeyboardButton(text=f"📄 Страница {page + 1} из {total_pages}", callback_data=f"admin_page_{page}")])

        await callback.message.edit_text("**Выберите тему для удаления** 📚\n*Доступные категории:*",
                                        reply_markup=keyboard, parse_mode="Markdown")

    elif action.startswith("admin_theme_") or action.startswith("admin_subthemes_"):
        # Пагинация подтем
        if action.startswith("admin_theme_"):
            theme_id = action[len("admin_theme_"):]
            page = 0
        else:
            theme_id, page = action[len("admin_subthemes_"):].split("_")
            page = int(page)

        theme_id = int(theme_id)
        items_per_page = 5

        themes = await db_utils.get_available_themes()
        theme_name = themes[theme_id]
        subthemes = await db_utils.get_subthemes(theme_name)
        if not subthemes:
            await callback.message.answer(f"⚠️ *Подтемы для __{theme_name}__ не найдены.*", parse_mode="Markdown")
            await callback.answer()
            await db_utils.db.close()
            return

        total_pages = (len(subthemes) + items_per_page - 1) // items_per_page
        start_idx = page * items_per_page
        end_idx = min(start_idx + items_per_page, len(subthemes))
        current_subthemes = subthemes[start_idx:end_idx]

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"📋 {subtheme}",
                                 callback_data=f"admin_delete_subtheme_{current_subthemes.index(subtheme) + start_idx}_{theme_id}")]
            for subtheme in current_subthemes
        ])

        nav_buttons = []
        if page > 0:
            nav_buttons.append(
                InlineKeyboardButton(text="◄ Назад", callback_data=f"admin_subthemes_{theme_id}_{page - 1}"))
        if page < total_pages - 1:
            nav_buttons.append(
                InlineKeyboardButton(text="Вперёд ►", callback_data=f"admin_subthemes_{theme_id}_{page + 1}"))
        if nav_buttons:
            keyboard.inline_keyboard.append(nav_buttons)
        keyboard.inline_keyboard.append(
            [InlineKeyboardButton(text=f"📄 Страница {page + 1} из {total_pages}", callback_data=f"admin_page_{page}")])

        await callback.message.edit_text(f"**Подтемы для __{theme_name}__** 📋\n*Выберите подтему для удаления:*",
                                        reply_markup=keyboard, parse_mode="Markdown")

    elif action.startswith("admin_delete_subtheme_"):
        subtheme_id, theme_id = action[len("admin_delete_subtheme_"):].split("_")
        subtheme_id = int(subtheme_id)
        theme_id = int(theme_id)

        themes = await db_utils.get_available_themes()
        theme_name = themes[theme_id]
        subthemes = await db_utils.get_subthemes(theme_name)
        subtheme_name = subthemes[subtheme_id]

        success = await db_utils.delete_selection(theme_name, subtheme_name)
        if success:
            await callback.message.edit_text(f"✅ Подборка '{theme_name}/{subtheme_name}' успешно удалена!",
                                            parse_mode="Markdown")
        else:
            await callback.message.edit_text(f"❌ Не удалось удалить подборку '{theme_name}/{subtheme_name}'",
                                            parse_mode="Markdown")

    await callback.answer()
    await db_utils.db.close()


@admin_router.callback_query(F.data.in_(['admin_select_expert']) |
                            F.data.regexp(r'^(admin_experts_page|admin_delete_expert)_'))
async def process_expert_selection(callback: CallbackQuery):
    await db_utils.db.connect()
    user_id = callback.from_user.id

    if user_id not in admins:
        await callback.message.answer("У вас нет доступа к админ-панели.")
        await callback.answer()
        await db_utils.db.close()
        return

    action = callback.data

    if action == "admin_select_expert" or action.startswith("admin_experts_page_"):
        # Пагинация экспертов
        if action == "admin_select_expert":
            page = 0
        else:
            page = int(action.split("_")[-1])
        items_per_page = 5

        experts = await db_utils.get_available_experts()
        if not experts:
            await callback.message.answer("⚠️ *Эксперты отсутствуют.*", parse_mode="Markdown")
            await callback.answer()
            await db_utils.db.close()
            return

        total_pages = (len(experts) + items_per_page - 1) // items_per_page
        start_idx = page * items_per_page
        end_idx = min(start_idx + items_per_page, len(experts))
        current_experts = experts[start_idx:end_idx]

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"👤 {expert[0]} ({expert[1]})",
                                 callback_data=f"admin_delete_expert_{current_experts.index(expert) + start_idx}")]
            for expert in current_experts
        ])

        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(text="◄ Назад", callback_data=f"admin_experts_page_{page - 1}"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton(text="Вперёд ►", callback_data=f"admin_experts_page_{page + 1}"))
        if nav_buttons:
            keyboard.inline_keyboard.append(nav_buttons)
        keyboard.inline_keyboard.append(
            [InlineKeyboardButton(text=f"📄 Страница {page + 1} из {total_pages}", callback_data=f"admin_page_{page}")])

        await callback.message.edit_text("**Выберите эксперта для удаления** 👤\n*Доступные эксперты:*",
                                        reply_markup=keyboard, parse_mode="Markdown")

    elif action.startswith("admin_delete_expert_"):
        expert_id = int(action[len("admin_delete_expert_"):])
        experts = await db_utils.get_available_experts()
        expert_name, expert_position = experts[expert_id]

        success = await db_utils.delete_expert(expert_name, expert_position)
        if success:
            await callback.message.edit_text(f"✅ Эксперт '{expert_name} ({expert_position})' успешно удален!",
                                            parse_mode="Markdown")
        else:
            await callback.message.edit_text(f"❌ Не удалось удалить эксперта '{expert_name} ({expert_position})'",
                                            parse_mode="Markdown")

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
    await db_utils.db.close()


@admin_router.message(AdminActions.waiting_for_file)
async def invalid_file_type(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Пожалуйста, отправьте файл в формате Excel (.xlsx или .xls).")