from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from db_handler.db_utils import DBUtils
from db_handler.db_class import Database

from keyboards.all_keyboards import main_kb, themes_inline_kb
from create_bot import bot

start_router = Router()


@start_router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer('Меню',
                         reply_markup=main_kb(message.from_user.id))


@start_router.message(F.text == 'привет')
async def cmd_start_3(message: Message):
    await message.answer('Привет!')


@start_router.message(F.text == "📚 Рекомендация экспертов")
async def expert_recommendation(message: Message):
    await message.answer(
        "Нажмите ниже, чтобы выбрать тему для рекомендаций экспертов:",
        reply_markup=themes_inline_kb()
    )


# Обработчик для callback-запросов инлайн-кнопок экспертов
@start_router.callback_query()
async def process_callback(callback: CallbackQuery):
    data = callback.data
    db_utils = DBUtils(db=Database(), bot=bot)
    await db_utils.db.connect()

    if data == "get_themes":
        # Получение доступных тем
        themes = await db_utils.get_available_themes()
        if not themes:
            await callback.message.answer("Темы отсутствуют.")
            await callback.answer()
            return

        # Создание инлайн-кнопок для каждой темы
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=theme, callback_data=f"theme_{theme}")]
            for theme in themes
        ])
        await callback.message.edit_text("Выберите тему:", reply_markup=keyboard)

    elif data.startswith("theme_"):
        # Извлечение названия темы
        theme_name = data[len("theme_"):]

        # Получение подтем
        subthemes = await db_utils.get_subthemes(theme_name)
        if not subthemes:
            await callback.message.answer(f"Подтемы для {theme_name} не найдены.")
            await callback.answer()
            return

        # Создание инлайн-кнопок для подтем
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=subtheme, callback_data=f"subtheme_{subtheme}")]
            for subtheme in subthemes
        ])
        await callback.message.edit_text(f"Выберите подтему для {theme_name}:", reply_markup=keyboard)

    elif data.startswith("subtheme_") or data.startswith("expert_"):
        # Инициализация переменных
        if data.startswith("subtheme_"):
            subtheme_name = data[len("subtheme_"):]
            current_index = 0
        else:
            # Извлечение подтемы и индекса из callback
            subtheme_name, action = data[len("expert_"):].split("_")
            current_index = int(callback.message.reply_markup.inline_keyboard[-1][0].callback_data.split("_")[-1])
            if action == "next":
                current_index += 1
            elif action == "prev":
                current_index -= 1

        # Получение рекомендаций экспертов
        recommendations = await db_utils.get_expert_recommendations(subtheme_name)
        if not recommendations:
            await callback.message.answer(f"Рекомендации для {subtheme_name} не найдены.")
            await callback.answer()
            return

        # Преобразование рекомендаций в список для удобного доступа по индексу
        experts = list(recommendations.items())
        if current_index < 0 or current_index >= len(experts):
            await callback.answer("Больше экспертов нет.")
            return

        # Получение данных текущего эксперта
        expert_id, info = experts[current_index]

        # Форматирование ответа
        response = f"**Рекомендации для {subtheme_name}**\n\n"
        response += f"👤 **{info['name']}** ({info['position']})\n"
        response += "📚 **Книги**:\n"
        for book_id, description in info['books']:
            # Получение названия книги по book_id
            book_name = book_id
            response += f"📖 {book_name}\n💬 {description}\n\n"

        # Создание инлайн-кнопок для перелистывания
        buttons = []
        if current_index > 0:
            buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"expert_{subtheme_name}_prev"))
        if current_index < len(experts) - 1:
            buttons.append(InlineKeyboardButton(text="Вперед ➡️", callback_data=f"expert_{subtheme_name}_next"))

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            buttons,
            [InlineKeyboardButton(text=f"Эксперт {current_index + 1}/{len(experts)}",
                                  callback_data=f"index_{current_index}")]
        ])

        # Обновление сообщения
        await callback.message.edit_text(response, parse_mode="Markdown", reply_markup=keyboard)

    await callback.answer()
    await db_utils.db.close()
