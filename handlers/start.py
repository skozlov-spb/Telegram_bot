from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from db_handler.db_utils import DBUtils
from db_handler.db_class import Database

from keyboards.all_keyboards import main_kb, themes_inline_kb
from create_bot import bot

start_router = Router()

db = Database()
db_utils = DBUtils(db=db, bot=bot)


@start_router.message(CommandStart())
async def cmd_start(message: Message):
    await db_utils.db.connect()
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.full_name
    is_new_user = await db_utils.register_user(user_id, username)
    
    await message.answer('**Добро пожаловать!** 🎉\nВыберите действие в меню ниже:',
                         reply_markup=main_kb(message.from_user.id), parse_mode="Markdown")
    await db_utils.db.close()


@start_router.message(F.text == "Привет")
async def cmd_start_3(message: Message):
    await message.answer('Привет! 😊 *Готов помочь!*')


@start_router.message(F.text == "📝 Рекомендация")
async def cmd_start_3(message: Message):
    await db_utils.db.connect()
    user_id = message.from_user.id
    await db_utils.log_user_activity(user_id, activity_type='get_recommenadation', theme_id=None)
    await db_utils.db.close()
    await message.answer('**В разработке...**', parse_mode="Markdown")


@start_router.message(F.text == "📚 Рекомендация экспертов")
async def expert_recommendation(message: Message):
    await message.answer(
        "**Выберите тему для рекомендаций** 📖\nНажмите на кнопку ниже, чтобы начать:",
        reply_markup=themes_inline_kb(), parse_mode="Markdown"
    )


# Обработчик для callback-запросов инлайн-кнопок экспертов
@start_router.callback_query()
async def process_callback(callback: CallbackQuery):
    data = callback.data
    await db_utils.db.connect()

    if data.startswith("themes_page_") or data == "get_themes":
        # Пагинация тем
        if data == "get_themes":
            page = 0
        else:
            page = int(data.split("_")[-1])
        items_per_page = 5

        # Получение всех тем
        themes = await db_utils.get_available_themes()
        if not themes:
            await callback.message.answer("⚠️ *Темы отсутствуют.*")
            await callback.answer()
            return

        # Вычисление границ страницы
        total_pages = (len(themes) + items_per_page - 1) // items_per_page
        start_idx = page * items_per_page
        end_idx = min(start_idx + items_per_page, len(themes))
        current_themes = themes[start_idx:end_idx]

        # Создание инлайн-кнопок для текущей страницы
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"📖 {theme}", callback_data=f"theme_{current_themes.index(theme) + start_idx}")]
            for theme in current_themes
        ])

        # Добавление кнопок пагинации
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(text="◄ Назад", callback_data=f"themes_page_{page - 1}"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton(text="Вперёд ►", callback_data=f"themes_page_{page + 1}"))
        if nav_buttons:
            keyboard.inline_keyboard.append(nav_buttons)
        keyboard.inline_keyboard.append(
            [InlineKeyboardButton(text=f"📄 Страница {page + 1} из {total_pages}", callback_data=f"page_{page}")])

        await callback.message.edit_text("**Выберите тему** 📚\n*Доступные категории:*", reply_markup=keyboard,
                                         parse_mode="Markdown")

    elif data.startswith("theme_") or data.startswith("subthemes_"):
        # Пагинация подтем
        if data.startswith("theme_"):
            theme_id = data[len("theme_"):]
            page = 0
        else:
            theme_id, page = data[len("subthemes_"):].split("_")
            page = int(page)

        theme_id = int(theme_id)
        items_per_page = 5

        # Получение подтем
        themes = await db_utils.get_available_themes()
        theme_name = themes[theme_id]
        subthemes = await db_utils.get_subthemes(theme_name)
        if not subthemes:
            await callback.message.answer(f"⚠️ *Подтемы для __{theme_name}__ не найдены.*", parse_mode="Markdown")
            await callback.answer()
            return

        # Вычисление границ страницы
        total_pages = (len(subthemes) + items_per_page - 1) // items_per_page
        start_idx = page * items_per_page
        end_idx = min(start_idx + items_per_page, len(subthemes))
        current_subthemes = subthemes[start_idx:end_idx]

        # Создание инлайн-кнопок для текущей страницы
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"📋 {subtheme}",
                                  callback_data=f"subtheme_{current_subthemes.index(subtheme) + start_idx}_{theme_id}")]
            for subtheme in current_subthemes
        ])

        # Добавление кнопок пагинации
        nav_buttons = []
        if page > 0:
            nav_buttons.append(
                InlineKeyboardButton(text="◄ Назад", callback_data=f"subthemes_{theme_id}_{page - 1}"))
        if page < total_pages - 1:
            nav_buttons.append(
                InlineKeyboardButton(text="Вперёд ►", callback_data=f"subthemes_{theme_id}_{page + 1}"))
        if nav_buttons:
            keyboard.inline_keyboard.append(nav_buttons)
        keyboard.inline_keyboard.append(
            [InlineKeyboardButton(text=f"📄 Страница {page + 1} из {total_pages}", callback_data=f"page_{page}")])

        await callback.message.edit_text(f"**Подтемы для __{theme_name}__** 📋\n*Выберите подтему:*",
                                         reply_markup=keyboard, parse_mode="Markdown")

    elif data.startswith("subtheme_") or data.startswith("expert_"):
        # Инициализация переменных
        if data.startswith("subtheme_"):
            subtheme_id, theme_id = data[len("subtheme_"):].split("_")
            current_index = 0
        else:
            # Извлечение подтемы и индекса из callback
            subtheme_id, action, theme_id = data[len("expert_"):].split("_")
            current_index = int(callback.message.reply_markup.inline_keyboard[-1][0].callback_data.split("_")[-1])
            if action == "next":
                current_index += 1
            elif action == "prev":
                current_index -= 1
        subtheme_id = int(subtheme_id)
        theme_id = int(theme_id)

        themes = await db_utils.get_available_themes()
        theme_name = themes[theme_id]

        subthemes = await db_utils.get_subthemes(theme_name)
        subtheme_name = subthemes[subtheme_id]

        # Получение рекомендаций экспертов
        recommendations = await db_utils.get_expert_recommendations(subtheme_name)
        if not recommendations:
            await callback.message.answer(f"⚠️ *Рекомендации для __{subtheme_name}__ не найдены.*",
                                          parse_mode="Markdown")
            await callback.answer()
            return

        # Преобразование рекомендаций в список для удобного доступа по индексу
        experts = list(recommendations.items())
        if current_index < 0 or current_index >= len(experts):
            await callback.answer("⚠️ Больше экспертов нет.")
            return

        # Получение данных текущего эксперта
        expert_id, info = experts[current_index]

        # Форматирование ответа
        theme_id = await db_utils.get_theme_id(theme_name, subtheme_name)
        await db_utils.log_user_activity(user_id=callback.from_user.id, activity_type='get_expert_recommendation', theme_id=theme_id)
        
        response = f"**Рекомендации для __{subtheme_name}__** 📚\n\n"
        response += f"👤 **{info['name']}** *({info['position']})*\n\n"
        response += "__Книги:__\n"
        for book_id, description in info['books']:
            # Получение названия книги по book_id
            book_name = book_id
            response += f"📖 *{book_name}*\n💬 {description}\n\n"

        # Создание инлайн-кнопок для перелистывания
        buttons = []
        if current_index > 0:
            buttons.append(InlineKeyboardButton(text="◄ Назад", callback_data=f"expert_{subtheme_id}_prev_{theme_id}"))
        if current_index < len(experts) - 1:
            buttons.append(InlineKeyboardButton(text="Вперёд ►", callback_data=f"expert_{subtheme_id}_next_{theme_id}"))

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            buttons,
            [InlineKeyboardButton(text=f"👨‍🏫 Эксперт {current_index + 1} из {len(experts)}",
                                  callback_data=f"index_{current_index}")]
        ])

        # Обновление сообщения
        await callback.message.edit_text(response, parse_mode="Markdown", reply_markup=keyboard)

    await callback.answer()
    await db_utils.db.close()
