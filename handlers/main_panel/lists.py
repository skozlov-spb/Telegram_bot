from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from keyboards.all_keyboards import main_kb
from db_handler.db_class import Database
from db_handler.db_utils import DBUtils
from create_bot import bot

db = Database()
db_utils = DBUtils(db=db, bot=bot)


# Функция для отображения списка тем с пагинацией
async def display_themes(page: int, callback: CallbackQuery):
    await db_utils.db.connect()
    try:
        items_per_page = 5
        themes = await db_utils.get_available_themes()
        if not themes:
            await callback.message.answer("⚠️*Темы отсутствуют.*",
                                          reply_markup=main_kb(callback.from_user.id),
                                          parse_mode="Markdown")
            await callback.answer()
            return

        total_pages = (len(themes) + items_per_page - 1) // items_per_page
        if page < 0 or page >= total_pages:
            await callback.answer("⚠️Страница не существует.")
            return

        start_idx = page * items_per_page
        end_idx = min(start_idx + items_per_page, len(themes))
        current_themes = themes[start_idx:end_idx]

        # Создаем клавиатуру с кнопками тем
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"📖{theme}", callback_data=f"theme_{themes.index(theme)}")]
            for theme in current_themes
        ])

        # Добавляем кнопки навигации по страницам
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(text="◄ Назад", callback_data=f"themes_page_{page - 1}"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton(text="Вперёд ►", callback_data=f"themes_page_{page + 1}"))
        if nav_buttons:
            keyboard.inline_keyboard.append(nav_buttons)

        # Добавляем информацию о странице и кнопку возврата
        keyboard.inline_keyboard.append(
            [InlineKeyboardButton(text=f"📄Страница {page + 1} из {total_pages}", callback_data=f"page_{page}")]
        )
        keyboard.inline_keyboard.append(
            [InlineKeyboardButton(text="◄ Вернуться в главное меню", callback_data="back_to_main")]
        )

        await callback.message.edit_text(
            "**Выберите тему**📚\n*Доступные категории:*",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    finally:
        await db_utils.db.close()


# Функция для отображения списка подтем с пагинацией
async def display_subthemes(theme_id: int, page: int, callback: CallbackQuery):
    await db_utils.db.connect()
    try:
        themes = await db_utils.get_available_themes()
        if not themes or theme_id < 0 or theme_id >= len(themes):
            await callback.message.delete()
            await callback.message.answer("⚠️*Тема не найдена.*",
                                          reply_markup=main_kb(callback.from_user.id),
                                          parse_mode="Markdown")
            await callback.answer()
            return

        theme_name = themes[theme_id]
        subthemes = await db_utils.get_subthemes(theme_name)
        if not subthemes:
            await callback.message.delete()
            await callback.message.answer(f"⚠️*Подтемы для __{theme_name}__ не найдены.*",
                                          reply_markup=main_kb(callback.from_user.id),
                                          parse_mode="Markdown")
            await callback.answer()
            return

        items_per_page = 5
        total_pages = (len(subthemes) + items_per_page - 1) // items_per_page
        if page < 0 or page >= total_pages:
            await callback.message.delete()
            await callback.answer("⚠️Страница не существует.")
            return

        start_idx = page * items_per_page
        end_idx = min(start_idx + items_per_page, len(subthemes))
        current_subthemes = subthemes[start_idx:end_idx]

        # Создаем клавиатуру с кнопками подтем
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"📋{subtheme}",
                                  callback_data=f"subtheme_{subthemes.index(subtheme)}_{theme_id}")]
            for subtheme in current_subthemes
        ])

        # Добавляем кнопки навигации по страницам
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(text="◄ Назад", callback_data=f"subthemes_{theme_id}_{page - 1}"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton(text="Вперёд ►", callback_data=f"subthemes_{theme_id}_{page + 1}"))
        if nav_buttons:
            keyboard.inline_keyboard.append(nav_buttons)

        # Добавляем информацию о странице и кнопку возврата
        keyboard.inline_keyboard.append(
            [InlineKeyboardButton(text=f"📄Страница {page + 1} из {total_pages}", callback_data=f"page_{page}")]
        )
        keyboard.inline_keyboard.append(
            [InlineKeyboardButton(text="◄ Вернуться к темам", callback_data="get_themes")]
        )

        await callback.message.edit_text(
            f"**Подтемы для __{theme_name}__**📋\n*Выберите подтему:*",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    finally:
        await db_utils.db.close()


# Функция для отображения рекомендаций эксперта
async def display_expert(subtheme_id: int, theme_id: int, expert_index: int, callback: CallbackQuery,
                         book_page: int = 0):
    await db_utils.db.connect()
    try:
        themes = await db_utils.get_available_themes()
        if not themes or theme_id < 0 or theme_id >= len(themes):
            await callback.message.answer("⚠️*Тема не найдена.*",
                                          reply_markup=main_kb(callback.from_user.id),
                                          parse_mode="Markdown")
            await callback.answer()
            return

        theme_name = themes[theme_id]
        subthemes = await db_utils.get_subthemes(theme_name)
        if not subthemes or subtheme_id < 0 or subtheme_id >= len(subthemes):
            await callback.message.answer(f"⚠️*Подтема для __{theme_name}__ не найдена.*",
                                          reply_markup=main_kb(callback.from_user.id),
                                          parse_mode="Markdown")
            await callback.answer()
            return

        subtheme_name = subthemes[subtheme_id]
        recommendations = await db_utils.get_expert_recommendations(subtheme_name)
        if not recommendations:
            await callback.message.answer(f"⚠️*Рекомендации по теме '{subtheme_name}' не найдены.*",
                                          reply_markup=main_kb(callback.from_user.id),
                                          parse_mode="Markdown")
            await callback.answer()
            return

        experts = list(recommendations.items())
        if expert_index < 0 or expert_index >= len(experts):
            await callback.answer("⚠️Эксперт не найден.")
            return

        expert_id, info = experts[expert_index]
        theme_id_db = await db_utils.get_theme_id(theme_name, subtheme_name)
        await db_utils.log_user_activity(
            user_id=callback.from_user.id,
            activity_type='get_expert_recommendation',
            theme_id=theme_id_db
        )

        # Пагинация книг
        books_per_page = 5
        total_books = len(info['books'])
        total_book_pages = (total_books + books_per_page - 1) // books_per_page

        start_idx = book_page * books_per_page
        end_idx = min(start_idx + books_per_page, total_books)
        current_books = info['books'][start_idx:end_idx]

        # Формируем текст
        response = f"📚*{subtheme_name}*\n\n"
        response += f"👤**{info['name']}** — *{info['position'][0].lower() + info['position'][1:]}*\n\n"
        response += "__Книги:__\n"

        for book_id, description in current_books:
            response += f"📖*{book_id}*\n💬{description}\n\n"

        if len(experts) > 1:
            response += f"👨‍🏫Эксперт {expert_index + 1} из {len(experts)}\n"

        if total_book_pages > 1:
            response += f"📄Страница книг {book_page + 1} из {total_book_pages}"

        # Книги: назад/вперед
        book_nav_buttons = []
        if book_page > 0:
            book_nav_buttons.append(InlineKeyboardButton(
                text="◄ Предыдущие книги",
                callback_data=f"books_{subtheme_id}_{theme_id}_{expert_index}_{book_page - 1}"
            ))
        if book_page < total_book_pages - 1:
            book_nav_buttons.append(InlineKeyboardButton(
                text="Следующие книги ►",
                callback_data=f"books_{subtheme_id}_{theme_id}_{expert_index}_{book_page + 1}"
            ))

        # Эксперт: назад/вперед
        expert_nav_buttons = []
        if expert_index > 0:
            expert_nav_buttons.append(InlineKeyboardButton(
                text="◄ Предыдущий эксперт",
                callback_data=f"expert_{subtheme_id}_prev_{theme_id}_{expert_index}"
            ))
        if expert_index < len(experts) - 1:
            expert_nav_buttons.append(InlineKeyboardButton(
                text="Следующий эксперт ►",
                callback_data=f"expert_{subtheme_id}_next_{theme_id}_{expert_index}"
            ))

        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        if book_nav_buttons:
            keyboard.inline_keyboard.append(book_nav_buttons)
        if expert_nav_buttons:
            keyboard.inline_keyboard.append(expert_nav_buttons)

        # Назад к подтемам
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                text=f"◄ Вернуться к подтемам",
                callback_data=f"subthemes_{theme_id}_0"
            )
        ])

        await callback.message.edit_text(response, reply_markup=keyboard, parse_mode="Markdown")
    finally:
        await db_utils.db.close()


async def handle_list(message: Message):
    await db_utils.db.connect()
    themes = await db_utils.get_available_themes()
    if not themes:
        await message.answer("⚠️*Темы отсутствуют.*",
                             reply_markup=main_kb(message.from_user.id),
                             parse_mode="Markdown")
        await db_utils.db.close()
        return

    items_per_page = 5
    page = 0
    total_pages = (len(themes) + items_per_page - 1) // items_per_page
    start_idx = page * items_per_page
    end_idx = min(start_idx + items_per_page, len(themes))
    current_themes = themes[start_idx:end_idx]

    # Создаем клавиатуру с кнопками тем
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"📖{theme}", callback_data=f"theme_{themes.index(theme)}")]
        for theme in current_themes
    ])

    # Добавляем кнопки навигации и возврата
    nav_buttons = []
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="Вперёд ►", callback_data=f"themes_page_{page + 1}"))
    if nav_buttons:
        keyboard.inline_keyboard.append(nav_buttons)
    keyboard.inline_keyboard.append(
        [InlineKeyboardButton(text=f"📄Страница {page + 1} из {total_pages}", callback_data=f"page_{page}")]
    )
    keyboard.inline_keyboard.append(
        [InlineKeyboardButton(text="◄ Вернуться в главное меню", callback_data="back_to_main")]
    )

    await message.answer(
        "**Выберите тему**📚\n*Доступные категории:*",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await db_utils.db.close()
