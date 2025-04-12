from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

from keyboards.all_keyboards import main_kb, create_spec_kb

start_router = Router()


@start_router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer('Меню',
                         reply_markup=main_kb(message.from_user.id))


@start_router.message(Command('start_2'))
async def cmd_start_2(message: Message):
    await message.answer('Меню 2',
                         reply_markup=create_spec_kb())


@start_router.message(F.text == 'привет')
async def cmd_start_3(message: Message):
    await message.answer('Привет!')