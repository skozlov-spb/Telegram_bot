from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import BotCommand, BotCommandScopeDefault

from create_bot import bot, admins


def main_kb(user_telegram_id: int):
    kb_list = [
        [KeyboardButton(text="📚 Просмотреть подборки от экспертов"), KeyboardButton(text="📝 Получить рекомендации"), ],
        # [KeyboardButton(text="🔔 Подписаться на рассылку")]
    ]
    if user_telegram_id in admins:
        kb_list.append([KeyboardButton(text="⚙️ Админ панель")])

    keyboard = ReplyKeyboardMarkup(
        keyboard=kb_list,
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Воспользуйтесь меню:"
    )
    return keyboard


async def set_commands():
    commands = [BotCommand(command='start', description='Старт')]
    await bot.set_my_commands(commands, BotCommandScopeDefault())


def themes_inline_kb():
    """Создает инлайн-клавиатуру с кнопкой 'Получить темы'"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Получить темы", callback_data="get_themes")]
    ])
    return keyboard


def admin_panel_kb():
    admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Получить статистику", callback_data="admin_get_stats")],
        [InlineKeyboardButton(text="📤 Загрузить данные", callback_data="admin_upload_data")],
        [InlineKeyboardButton(text="🗑️ Удалить данные", callback_data="admin_delete_menu")],
        # [
        #     InlineKeyboardButton(text="🗑️ Книгу", callback_data="admin_delete_book"),
        #     InlineKeyboardButton(text="🗑️ Подборку", callback_data="admin_select_theme"),
        #     InlineKeyboardButton(text="🗑️ Эксперта", callback_data="admin_select_expert")
        # ],
        [InlineKeyboardButton(text="👑 Добавить администратора", callback_data="admin_add_admin")],
        # [InlineKeyboardButton(text="📩 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="◄ Меню", callback_data="admin_back_to_menu")]
    ])
    return admin_keyboard


def admin_delete_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑️ Удалить книгу", callback_data="admin_delete_book")],
        [InlineKeyboardButton(text="🗑️ Удалить подборку", callback_data="admin_select_theme")],
        [InlineKeyboardButton(text="🗑️ Удалить эксперта", callback_data="admin_select_expert")],
        [InlineKeyboardButton(text="◄ Назад", callback_data="admin_back_to_panel")]
    ])


def subscribe_channels_kb():
    """Создает инлайн-клавиатуру для проверки подписки на канал."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Я подписался!", callback_data="check_subscription")]
    ])
    return keyboard
