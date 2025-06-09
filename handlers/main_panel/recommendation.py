from aiogram.types import Message
from db_handler.db_utils import DBUtils
from recommendation_system.model import RecommendationSystem
from db_handler.db_class import Database
from keyboards.all_keyboards import main_kb
from create_bot import bot

db = Database()
db_utils = DBUtils(db=db, bot=bot)
rec_sys = RecommendationSystem(db=db)


async def handle_recommendation(message: Message):
    user_id = message.from_user.id
    await db_utils.db.connect()
    await db_utils.log_user_activity(user_id, activity_type='get_recommendation', theme_id=None)

    try:
        recommendations = await rec_sys.recommend(user_id)

        if not recommendations:
            await message.answer('Если вы еще не посмотрели __ни одной__ подборки от экспертов, то рекомендации '
                                 '__не будут работать__.',
                                 reply_markup=main_kb(user_id),
                                 parse_mode="Markdown")
            return

    except Exception as _:
        await message.answer('__Ошибка получения рекомендации!__\n',
                             reply_markup=main_kb(user_id))
        await db_utils.db.close()
        return

    await db_utils.db.close()

    response = "**Рекомендации на основе ваших запросов:**\n\n"
    book_count = 0
    for theme in recommendations:
        response += f"📚*{theme['theme_name']} — {theme['specific_theme']}*\n\n"
        for expert in theme['experts']:
            if book_count >= 5:
                break
            expert_name = expert['expert_name']
            expert_position = expert['expert_position']
            book_name = expert['book_name']
            description = expert['description']
            response += f"👤**{expert_name}** — *{expert_position[0].lower() + expert_position[1:]}.\n*"
            response += f"📖{book_name}\n💬{description}\n\n"
            book_count += 1

        if book_count >= 5:
            break

        # Send message if length exceeds Telegram limit
        if len(response) > 3000:
            await message.answer(response, reply_markup=main_kb(user_id), parse_mode="Markdown")
            response = ""

    if response:
        await message.answer(response, reply_markup=main_kb(user_id), parse_mode="Markdown")
