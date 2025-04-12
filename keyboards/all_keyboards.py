from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.types import BotCommand, BotCommandScopeDefault

from create_bot import admins, bot


def main_kb(user_telegram_id: int):
    kb_list = [
        [KeyboardButton(text="📝 Рекомендация"), KeyboardButton(text="📚 Рекомендация экспертов")]
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
