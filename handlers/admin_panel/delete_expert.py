from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from keyboards.all_keyboards import main_kb
from db_handler.db_utils import DBUtils
from db_handler.db_class import Database
import create_bot
from create_bot import bot
from handlers.admin_panel.states import AdminActions

admin_router = Router()
db_utils = DBUtils(db=Database(), bot=bot)


@admin_router.callback_query(
    F.data.in_(['admin_select_expert']) | F.data.regexp(r'^(admin_experts_page|admin_delete_expert)_')
)
async def process_expert_selection(callback: CallbackQuery, state: FSMContext):
    await db_utils.db.connect()
    user_id = callback.from_user.id

    if user_id not in create_bot.admins:
        await callback.message.answer("У вас нет доступа к админ-панели.", reply_markup=main_kb(user_id))
        await callback.answer()
        await db_utils.db.close()
        return

    action = callback.data

    if action == "admin_select_expert" or action.startswith("admin_experts_page_"):
        if action == "admin_select_expert":
            page = 0
        else:
            page = int(action.split("_")[-1])
        items_per_page = 5

        experts = await db_utils.get_available_experts()
        if not experts:
            await callback.message.answer("⚠️*Эксперты отсутствуют.*", reply_markup=main_kb(user_id),
                                          parse_mode="Markdown")
            await callback.answer()
            await db_utils.db.close()
            return

        total_pages = (len(experts) + items_per_page - 1) // items_per_page
        start_idx = page * items_per_page
        end_idx = min(start_idx + items_per_page, len(experts))
        current_experts = experts[start_idx:end_idx]

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"👤{expert[0]} — {expert[1][0].lower() + expert[1][1:]}",
                                  callback_data=f"admin_delete_expert_{current_experts.index(expert) + start_idx}")]
            for expert in current_experts
        ])

        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(text="◄ Назад", callback_data=f"admin_experts_page_{page - 1}"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton(text="Вперёд ►", callback_data=f"admin_experts_page_{page + 1}"))
        if nav_buttons:
            keyboard.inline_keyboard.append(nav_buttons)
        keyboard.inline_keyboard.append(
            [InlineKeyboardButton(text=f"📄Страница {page + 1} из {total_pages}", callback_data=f"admin_page_{page}")]
        )
        keyboard.inline_keyboard.append(
            [InlineKeyboardButton(text="◄ Назад в админ-панель", callback_data="admin_back_to_panel")]
        )

        await callback.message.edit_text("**Выберите эксперта для удаления** 👤\n*Доступные эксперты:*",
                                         reply_markup=keyboard, parse_mode="Markdown")

    elif action.startswith("admin_delete_expert_"):
        expert_id = int(action[len("admin_delete_expert_"):])
        experts = await db_utils.get_available_experts()
        expert_name, expert_position = experts[expert_id]

        await state.update_data(
            expert_id=expert_id,
            expert_name=expert_name,
            expert_position=expert_position
        )

        confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Да", callback_data="confirm_expert_delete"),
             InlineKeyboardButton(text="Нет", callback_data="cancel_expert_delete")]
        ])

        await callback.message.edit_text(
            f"⚠️Вы уверены, что хотите удалить эксперта?\n{expert_name} — {expert_position[0].lower() + expert_position[1:]}",
            reply_markup=confirm_keyboard
        )
        await state.set_state(AdminActions.waiting_expert_delete_confirmation)

    await callback.answer()
    await db_utils.db.close()


@admin_router.callback_query(
    AdminActions.waiting_expert_delete_confirmation,
    F.data.in_(["confirm_expert_delete", "cancel_expert_delete"])
)
async def handle_expert_deletion(callback: CallbackQuery, state: FSMContext):
    await db_utils.db.connect()
    data = await state.get_data()

    if callback.data == "confirm_expert_delete":
        success = await db_utils.delete_expert(data['expert_name'], data['expert_position'])
        if success:
            await callback.message.delete()
            await callback.message.answer(
                f"✅Эксперт {data['expert_name']} — {data['expert_position'][0].lower() + data['expert_position'][1:]} успешно удален!",
                reply_markup=main_kb(callback.from_user.id)
            )
        else:
            await callback.message.delete()
            await callback.message.answer(
                f"❌Не удалось удалить эксперта {data['expert_name']} — {data['expert_position'][0].lower() + data['expert_position'][1:]}",
                reply_markup=main_kb(callback.from_user.id)
            )
    else:
        await callback.message.delete()
        await callback.message.answer(
            "❌Удаление эксперта отменено",
            reply_markup=main_kb(callback.from_user.id)
        )

    await state.clear()
    await callback.answer()
    await db_utils.db.close()
