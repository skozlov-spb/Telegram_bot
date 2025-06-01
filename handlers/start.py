from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from keyboards.all_keyboards import main_kb, themes_inline_kb, subscribe_channels_kb

from create_bot import bot
from decouple import config

from db_handler.db_utils import DBUtils
from recommendation_system.model import RecommendationSystem
from db_handler.db_class import Database
from aiogram.exceptions import TelegramBadRequest
start_router = Router()

db = Database()
rec_sys = RecommendationSystem(db=db)
db_utils = DBUtils(db=db, bot=bot)


@start_router.message(CommandStart())
async def cmd_start(message: Message):
    await db_utils.db.connect()
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.full_name

    _ = await db_utils.register_user(user_id, username)
    # is_spbu_member = await db_utils.is_user_channel_member(user_id)
    is_spbu_member = True

    if not is_spbu_member:
        await message.answer(
            f"Привет! 👋\nДля использования бота необходимо подписаться "
            f"на наши каналы [СПБГУ]({config('CHANNEL_SPBU_LINK')}) и "
            f"[Ландау позвонит]({config('CHANNEL_LANDAU_LINK')}).\n"
            f"После подписки, пожалуйста, нажмите кнопку 'Я подписался!'",
            reply_markup=subscribe_channels_kb(),
            parse_mode="Markdown"
        )
        await db_utils.db.close()
        return

    await message.answer('**Добро пожаловать!** 🎉\nВыберите действие в меню ниже:',
                         reply_markup=main_kb(message.from_user.id), parse_mode="Markdown")
    await db_utils.db.close()


@start_router.callback_query(F.data == "check_subscription")
async def check_subscription_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    await db_utils.db.connect()

    is_spbu_member = await db_utils.is_user_channel_member(user_id)

    if is_spbu_member:
        await callback.message.delete()  # Удаляем предыдущее сообщение с кнопкой
        await callback.message.answer(
            "Спасибо за подписку! Теперь вы можете пользоваться ботом. 🎉",
            reply_markup=main_kb(user_id),
            parse_mode="Markdown"
        )
        await db_utils.log_user_activity(user_id, activity_type='subscribed_channels', theme_id=None) # Логируем
    else:
        await callback.answer("Вы еще не подписались на канал.", show_alert=True)  # Покажем всплывающее уведомление

    await db_utils.db.close()


@start_router.message(F.text == "📝 Получить рекомендации")
async def cmd_recc(message: Message):
    user_id = message.from_user.id
    await db_utils.db.connect()
    await db_utils.log_user_activity(user_id, activity_type='get_recommendation', theme_id=None)

    try:
        recommendations = await rec_sys.recommend(user_id)

        if not recommendations:
            await message.answer('**Рекомендации пока недоступны.**', reply_markup=main_kb(user_id),
                                 parse_mode="Markdown")
            return

    except Exception as e:
        await message.answer(f"Ошибка при получении рекомендаций {e}", reply_markup=main_kb(user_id))
        await db_utils.db.close()
        return

    await db_utils.db.close()

    response = "**Рекомендации на основе ваших запросов:**\n\n"
    book_count = 0
    for theme in recommendations:
        response += f"📚 *{theme['theme_name']} — {theme['specific_theme']}*\n\n"
        for expert in theme['experts']:
            if book_count >= 5:
                break
            expert_name = expert['expert_name']
            expert_position = expert['expert_position']
            book_name = expert['book_name']
            description = expert['description']
            response += f"👤 **{expert_name}** — *{expert_position[0].lower() + expert_position[1:]}.\n*"
            response += f"📖 {book_name}\n💬 {description}\n\n"
            book_count += 1

        if book_count >= 5:
            break

        # Send message if length exceeds Telegram limit
        if len(response) > 3000:
            await message.answer(response, reply_markup=main_kb(user_id), parse_mode="Markdown")
            response = ""

    if response:
        await message.answer(response, reply_markup=main_kb(user_id), parse_mode="Markdown")


# # Обработчик кнопки "Подписка"
# @start_router.message(F.text == "🔔 Подписаться на рассылку")
# async def handle_subscription(message: Message):
#     await db_utils.db.connect()
#     user_id = message.from_user.id
#     is_sub = await db_utils.is_subscribed(user_id)
#
#     # Создаем инлайн-клавиатуру
#     keyboard = InlineKeyboardMarkup(inline_keyboard=[[
#         InlineKeyboardButton(
#             text="Отписаться" if is_sub else "Подписаться",
#             callback_data="unsubscribe" if is_sub else "subscribe"
#         )
#     ]])
#
#     await message.answer(
#         text=f"Нажмите кнопку для "
#              f"{'подписки на рассылку' if not is_sub else 'отписки от рассылки'}:",
#         reply_markup=keyboard
#     )
#     await db_utils.db.close()


# Обработчик инлайн-кнопок подписки/отписки
@start_router.callback_query(F.data.in_(["subscribe", "unsubscribe"]))
async def process_subscription_callback(callback: CallbackQuery):
    await db_utils.db.connect()
    user_id = callback.from_user.id
    action = callback.data

    # Определяем новое состояние подписки

    # Логируем активность
    activity_type = "subscribe" if action == "subscribe" else "unsubscribe"
    await db_utils.log_user_activity(
        user_id=user_id,
        activity_type=activity_type,
        theme_id=None
    )

    response_text = "Вы подписались!" if action == "subscribe" else "Вы отписались!"

    try:
        # Удаляем сообщение бота
        await callback.message.delete()
    except TelegramBadRequest as _:
        # Обрабатываем возможные ошибки, например, если сообщение уже удалено
        pass

    await callback.message.answer(response_text, reply_markup=main_kb(user_id))
    await callback.answer()
    await db_utils.db.close()


# Функция для отображения списка тем с пагинацией
async def display_themes(page: int, callback: CallbackQuery):
    items_per_page = 5
    themes = await db_utils.get_available_themes()
    if not themes:
        await callback.message.answer("⚠️ *Темы отсутствуют.*", parse_mode="Markdown")
        await callback.answer()
        return

    total_pages = (len(themes) + items_per_page - 1) // items_per_page
    if page < 0 or page >= total_pages:
        await callback.answer("⚠️ Страница не существует.")
        return

    start_idx = page * items_per_page
    end_idx = min(start_idx + items_per_page, len(themes))
    current_themes = themes[start_idx:end_idx]

    # Создаем клавиатуру с кнопками тем
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"📖 {theme}", callback_data=f"theme_{themes.index(theme)}")]
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
        [InlineKeyboardButton(text=f"📄 Страница {page + 1} из {total_pages}", callback_data=f"page_{page}")]
    )
    keyboard.inline_keyboard.append(
        [InlineKeyboardButton(text="◄ Вернуться в главное меню", callback_data="back_to_main")]
    )

    await callback.message.edit_text(
        "**Выберите тему** 📚\n*Доступные категории:*",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


# Функция для отображения списка подтем с пагинацией
async def display_subthemes(theme_id: int, page: int, callback: CallbackQuery):
    themes = await db_utils.get_available_themes()
    if not themes or theme_id < 0 or theme_id >= len(themes):
        await callback.message.answer("⚠️ *Тема не найдена.*", parse_mode="Markdown")
        await callback.answer()
        return

    theme_name = themes[theme_id]
    subthemes = await db_utils.get_subthemes(theme_name)
    if not subthemes:
        await callback.message.answer(f"⚠️ *Подтемы для __{theme_name}__ не найдены.*", parse_mode="Markdown")
        await callback.answer()
        return

    items_per_page = 5
    total_pages = (len(subthemes) + items_per_page - 1) // items_per_page
    if page < 0 or page >= total_pages:
        await callback.answer("⚠️ Страница не существует.")
        return

    start_idx = page * items_per_page
    end_idx = min(start_idx + items_per_page, len(subthemes))
    current_subthemes = subthemes[start_idx:end_idx]

    # Создаем клавиатуру с кнопками подтем
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"📋 {subtheme}", callback_data=f"subtheme_{subthemes.index(subtheme)}_{theme_id}")]
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
        [InlineKeyboardButton(text=f"📄 Страница {page + 1} из {total_pages}", callback_data=f"page_{page}")]
    )
    keyboard.inline_keyboard.append(
        [InlineKeyboardButton(text="◄ Вернуться к темам", callback_data="get_themes")]
    )

    await callback.message.edit_text(
        f"**Подтемы для __{theme_name}__** 📋\n*Выберите подтему:*",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


# Функция для отображения рекомендаций эксперта
async def display_expert(subtheme_id: int, theme_id: int, expert_index: int, callback: CallbackQuery,
                         book_page: int = 0):
    themes = await db_utils.get_available_themes()
    if not themes or theme_id < 0 or theme_id >= len(themes):
        await callback.message.answer("⚠️ *Тема не найдена.*", parse_mode="Markdown")
        await callback.answer()
        return

    theme_name = themes[theme_id]
    subthemes = await db_utils.get_subthemes(theme_name)
    if not subthemes or subtheme_id < 0 or subtheme_id >= len(subthemes):
        await callback.message.answer(f"⚠️ *Подтема для __{theme_name}__ не найдена.*", parse_mode="Markdown")
        await callback.answer()
        return

    subtheme_name = subthemes[subtheme_id]
    recommendations = await db_utils.get_expert_recommendations(subtheme_name)
    if not recommendations:
        await callback.message.answer(f"⚠️ *Рекомендации по теме '{subtheme_name}' не найдены.*", parse_mode="Markdown")
        await callback.answer()
        return

    experts = list(recommendations.items())
    if expert_index < 0 or expert_index >= len(experts):
        await callback.answer("⚠️ Эксперт не найден.")
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
    response = f"*{subtheme_name}* 📚\n\n"
    response += f"👤 **{info['name']}** — *{info['position'][0] + info['position'][1:]}.*\n\n"
    response += "__Книги:__\n"

    for book_id, description in current_books:
        response += f"📖 *{book_id}*\n💬 {description}\n\n"

    if len(experts) > 1:
        response += f"👨‍🏫 Эксперт {expert_index + 1} из {len(experts)}\n"

    if total_book_pages > 1:
        response += f"📄 Страница книг {book_page + 1} из {total_book_pages}"
    # Кнопки
    buttons = []

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
            text=f"◄ Вернуться к подтемам {theme_name}",
            callback_data=f"subthemes_{theme_id}_0"
        )
    ])

    await callback.message.edit_text(response, reply_markup=keyboard, parse_mode="Markdown")


# Обработчик команды "📚 Просмотреть подборки от экспертов"
@start_router.message(F.text == "📚 Просмотреть подборки от экспертов")
async def expert_recommendation(message: Message):
    await db_utils.db.connect()
    themes = await db_utils.get_available_themes()
    if not themes:
        await message.answer("⚠️ *Темы отсутствуют.*", parse_mode="Markdown")
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
        [InlineKeyboardButton(text=f"📖 {theme}", callback_data=f"theme_{themes.index(theme)}")]
        for theme in current_themes
    ])

    # Добавляем кнопки навигации и возврата
    nav_buttons = []
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="Вперёд ►", callback_data=f"themes_page_{page + 1}"))
    if nav_buttons:
        keyboard.inline_keyboard.append(nav_buttons)
    keyboard.inline_keyboard.append(
        [InlineKeyboardButton(text=f"📄 Страница {page + 1} из {total_pages}", callback_data=f"page_{page}")]
    )
    keyboard.inline_keyboard.append(
        [InlineKeyboardButton(text="◄ Вернуться в главное меню", callback_data="back_to_main")]
    )

    await message.answer(
        "**Выберите тему** 📚\n*Доступные категории:*",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await db_utils.db.close()


# Обработчик callback-запросов
@start_router.callback_query(F.data.in_(['get_themes', 'back_to_main']) | F.data.regexp(
    r'^(themes_page|theme|subthemes|subtheme|expert|page|index|books)_'))
async def process_callback_expert_rec(callback: CallbackQuery):
    data = callback.data
    await db_utils.db.connect()

    if data == "back_to_main":
        await callback.message.delete()
        await callback.message.answer(
            '**Выберите действие в меню ниже:',
            reply_markup=main_kb(callback.from_user.id),
            parse_mode="Markdown"
        )
        await callback.answer()

    elif data == "get_themes":
        await display_themes(0, callback)

    elif data.startswith("themes_page_"):
        parts = data.split("_")
        if len(parts) == 3 and parts[2].isdigit():
            page = int(parts[2])
            await display_themes(page, callback)
        else:
            await callback.message.answer("⚠️ *Некорректный номер страницы.*", parse_mode="Markdown")
            await callback.answer()

    elif data.startswith("theme_"):
        parts = data.split("_")
        if len(parts) == 2 and parts[1].isdigit():
            theme_id = int(parts[1])
            await display_subthemes(theme_id, 0, callback)
        else:
            await callback.message.answer("⚠️ *Некорректный идентификатор темы.*", parse_mode="Markdown")
            await callback.answer()

    elif data.startswith("subthemes_"):
        parts = data.split("_")
        if len(parts) == 3 and parts[1].isdigit() and parts[2].isdigit():
            theme_id = int(parts[1])
            page = int(parts[2])
            await display_subthemes(theme_id, page, callback)
        else:
            await callback.message.answer("⚠️ *Некорректный идентификатор темы или страницы.*", parse_mode="Markdown")
            await callback.answer()

    elif data.startswith("subtheme_"):
        parts = data.split("_")
        if len(parts) == 3 and parts[1].isdigit() and parts[2].isdigit():
            subtheme_id = int(parts[1])
            theme_id = int(parts[2])
            await display_expert(subtheme_id, theme_id, 0, callback)
        else:
            await callback.message.answer("⚠️ *Некорректный идентификатор подтемы или темы.*", parse_mode="Markdown")
            await callback.answer()

    elif data.startswith("expert_"):
        parts = data.split("_")
        if (len(parts) == 5 and parts[1].isdigit() and parts[3].isdigit() and
                parts[4].isdigit() and parts[2] in ["next", "prev"]):
            subtheme_id = int(parts[1])
            action = parts[2]
            theme_id = int(parts[3])
            current_index = int(parts[4])
            if action == "next":
                current_index += 1
            elif action == "prev":
                current_index -= 1
            await display_expert(subtheme_id, theme_id, current_index, callback)
        else:
            await callback.message.answer("⚠️ *Некорректные данные для эксперта.*", parse_mode="Markdown")
            await callback.answer()

    elif data.startswith("books_"):
        parts = data.split("_")
        if len(parts) == 5 and all(p.isdigit() for p in parts[1:]):
            subtheme_id = int(parts[1])
            theme_id = int(parts[2])
            expert_index = int(parts[3])
            book_page = int(parts[4])
            await display_expert(subtheme_id, theme_id, expert_index, callback, book_page)
    else:
        await callback.message.answer("⚠️ *Неизвестное действие.*", parse_mode="Markdown")
        await callback.answer()

    await db_utils.db.close()
