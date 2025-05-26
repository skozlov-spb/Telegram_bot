from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import BotCommand, BotCommandScopeDefault

from create_bot import admins, bot, dp


def main_kb(user_telegram_id: int):
    kb_list = [
        [KeyboardButton(text="📚 Просмотреть подборки от экспертов"), KeyboardButton(text="📝 Получить рекомендации"), ],
        [KeyboardButton(text="🔔 Подписаться на рассылку")]
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
        [
            InlineKeyboardButton(text="❌ Книгу", callback_data="admin_delete_book"),
            InlineKeyboardButton(text="❌ Подборку", callback_data="admin_select_theme"),
            InlineKeyboardButton(text="❌ Эксперта", callback_data="admin_select_expert")
        ],
        [
            InlineKeyboardButton(text="📩 Сделать рассылку", callback_data="admin_broadcast"),
            InlineKeyboardButton(text="👑 Добавить администратора", callback_data="admin_add_admin")
        ],
        [InlineKeyboardButton(text="🔙 Меню", callback_data="admin_back_to_menu")]
    ])
    return admin_keyboard
