from aiogram.fsm.state import State, StatesGroup


class AdminActions(StatesGroup):
    waiting_for_file = State()
    waiting_book_name = State()
    waiting_broadcast_message = State()
    waiting_broadcast_confirmation = State()
    waiting_book_delete_confirmation = State()
    waiting_subtheme_delete_confirmation = State()
    waiting_expert_delete_confirmation = State()
    waiting_new_admin_id = State()
