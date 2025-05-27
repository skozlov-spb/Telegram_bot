import os
import asyncio
from aiogram import F, Router
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.chat_action import ChatActionSender
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from create_bot import bot, admins
from keyboards.all_keyboards import admin_panel_kb, admin_delete_menu_kb
from db_handler.db_utils import DBUtils, get_admin_ids
from db_handler.db_class import Database
from keyboards.all_keyboards import main_kb

db_utils = DBUtils(db=Database(), bot=bot)

admin_router = Router()

DATA_DIR = "data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)


class AdminActions(StatesGroup):
    waiting_for_file = State()
    waiting_book_name = State()
    waiting_broadcast_message = State()
    waiting_broadcast_confirmation = State()
    waiting_book_delete_confirmation = State()
    waiting_subtheme_delete_confirmation = State()
    waiting_expert_delete_confirmation = State()
    waiting_new_admin_id = State()


@admin_router.message((F.text.endswith("Админ панель")) & (F.from_user.id.in_(admins)))
async def admin_panel(message: Message):
    await message.answer(
        "**Выберите действие в админ-панели**:",
        reply_markup=admin_panel_kb(),
        parse_mode="Markdown"
    )


@admin_router.callback_query(F.data == "admin_delete_menu")
async def show_delete_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "Выберите что хотите удалить:",
        reply_markup=admin_delete_menu_kb()
    )
    await callback.answer()


@admin_router.callback_query(F.data.in_(
    ['admin_get_stats', 'admin_upload_data', 'admin_delete_book']))
async def process_admin_callback(callback: CallbackQuery, state: FSMContext):
    await db_utils.db.connect()
    action = callback.data
    user_id = callback.from_user.id

    if user_id not in admins:
        await callback.message.answer("У вас нет доступа к админ-панели.")
        await callback.answer()
        return

    if action == "admin_get_stats":
        stats = await db_utils.get_statistic()
        response = (
            f"📊 **Статистика**:\n"
            f"Всего пользователей: {stats['total_users']}\n"
            f"Неактивные пользователи: {stats['inactive_percent']}%\n"
            # f"Подписанные на рассылку: {stats['subscribed_users']}"
        )
        await callback.message.answer(response, parse_mode="Markdown", reply_markup=main_kb(user_id))

    elif action == "admin_upload_data":
        await state.set_state(AdminActions.waiting_for_file)
        await callback.message.answer(
            "📤 Пожалуйста, отправьте Excel-файл с данными.",
            parse_mode="Markdown"
        )

    elif action == "admin_delete_book":
        await state.set_state(AdminActions.waiting_book_name)
        await callback.message.answer("📝 Введите название книги для удаления:")

    await callback.answer()
    await db_utils.db.close()


@admin_router.callback_query(F.data.in_(['admin_select_theme', 'admin_back_to_panel']) |
                            F.data.regexp(r'^(admin_themes_page|admin_theme|admin_subthemes|admin_delete_subtheme)_'))
async def process_theme_selection(callback: CallbackQuery, state: FSMContext):
    await db_utils.db.connect()
    user_id = callback.from_user.id

    if user_id not in admins:
        await callback.message.answer("У вас нет доступа к админ-панели.", reply_markup=main_kb(user_id))
        await callback.answer()
        await db_utils.db.close()
        return

    action = callback.data

    if action == "admin_back_to_panel":
        await callback.message.edit_text(
            "**Выберите действие в админ-панели**:",
            reply_markup=admin_panel_kb(),
            parse_mode="Markdown"
        )

    elif action == "admin_select_theme" or action.startswith("admin_themes_page_"):
        if action == "admin_select_theme":
            page = 0
        else:
            page = int(action.split("_")[-1])
        items_per_page = 5

        themes = await db_utils.get_available_themes()
        if not themes:
            await callback.message.answer("⚠️ *Темы отсутствуют.*", parse_mode="Markdown")
            await callback.answer()
            await db_utils.db.close()
            return

        total_pages = (len(themes) + items_per_page - 1) // items_per_page
        start_idx = page * items_per_page
        end_idx = min(start_idx + items_per_page, len(themes))
        current_themes = themes[start_idx:end_idx]

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"📖 {theme}",
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
            [InlineKeyboardButton(text=f"📄 Страница {page + 1} из {total_pages}", callback_data=f"admin_page_{page}")]
        )
        keyboard.inline_keyboard.append(
            [InlineKeyboardButton(text="◄ Назад в админ-панель", callback_data="admin_back_to_panel")]
        )

        await callback.message.edit_text("**Выберите тему для удаления** 📚\n*Доступные категории:*",
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
            await callback.message.answer(f"⚠️ *Подтемы для __{theme_name}__ не найдены.*", parse_mode="Markdown")
            await callback.answer()
            await db_utils.db.close()
            return

        total_pages = (len(subthemes) + items_per_page - 1) // items_per_page
        start_idx = page * items_per_page
        end_idx = min(start_idx + items_per_page, len(subthemes))
        current_subthemes = subthemes[start_idx:end_idx]

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"📋 {subtheme}",
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
            [InlineKeyboardButton(text=f"📄 Страница {page + 1} из {total_pages}", callback_data=f"admin_page_{page}")]
        )
        keyboard.inline_keyboard.append(
            [InlineKeyboardButton(text="◄ Назад к темам", callback_data=f"admin_select_theme")]
        )

        await callback.message.edit_text(f"**Подтемы для __{theme_name}__** 📋\n*Выберите подтему для удаления:*",
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
            f"⚠️ Вы уверены, что хотите удалить подборку «_{theme_name}/{subtheme_name}_»?",
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
                f"✅ Подборка «{data['theme_name']}/{data['subtheme_name']}» успешно удалена!",
                reply_markup=main_kb(callback.from_user.id)
            )
        else:
            await callback.message.delete()
            await callback.message.answer(
                f"❌ Не удалось удалить подборку «{data['theme_name']}/{data['subtheme_name']}»",
                reply_markup=main_kb(callback.from_user.id)
            )
    else:
        await callback.message.delete()
        await callback.message.answer(
            "❌ Удаление подборки отменено",
            reply_markup=main_kb(callback.from_user.id)
        )
    
    await state.clear()
    await callback.answer()
    await db_utils.db.close()


@admin_router.callback_query(F.data.in_(['admin_select_expert', 'admin_back_to_panel']) |
                             F.data.regexp(r'^(admin_experts_page|admin_delete_expert)_'))
async def process_expert_selection(callback: CallbackQuery, state: FSMContext):
    await db_utils.db.connect()
    user_id = callback.from_user.id

    if user_id not in admins:
        await callback.message.answer("У вас нет доступа к админ-панели.", reply_markup=main_kb(user_id))
        await callback.answer()
        await db_utils.db.close()
        return

    action = callback.data

    if action == "admin_back_to_panel":
        await callback.message.edit_text(
            "**Выберите действие в админ-панели**:",
            reply_markup=admin_panel_kb(),
            parse_mode="Markdown"
        )

    elif action == "admin_select_expert" or action.startswith("admin_experts_page_"):
        if action == "admin_select_expert":
            page = 0
        else:
            page = int(action.split("_")[-1])
        items_per_page = 5

        experts = await db_utils.get_available_experts()
        if not experts:
            await callback.message.answer("⚠️ *Эксперты отсутствуют.*", parse_mode="Markdown")
            await callback.answer()
            await db_utils.db.close()
            return

        total_pages = (len(experts) + items_per_page - 1) // items_per_page
        start_idx = page * items_per_page
        end_idx = min(start_idx + items_per_page, len(experts))
        current_experts = experts[start_idx:end_idx]

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"👤 {expert[0]} — {expert[1][0].lower() + expert[1][1:]}",
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
            [InlineKeyboardButton(text=f"📄 Страница {page + 1} из {total_pages}", callback_data=f"admin_page_{page}")]
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
            [InlineKeyboardButton(text="✅ Да", callback_data="confirm_expert_delete"),
             InlineKeyboardButton(text="❌ Нет", callback_data="cancel_expert_delete")]
        ])
        
        await callback.message.edit_text(
            f"⚠️ Вы уверены, что хотите удалить эксперта?\n{expert_name} ({expert_position})",
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
                f"✅ Эксперт '{data['expert_name']} ({data['expert_position']})' успешно удален!",
                reply_markup=main_kb(callback.from_user.id)
            )
        else:
            await callback.message.delete()
            await callback.message.answer(
                f"❌ Не удалось удалить эксперта '{data['expert_name']} ({data['expert_position']})'",
                reply_markup=main_kb(callback.from_user.id)
            )
    else:
        await callback.message.delete()
        await callback.message.answer(
            "❌ Удаление эксперта отменено",
            reply_markup=main_kb(callback.from_user.id)
        )
    
    await state.clear()
    await callback.answer()
    await db_utils.db.close()


@admin_router.message(AdminActions.waiting_for_file, F.document, F.from_user.id.in_(admins))
async def process_uploaded_file(message: Message, state: FSMContext):
    await db_utils.db.connect()
    document = message.document
    if not document.file_name.endswith(('.xlsx', '.xls')):
        await message.answer("❌ Пожалуйста, отправьте файл в формате Excel (.xlsx или .xls).", reply_markup=main_kb(message.from_user.id))
        await state.clear()
        return

    try:
        async with ChatActionSender.upload_document(bot=bot, chat_id=message.chat.id):
            file_path = os.path.join(DATA_DIR, document.file_name)
            file = await bot.get_file(document.file_id)
            await bot.download_file(file.file_path, file_path)

            success = await db_utils.upload_data(file_path)

            if success:
                await message.answer(f"✅ Данные из файла {document.file_name} успешно загружены!", reply_markup=main_kb(message.from_user.id))
                os.remove(file_path)
            else:
                await message.answer(f"❌ Ошибка при загрузке данных из файла {document.file_name}", reply_markup=main_kb(message.from_user.id))

            await state.clear()

    except Exception as exc:
        await message.answer(f"❌ Ошибка при обработке файла: {str(exc)}", reply_markup=main_kb(message.from_user.id))
        await state.clear()
    await db_utils.db.close()


@admin_router.message(AdminActions.waiting_book_name, F.from_user.id.in_(admins))
async def process_book_name(message: Message, state: FSMContext):
    await state.update_data(book_name=message.text)
    
    confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да", callback_data="confirm_delete"),
            InlineKeyboardButton(text="❌ Нет", callback_data="cancel_delete")
        ]
    ])
    
    await message.answer(
        f"⚠️ Вы уверены, что хотите удалить книгу?\nНазвание: {message.text}",
        reply_markup=confirm_keyboard
    )
    await state.set_state(AdminActions.waiting_book_delete_confirmation)
    
    
@admin_router.callback_query(
    AdminActions.waiting_book_delete_confirmation,
    F.data.in_(["confirm_delete", "cancel_delete"])
)
async def handle_delete_confirmation(callback: CallbackQuery, state: FSMContext):
    await db_utils.db.connect()
    try:
        data = await state.get_data()
        
        if callback.data == "confirm_delete":
            book_name = data['book_name']
            success = await db_utils.delete_book(book_name)
            
            if success:
                await callback.message.answer(
                    f"✅ Книга '{book_name}' успешно удалена!",
                    reply_markup=admin_panel_kb()
                )
            else:
                await callback.message.answer(
                    f"❌ Не удалось удалить книгу '{book_name}'",
                    reply_markup=admin_panel_kb()
                )
        else:
            await callback.message.answer(
                "❌ Удаление отменено",
                reply_markup=admin_panel_kb()
            )
            
    except Exception as e:
        await callback.message.answer("⚠️ Произошла ошибка при удалении", reply_markup=admin_panel_kb())
    
    await state.clear()
    await callback.answer()
    await db_utils.db.close()


@admin_router.message(AdminActions.waiting_for_file)
async def invalid_file_type(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Пожалуйста, отправьте файл в формате Excel (.xlsx или .xls).", reply_markup=main_kb(message.from_user.id))


# @admin_router.callback_query(F.data == "admin_broadcast")
# async def start_broadcast(callback: CallbackQuery, state: FSMContext):
#     await state.set_state(AdminActions.waiting_broadcast_message)
#     await callback.message.answer("Введите сообщение для рассылки:")
#     await callback.answer()


@admin_router.callback_query(F.data == "admin_back_to_menu")
async def back_to_main_menu(callback: CallbackQuery):
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
    
    await callback.message.answer(
        "Главное меню:",
        reply_markup=main_kb(callback.from_user.id)
    )
    await callback.answer()
    

@admin_router.message(
    AdminActions.waiting_broadcast_message,
    F.from_user.id.in_(admins),
    F.content_type.in_({'text', 'photo'})  # Принимаем текст и фото
)
async def process_broadcast_message(message: Message, state: FSMContext):
    await db_utils.db.connect()
    try:
        subscribers = await db_utils.get_subscribed_users()
        
        if not subscribers:
            await message.answer("❌ Нет активных подписчиков для рассылки", reply_markup=admin_panel_kb())
            await state.clear()
            return

        content_data = {}
        if message.photo:
            # Сохраняем фото и подпись (если есть)
            content_data['photo_id'] = message.photo[-1].file_id
            content_data['caption'] = message.caption if message.caption else ""
            content_type = 'photo'
        else:
            # Сохраняем только текст
            content_data['text'] = message.text
            content_type = 'text'

        await state.update_data(
            content_type=content_type,
            content_data=content_data,
            subscribers_count=len(subscribers)
        )  # Исправлено: добавлена закрывающая скобка

        # Формируем сообщение для подтверждения
        confirm_text = (
            "✉️ Подтвердите рассылку:\n"
            f"Получателей: {len(subscribers)}\n"
            f"Тип: {'Фото с текстом' if content_type == 'photo' else 'Текст'}\n"
        )

        if content_type == 'photo':
            # Добавляем подпись к фото в превью
            confirm_text += f"Текст к фото: {content_data['caption']}\n" if content_data['caption'] else ""
            
            # Отправляем превью с фото
            await message.answer_photo(
                photo=content_data['photo_id'],
                caption=confirm_text.strip(),
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Подтвердить", callback_data="confirm_broadcast"),
                     InlineKeyboardButton(text="Отменить", callback_data="cancel_broadcast")]
                ])
            )
        else:
            # Добавляем текст сообщения в превью
            confirm_text += f"\nТекст сообщения:\n{content_data['text']}"
            await message.answer(
                confirm_text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Подтвердить", callback_data="confirm_broadcast"),
                     InlineKeyboardButton(text="Отменить", callback_data="cancel_broadcast")]
                ])
            )

        await state.set_state(AdminActions.waiting_broadcast_confirmation)

    except Exception as e:
        await message.answer(f"⚠️ Ошибка при подготовке рассылки: {str(e)}", reply_markup=admin_panel_kb())
        await state.clear()
    
    finally:
        await db_utils.db.close()


@admin_router.callback_query(
    AdminActions.waiting_broadcast_confirmation,
    F.data.in_(["confirm_broadcast", "cancel_broadcast"])
)
async def handle_broadcast_confirmation(callback: CallbackQuery, state: FSMContext):
    await db_utils.db.connect()
    try:
        data = await state.get_data()
        
        if callback.data == "confirm_broadcast":
            subscribers = await db_utils.get_subscribed_users()
            success_count = 0
            
            for user_id in subscribers:
                try:
                    if data['content_type'] == 'photo':
                        await bot.send_photo(
                            chat_id=user_id,
                            photo=data['content_data']['photo_id'],
                            caption=data['content_data']['caption'] if data['content_data']['caption'] else None
                        )
                    else:
                        await bot.send_message(
                            chat_id=user_id,
                            text=data['content_data']['text']
                        )
                    success_count += 1
                    await asyncio.sleep(0.1)  
                except Exception as e:
                    print(f"Ошибка отправки пользователю {user_id}: {str(e)}")
            
            report = (
                f"📬 Рассылка завершена:\n"
                f"Всего получателей: {data['subscribers_count']}\n"
                f"Успешно отправлено: {success_count}\n"
                f"Не удалось отправить: {data['subscribers_count'] - success_count}"
            )
            
            await callback.message.answer(report, reply_markup=admin_panel_kb())
            
        else:
            await callback.message.answer("❌ Рассылка отменена", reply_markup=admin_panel_kb())

    except Exception as e:
        await callback.message.answer(f"⚠️ Произошла ошибка при рассылке: {str(e)}", reply_markup=admin_panel_kb())
    
    finally:
        await state.clear()
        await callback.answer()
        await db_utils.db.close()


@admin_router.callback_query(F.data == "admin_add_admin")
async def add_admin_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminActions.waiting_new_admin_id)
    await callback.message.answer(
        "Введите ID пользователя, которого хотите сделать администратором(узнать его можно тут: @getmyid_bot):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel_add")]
        ])
    )
    await callback.answer()


@admin_router.callback_query(F.data == "admin_cancel_add")
async def cancel_add_admin(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Добавление администратора отменено")
    await callback.message.answer(
        "Админ-панель:",
        reply_markup=admin_panel_kb()
    )
    await callback.answer()


@admin_router.message(AdminActions.waiting_new_admin_id, F.text)
async def process_admin_id(message: Message, state: FSMContext):
    try:
        new_admin_id = int(message.text)
        
        # Проверяем существует ли пользователь
        try:
            user = await bot.get_chat(new_admin_id)
        except Exception:
            await message.answer("❌ Пользователь с таким ID не найден")
            return

        # Добавляем в список админов
        if new_admin_id not in admins:
            await db_utils.db.connect()

            await db_utils.assign_admin_role(new_admin_id)

            await db_utils.db.close()
            admins.append(new_admin_id)
            # Здесь можно добавить сохранение в БД
            await message.answer(f"✅ Пользователь {user.full_name} (@{user.username}) добавлен в администраторы")
        else:
            await message.answer("⚠️ Этот пользователь уже является администратором")

        await state.clear()
        await message.answer(
            "Админ-панель:",
            reply_markup=admin_panel_kb()
        )

    except ValueError:
        await message.answer("❌ Неверный формат ID. Введите числовой идентификатор")
