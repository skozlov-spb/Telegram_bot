import unittest
import asyncio
from unittest.mock import patch, AsyncMock
from unittest import IsolatedAsyncioTestCase
from aiogram.types import BotCommand, KeyboardButton


class TestAllKeyboards(IsolatedAsyncioTestCase):
    def setUp(self):
        self.bot_patch = patch('keyboards.all_keyboards.bot', new_callable=AsyncMock)
        self.mock_bot = self.bot_patch.start()
        self.addCleanup(self.bot_patch.stop)

    async def test_set_commands_success(self):
        from keyboards.all_keyboards import set_commands

        await set_commands()

        self.mock_bot.set_my_commands.assert_awaited_once()

        args, _ = self.mock_bot.set_my_commands.call_args
        commands = args[0]
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0].command, 'start')
        self.assertEqual(commands[0].description, 'Старт')

    def test_main_kb_structure(self):
        from keyboards.all_keyboards import main_kb

        keyboard = main_kb(123)

        self.assertEqual(len(keyboard.keyboard), 1)
        self.assertEqual(len(keyboard.keyboard[0]), 2)

        self.assertEqual(keyboard.keyboard[0][0].text, "📚 Просмотреть подборки от экспертов")
        self.assertEqual(keyboard.keyboard[0][1].text, "📝 Получить рекомендации")

    def test_admin_kb_structure(self):
        """Тестируем клавиатуру для администратора"""
        from keyboards.all_keyboards import main_kb

        with patch('keyboards.all_keyboards.admins', [123]):
            keyboard = main_kb(123)

            self.assertEqual(len(keyboard.keyboard), 2)
            self.assertEqual(len(keyboard.keyboard[1]), 1)
            self.assertEqual(keyboard.keyboard[1][0].text, "⚙️ Админ панель")

    def test_themes_inline_kb_structure(self):
        """Тестируем структуру инлайн-клавиатуры для тем"""
        from keyboards.all_keyboards import themes_inline_kb

        keyboard = themes_inline_kb()

        self.assertEqual(len(keyboard.inline_keyboard), 1)  # Одна строка
        self.assertEqual(len(keyboard.inline_keyboard[0]), 1)  # Одна кнопка

        button = keyboard.inline_keyboard[0][0]
        self.assertEqual(button.text, "Получить темы")
        self.assertEqual(button.callback_data, "get_themes")

    def test_keyboard_properties(self):
        """Тестируем свойства клавиатур"""
        from keyboards.all_keyboards import main_kb

        keyboard = main_kb(123)

        self.assertTrue(keyboard.resize_keyboard)
        self.assertTrue(keyboard.one_time_keyboard)
        self.assertEqual(keyboard.input_field_placeholder, "Воспользуйтесь меню:")


if __name__ == "__main__":
    unittest.main()
