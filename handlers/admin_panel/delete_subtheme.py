from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from keyboards.all_keyboards import main_kb, admin_delete_menu_kb
from db_handler.db_utils import DBUtils
from db_handler.db_class import Database
import create_bot
from create_bot import bot
from handlers.admin_panel.states import AdminActions

admin_router = Router()
db_utils = DBUtils(db=Database(), bot=bot)


@admin_router.callback_query(F.data == "admin_delete_menu")
async def show_delete_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "Выберите что хотите удалить:",
        reply_markup=admin_delete_menu_kb()
    )
    await callback.answer()


@admin_router.callback_query(
    F.data.in_(['admin_select_theme']) | F.data.regexp(
        r'^(admin_themes_page|admin_theme|admin_subthemes|admin_delete_subtheme)_')
)
async def process_theme_selection(callback: CallbackQuery, state: FSMContext):
    await db_utils.db.connect()
    user_id = callback.from_user.id

    if user_id not in create_bot.admins:
        await callback.message.answer("У вас нет доступа к админ-панели.", reply_markup=main_kb(user_id))
        await callback.answer()
        await db_utils.db.close()
        return

    action = callback.data

    if action == "admin_select_theme" or action.startswith("admin_themes_page_"):
        if action == "admin_select_theme":
            page = 0
        else:
            page = int(action.split("_")[-1])
        items_per_page = 5

        themes = await db_utils.get_available_themes()
        if not themes:
            await callback.message.answer("⚠️*Темы отсутствуют.*", reply_markup=main_kb(user_id), parse_mode="Markdown")
            await callback.answer()
            await db_utils.db.close()
            return

        total_pages = (len(themes) + items_per_page - 1) // items_per_page
        start_idx = page * items_per_page
        end_idx = min(start_idx + items_per_page, len(themes))
        current_themes = themes[start_idx:end_idx]

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"📖{theme}",
                                  callback_data=f"admin_theme_{current_themes.index(theme) + start_idx}")]
            for theme in current_themes
        ])

        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(text="◄ Назад", callback_data=f"admin_themes_page_{page - 1}"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton(text="Вперёд ►", callback_data=f"admin_themes_page_{page + 1}"))
        if nav_buttons:
            keyboard.inline_keyboard.append(nav_buttons)
        keyboard.inline_keyboard.append(
            [InlineKeyboardButton(text=f"📄Страница {page + 1} из {total_pages}", callback_data=f"admin_page_{page}")]
        )
        keyboard.inline_keyboard.append(
            [InlineKeyboardButton(text="◄ Назад в админ-панель", callback_data="admin_back_to_panel")]
        )

        await callback.message.edit_text("**Выберите тему для удаления**📚\n*Доступные категории:*",
                                         reply_markup=keyboard, parse_mode="Markdown")

    elif action.startswith("admin_theme_") or action.startswith("admin_subthemes_"):
        if action.startswith("admin_theme_"):
            theme_id = action[len("admin_theme_"):]
            page = 0
        else:
            theme_id, page = action[len("admin_subthemes_"):].split("_")
            page = int(page)

        theme_id = int(theme_id)
        items_per_page = 5

        themes = await db_utils.get_available_themes()
        theme_name = themes[theme_id]
        subthemes = await db_utils.get_subthemes(theme_name)
        if not subthemes:
            await callback.message.answer(f"⚠️*Подтемы для __{theme_name}__ не найдены.*", parse_mode="Markdown")
            await callback.answer()
            await db_utils.db.close()
            return

        total_pages = (len(subthemes) + items_per_page - 1) // items_per_page
        start_idx = page * items_per_page
        end_idx = min(start_idx + items_per_page, len(subthemes))
        current_subthemes = subthemes[start_idx:end_idx]

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"📋{subtheme}",
                                  callback_data=f"admin_delete_subtheme_{theme_id}_"
                                                f"{current_subthemes.index(subtheme) + start_idx}")]
            for subtheme in current_subthemes
        ])

        nav_buttons = []
        if page > 0:
            nav_buttons.append(
                InlineKeyboardButton(text="◄ Назад", callback_data=f"admin_subthemes_{theme_id}_{page - 1}"))
        if page < total_pages - 1:
            nav_buttons.append(
                InlineKeyboardButton(text="Вперёд ►", callback_data=f"admin_subthemes_{theme_id}_{page + 1}"))
        if nav_buttons:
            keyboard.inline_keyboard.append(nav_buttons)
        keyboard.inline_keyboard.append(
            [InlineKeyboardButton(text=f"📄Страница {page + 1} из {total_pages}", callback_data=f"admin_page_{page}")]
        )
        keyboard.inline_keyboard.append(
            [InlineKeyboardButton(text="◄ Назад к темам", callback_data=f"admin_select_theme")]
        )

        await callback.message.edit_text(f"**Подтемы для __{theme_name}__**📋\n*Выберите подтему для удаления:*",
                                         reply_markup=keyboard, parse_mode="Markdown")

    elif action.startswith("admin_delete_subtheme_"):
        theme_id, subtheme_id = action[len("admin_delete_subtheme_"):].split("_")
        subtheme_id = int(subtheme_id)
        theme_id = int(theme_id)

        themes = await db_utils.get_available_themes()
        theme_name = themes[theme_id]
        subthemes = await db_utils.get_subthemes(theme_name)
        subtheme_name = subthemes[subtheme_id]

        await state.update_data(
            theme_id=theme_id,
            subtheme_id=subtheme_id,
            theme_name=theme_name,
            subtheme_name=subtheme_name
        )

        confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Да", callback_data="confirm_subtheme_delete"),
             InlineKeyboardButton(text="Нет", callback_data="cancel_subtheme_delete")]
        ])

        await callback.message.edit_text(
            f"⚠️Вы уверены, что хотите удалить подборку «{subtheme_name}» по теме «{theme_name}»?",
            reply_markup=confirm_keyboard
        )
        await state.set_state(AdminActions.waiting_subtheme_delete_confirmation)

    await callback.answer()
    await db_utils.db.close()


@admin_router.callback_query(
    AdminActions.waiting_subtheme_delete_confirmation,
    F.data.in_(["confirm_subtheme_delete", "cancel_subtheme_delete"])
)
async def handle_subtheme_deletion(callback: CallbackQuery, state: FSMContext):
    await db_utils.db.connect()
    data = await state.get_data()

    if callback.data == "confirm_subtheme_delete":
        success = await db_utils.delete_selection(data['theme_name'], data['subtheme_name'])
        if success:
            await callback.message.delete()
            await callback.message.answer(
                f"✅Подборка «{data['subtheme_name']}» по теме «{data['theme_name']}» успешно удалена!",
                reply_markup=main_kb(callback.from_user.id)
            )
        else:
            await callback.message.delete()
            await callback.message.answer(
                f"❌Не удалось удалить подборку «{data['subtheme_name']}» по теме «{data['theme_name']}»",
                reply_markup=main_kb(callback.from_user.id)
            )
    else:
        await callback.message.delete()
        await callback.message.answer(
            "❌Удаление подборки отменено",
            reply_markup=main_kb(callback.from_user.id)
        )

    await state.clear()
    await callback.answer()
    await db_utils.db.close()
