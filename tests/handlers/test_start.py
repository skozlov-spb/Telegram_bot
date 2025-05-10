import unittest
from unittest.mock import Mock, AsyncMock, patch
from aiogram import types

# Патчим psycopg2.connect до импорта
with patch('psycopg2.connect') as mock_psycopg2_connect:
    mock_psycopg2_connect.return_value = Mock()
    from handlers.start import start_router, cmd_start, cmd_start_2, cmd_start_3, expert_recommendation, process_callback

class TestStartHandlers(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.mock_message = Mock(spec=types.Message)
        self.mock_message.from_user = Mock(id=123, username="test_user")
        self.mock_callback = Mock(spec=types.CallbackQuery)
        self.mock_callback.message = Mock(spec=types.Message)
        self.mock_callback.message.edit_text = AsyncMock()
        self.mock_callback.message.answer = AsyncMock()
        self.mock_callback.answer = AsyncMock()

        self.mock_db_utils = AsyncMock()
        self.patcher_db_utils = patch('handlers.start.db_utils', self.mock_db_utils)
        self.patcher_db_utils.start()

    def tearDown(self):
        self.patcher_db_utils.stop()

    async def test_cmd_start(self):
        self.mock_message.answer = AsyncMock()
        await cmd_start(self.mock_message)  # Передаём только message
        self.mock_message.answer.assert_called_once_with('Меню', reply_markup=Mock())

    async def test_cmd_start_2(self):
        self.mock_message.answer = AsyncMock()
        await cmd_start_2(self.mock_message)
        self.mock_message.answer.assert_called_once_with('Меню 2', reply_markup=Mock())

    async def test_cmd_start_3(self):
        self.mock_message.answer = AsyncMock()
        self.mock_message.text = 'привет'
        await cmd_start_3(self.mock_message)
        self.mock_message.answer.assert_called_once_with('Привет!')

    async def test_expert_recommendation(self):
        self.mock_message.answer = AsyncMock()
        self.mock_message.text = '📚 Рекомендация экспертов'
        await expert_recommendation(self.mock_message)
        self.mock_message.answer.assert_called_once_with(
            "Нажмите ниже, чтобы выбрать тему для рекомендаций экспертов:",
            reply_markup=Mock()
        )

    async def test_process_callback_get_themes(self):
        self.mock_callback.data = "get_themes"
        self.mock_db_utils.get_available_themes.return_value = ["theme1", "theme2"]
        await process_callback(self.mock_callback)
        self.mock_db_utils.get_available_themes.assert_called_once()
        self.mock_callback.message.edit_text.assert_called_once_with("Выберите тему:", reply_markup=Mock())
        self.mock_callback.answer.assert_called_once()

    async def test_process_callback_get_themes_empty(self):
        self.mock_callback.data = "get_themes"
        self.mock_db_utils.get_available_themes.return_value = []
        await process_callback(self.mock_callback)
        self.mock_db_utils.get_available_themes.assert_called_once()
        self.mock_callback.message.answer.assert_called_once_with("Темы отсутствуют.")
        self.mock_callback.answer.assert_called_once()

    async def test_process_callback_theme(self):
        self.mock_callback.data = "theme_test"
        self.mock_db_utils.get_subthemes.return_value = ["subtheme1", "subtheme2"]
        await process_callback(self.mock_callback)
        self.mock_db_utils.get_subthemes.assert_called_once_with("test")
        self.mock_callback.message.edit_text.assert_called_once_with("Выберите подтему для test:", reply_markup=Mock())
        self.mock_callback.answer.assert_called_once()

    async def test_process_callback_theme_empty(self):
        self.mock_callback.data = "theme_test"
        self.mock_db_utils.get_subthemes.return_value = []
        await process_callback(self.mock_callback)
        self.mock_db_utils.get_subthemes.assert_called_once_with("test")
        self.mock_callback.message.answer.assert_called_once_with("Подтемы для test не найдены.")
        self.mock_callback.answer.assert_called_once()

    async def test_process_callback_subtheme(self):
        self.mock_callback.data = "subtheme_subtest"
        self.mock_db_utils.get_expert_recommendations.return_value = {
            "1": {
                "book_name": "Book1",
                "expert_name": "Expert1",
                "expert_position": "Position1",
                "description": "Desc1"
            }
        }
        await process_callback(self.mock_callback)
        self.mock_db_utils.get_expert_recommendations.assert_called_once_with("subtest")
        self.mock_callback.message.edit_text.assert_called_once()
        self.mock_callback.answer.assert_called_once()

    async def test_process_callback_subtheme_empty(self):
        self.mock_callback.data = "subtheme_subtest"
        self.mock_db_utils.get_expert_recommendations.return_value = None
        await process_callback(self.mock_callback)
        self.mock_db_utils.get_expert_recommendations.assert_called_once_with("subtest")
        self.mock_callback.message.answer.assert_called_once_with("Рекомендации для subtest не найдены.")
        self.mock_callback.answer.assert_called_once()

if __name__ == "__main__":
    unittest.main()