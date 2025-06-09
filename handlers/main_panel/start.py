from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from keyboards.all_keyboards import subscribe_channels_kb, main_kb
from db_handler.db_class import Database
from db_handler.db_utils import DBUtils
from create_bot import bot

router = Router()

db = Database()
db_utils = DBUtils(db=db, bot=bot)


@router.message(CommandStart())
async def cmd_start(message: Message):
    await db_utils.db.connect()
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.full_name

    _ = await db_utils.register_user(user_id, username)
    # is_spbu_member = await db_utils.is_user_channel_member(user_id)  # До вывода в прод лучше закоммитить функцию
    is_spbu_member = True

    if not is_spbu_member:
        await message.answer(
            f"Привет! 👋\nДля использования бота необходимо подписаться "
            f"на наши каналы [Что там СПбГУ](https://t.me/spbuniversity1724) и "
            f"[Ландау позвонит](https://t.me/spbuniversity).\n"
            f"После подписки, пожалуйста, нажмите кнопку «Я подписался!»",
            reply_markup=subscribe_channels_kb(),
            parse_mode="Markdown"
        )
        await db_utils.db.close()
        return

    await message.answer('**🎉Добро пожаловать!**\nВыберите действие в меню ниже:',
                         reply_markup=main_kb(message.from_user.id), parse_mode="Markdown")
    await db_utils.db.close()
