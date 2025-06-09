from aiogram import Router, F
from aiogram.types import CallbackQuery

from keyboards.all_keyboards import main_kb
from db_handler.db_class import Database
from db_handler.db_utils import DBUtils

from handlers.main_panel.lists import display_themes
from handlers.main_panel.lists import display_subthemes
from handlers.main_panel.lists import display_expert
from create_bot import bot

router = Router()

db = Database()
db_utils = DBUtils(db=db, bot=bot)


@router.callback_query(
    F.data.in_(['get_themes', 'back_to_main']) |
    F.data.regexp(r'^(themes_page|theme|subthemes|subtheme|expert|page|books)_')
)
async def process_callback_expert_rec(callback: CallbackQuery):
    data = callback.data
    user_id = callback.from_user.id
    await db_utils.db.connect()

    if data == "back_to_main":
        await callback.message.delete()
        await callback.message.answer(
            '**Выберите действие в меню ниже:**',
            reply_markup=main_kb(user_id),
            parse_mode="Markdown"
        )
        await callback.answer()
    elif data == "get_themes":
        await display_themes(page=0, callback=callback)
    elif data.startswith("themes_page_"):
        _, _, page = data.split("_")
        if page.isdigit():
            await display_themes(page=int(page), callback=callback)
        else:
            await callback.answer("⚠️ Некорректный номер страницы.")
    elif data.startswith("theme_"):
        _, theme_id = data.split("_")
        if theme_id.isdigit():
            await display_subthemes(theme_id=int(theme_id), page=0, callback=callback)
        else:
            await callback.answer("⚠️ Некорректный идентификатор темы.")
    elif data.startswith("subthemes_"):
        _, theme_id, page = data.split("_")
        if theme_id.isdigit() and page.isdigit():
            await display_subthemes(theme_id=int(theme_id), page=int(page), callback=callback)
        else:
            await callback.answer("⚠️ Некорректные параметры.")
    elif data.startswith("subtheme_"):
        _, subtheme_id, theme_id = data.split("_")
        if subtheme_id.isdigit() and theme_id.isdigit():
            await display_expert(subtheme_id=int(subtheme_id),
                                 theme_id=int(theme_id),
                                 expert_index=0,
                                 callback=callback)
        else:
            await callback.answer("⚠️ Некорректный идентификатор подтемы.")
    elif data.startswith("expert_"):
        # expert_{subtheme_id}_{action}_{theme_id}_{index}
        parts = data.split("_")
        if len(parts) == 5 and parts[1].isdigit() and parts[4].isdigit():
            _, sub_id, action, theme_id, idx = parts
            idx = int(idx) + (1 if action == "next" else -1)
            await display_expert(
                subtheme_id=int(sub_id),
                theme_id=int(theme_id),
                expert_index=idx,
                callback=callback
            )
        else:
            await callback.answer("⚠️ Некорректные данные для эксперта.")
    elif data.startswith("books_"):
        # books_{subtheme_id}_{theme_id}_{expert_index}_{book_page}
        _, sub_id, theme_id, expert_idx, book_page = data.split("_")
        await display_expert(
            subtheme_id=int(sub_id),
            theme_id=int(theme_id),
            expert_index=int(expert_idx),
            callback=callback,
            book_page=int(book_page)
        )
    else:
        await callback.answer()

    await db_utils.db.close()
