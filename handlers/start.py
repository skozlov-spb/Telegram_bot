from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from db_handler.db_utils import DBUtils
from db_handler.db_class import Database

from keyboards.all_keyboards import main_kb, themes_inline_kb
from create_bot import bot

start_router = Router()
db_utils = DBUtils(db=Database(), bot=bot)


@start_router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer('Меню',
                         reply_markup=main_kb(message.from_user.id))


@start_router.message(Command('start_2'))
async def cmd_start_2(message: Message):
    await message.answer('Меню 2',
                         reply_markup=create_spec_kb())


@start_router.message(F.text == 'привет')
async def cmd_start_3(message: Message):
    await message.answer('Привет!')

@start_router.message(F.text == "📚 Рекомендация экспертов")
async def expert_recommendation(message: Message):
    await message.answer(
        "Нажмите ниже, чтобы выбрать тему для рекомендаций экспертов:",
        reply_markup=themes_inline_kb()
    )


# Обработчик для callback-запросов инлайн-кнопок
@start_router.callback_query()
async def process_callback(callback: CallbackQuery):
    data = callback.data

    if data == "get_themes":
        # Получение доступных тем
        themes: List[str] =  await db_utils.get_available_themes()
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
        subthemes: List[str] =  await db_utils.get_subthemes(theme_name)
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

    elif data.startswith("subtheme_"):
        # Извлечение названия подтемы
        subtheme_name = data[len("subtheme_"):]

        # Получение рекомендаций экспертов
        recommendations: Optional[dict] = await db_utils.get_expert_recommendations(subtheme_name)
        if not recommendations:
            await callback.message.answer(f"Рекомендации для {subtheme_name} не найдены.")
            await callback.answer()
            return

        # Форматирование рекомендаций
        response = f"Рекомендации для {subtheme_name}:\n\n"
        for book_id, info in recommendations.items():
            response += (
                f"📖 *Книга*: {info['book_name']}\n"
                f"👤 *Эксперт*: {info['expert_name']} ({info['expert_position']})\n"
                f"💬 *Описание*: {info['description']}\n\n"
            )

        await callback.message.edit_text(response, parse_mode="Markdown")

    await callback.answer()
