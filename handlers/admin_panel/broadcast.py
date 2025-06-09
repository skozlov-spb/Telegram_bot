import asyncio
from aiogram import F, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from keyboards.all_keyboards import main_kb, admin_panel_kb
from db_handler.db_utils import DBUtils
from db_handler.db_class import Database
import create_bot
from create_bot import bot
from handlers.admin_panel.states import AdminActions

admin_router = Router()
db_utils = DBUtils(db=Database(), bot=bot)


@admin_router.callback_query(F.data == "admin_broadcast")
async def start_broadcast(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await state.set_state(AdminActions.waiting_broadcast_message)
    await callback.message.answer("Введите сообщение для рассылки:")
    await callback.answer()


@admin_router.message(
    AdminActions.waiting_broadcast_message,
    F.from_user.id.in_(create_bot.admins),
    F.content_type.in_({'text', 'photo'})
)
async def process_broadcast_message(message: Message, state: FSMContext):
    await db_utils.db.connect()
    try:
        subscribers = await db_utils.get_subscribed_users()

        if not subscribers:
            await message.answer("❌Нет активных подписчиков для рассылки", reply_markup=admin_panel_kb())
            await state.clear()
            await db_utils.db.close()
            return

        content_data = {}
        if message.photo:
            content_data['photo_id'] = message.photo[-1].file_id
            content_data['caption'] = message.caption if message.caption else ""
            content_type = 'photo'
        else:
            content_data['text'] = message.text
            content_type = 'text'

        await state.update_data(
            content_type=content_type,
            content_data=content_data,
            subscribers_count=len(subscribers)
        )

        confirm_text = (
            "✉️Подтвердите рассылку:\n"
            f"Получателей: {len(subscribers)}\n"
            f"Тип: {'Фото с текстом' if content_type == 'photo' else 'Текст'}\n"
        )

        if content_type == 'photo':
            confirm_text += f"Текст к фото: {content_data['caption']}\n" if content_data['caption'] else ""
            await message.answer_photo(
                photo=content_data['photo_id'],
                caption=confirm_text.strip(),
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Подтвердить", callback_data="confirm_broadcast"),
                     InlineKeyboardButton(text="Отменить", callback_data="cancel_broadcast")]
                ])
            )
        else:
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
        await message.answer(f"⚠️Ошибка при подготовке рассылки: {str(e)}", reply_markup=admin_panel_kb())
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
        await callback.message.delete()
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
                f"📬Рассылка завершена:\n"
                f"Всего получателей: {data['subscribers_count']}\n"
                f"Успешно отправлено: {success_count}\n"
                f"Не удалось отправить: {data['subscribers_count'] - success_count}"
            )

            await callback.message.answer(report, reply_markup=main_kb(callback.from_user.id))

        else:
            await callback.message.answer("❌Рассылка отменена", reply_markup=main_kb(callback.from_user.id))

    except Exception as e:
        await callback.message.answer(f"⚠️Произошла ошибка при рассылке: {str(e)}",
                                      reply_markup=main_kb(callback.from_user.id))

    finally:
        await state.clear()
        await callback.answer()
        await db_utils.db.close()
