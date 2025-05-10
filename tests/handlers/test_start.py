import unittest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from aiogram import types
from aiogram.types import (
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    KeyboardButton,
    Message,
    CallbackQuery
)
from typing import List, Optional


class TestStartHandlers(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Создаем моки для сообщений и callback-запросов
        self.mock_message = MagicMock(spec=Message)
        self.mock_message.from_user = MagicMock(id=123, username="test_user")
        self.mock_message.answer = AsyncMock()
        self.mock_message.edit_text = AsyncMock()

        self.mock_callback = MagicMock(spec=CallbackQuery)
        self.mock_callback.message = self.mock_message
        self.mock_callback.answer = AsyncMock()
        self.mock_callback.data = ""

        # Мокируем зависимости
        self.mock_db_utils = AsyncMock()
        self.mock_main_kb = MagicMock(return_value=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="📝 Рекомендация"), KeyboardButton(text="📚 Рекомендация экспертов")]],
            resize_keyboard=True
        ))
        self.mock_themes_inline_kb = MagicMock(return_value=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="Получить темы", callback_data="get_themes")]]
        ))

        # Патчим все зависимости
        self.patches = [
            patch('handlers.start.db_utils', self.mock_db_utils),
            patch('handlers.start.main_kb', self.mock_main_kb),
            patch('handlers.start.themes_inline_kb', self.mock_themes_inline_kb),
            patch('handlers.start.bot', AsyncMock())
        ]

        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

    async def test_cmd_start(self):
        from handlers.start import cmd_start

        await cmd_start(self.mock_message)

        self.mock_main_kb.assert_called_once_with(123)
        self.mock_message.answer.assert_called_once_with(
            'Меню',
            reply_markup=self.mock_main_kb.return_value
        )

    async def test_cmd_start_3(self):
        from handlers.start import cmd_start_3

        self.mock_message.text = 'привет'
        await cmd_start_3(self.mock_message)

        self.mock_message.answer.assert_called_once_with('Привет!')

    async def test_expert_recommendation(self):
        from handlers.start import expert_recommendation

        self.mock_message.text = '📚 Рекомендация экспертов'
        await expert_recommendation(self.mock_message)

        self.mock_themes_inline_kb.assert_called_once()
        self.mock_message.answer.assert_called_once_with(
            "Нажмите ниже, чтобы выбрать тему для рекомендаций экспертов:",
            reply_markup=self.mock_themes_inline_kb.return_value
        )

    async def test_process_callback_get_themes(self):
        from handlers.start import process_callback

        self.mock_callback.data = "get_themes"
        self.mock_db_utils.get_available_themes.return_value = ["theme1", "theme2"]

        await process_callback(self.mock_callback)

        self.mock_db_utils.get_available_themes.assert_called_once()
        self.mock_message.edit_text.assert_called_once()
        self.mock_callback.answer.assert_called_once()

    async def test_process_callback_theme(self):
        from handlers.start import process_callback

        self.mock_callback.data = "theme_test"
        self.mock_db_utils.get_subthemes.return_value = ["sub1", "sub2"]

        await process_callback(self.mock_callback)

        self.mock_db_utils.get_subthemes.assert_called_once_with("test")
        self.mock_message.edit_text.assert_called_once()
        self.mock_callback.answer.assert_called_once()

    async def test_process_callback_subtheme(self):
        from handlers.start import process_callback

        self.mock_callback.data = "subtheme_test"
        self.mock_db_utils.get_expert_recommendations.return_value = {
            "1": {
                "book_name": "Book",
                "expert_name": "Expert",
                "expert_position": "Position",
                "description": "Desc"
            }
        }

        await process_callback(self.mock_callback)

        self.mock_db_utils.get_expert_recommendations.assert_called_once_with("test")
        self.mock_message.edit_text.assert_called_once()
        self.mock_callback.answer.assert_called_once()

    async def test_process_callback_empty_themes(self):
        from handlers.start import process_callback

        self.mock_callback.data = "get_themes"
        self.mock_db_utils.get_available_themes.return_value = []

        await process_callback(self.mock_callback)

        self.mock_message.answer.assert_called_once_with("Темы отсутствуют.")
        self.mock_callback.answer.assert_called_once()

    async def test_process_callback_empty_subthemes(self):
        from handlers.start import process_callback

        self.mock_callback.data = "theme_test"
        self.mock_db_utils.get_subthemes.return_value = []

        await process_callback(self.mock_callback)

        self.mock_message.answer.assert_called_once_with("Подтемы для test не найдены.")
        self.mock_callback.answer.assert_called_once()

    async def test_process_callback_empty_recommendations(self):
        from handlers.start import process_callback

        self.mock_callback.data = "subtheme_test"
        self.mock_db_utils.get_expert_recommendations.return_value = None

        await process_callback(self.mock_callback)

        self.mock_message.answer.assert_called_once_with("Рекомендации для test не найдены.")
        self.mock_callback.answer.assert_called_once()


if __name__ == "__main__":
    unittest.main()