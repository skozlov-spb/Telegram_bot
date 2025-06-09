from aiogram import Router, F
from aiogram.types import Message

from handlers.main_panel.recommendation import handle_recommendation
from handlers.main_panel.lists import handle_list
from handlers.main_panel.broadcast import handle_broadcast

router = Router()


@router.message(F.text == "📝Получить рекомендации")
async def cmd_recommend(message: Message):
    await handle_recommendation(message)


@router.message(F.text == "📚Просмотреть подборки от экспертов")
async def cmd_expert_list(message: Message):
    await handle_list(message)


@router.message(F.text == "🔔 Подписаться на рассылку")
async def cmd_letters(message: Message):
    await handle_broadcast(message)
