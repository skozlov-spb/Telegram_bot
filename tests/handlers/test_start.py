import pytest
from unittest.mock import AsyncMock, MagicMock, patch, ANY
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext


@pytest.fixture
def mock_db():
    mock = AsyncMock()
    mock.connect = AsyncMock()
    mock.close = AsyncMock()
    return mock


@pytest.fixture
def mock_db_utils(mock_db):
    mock = AsyncMock()
    mock.db = mock_db
    mock.register_user = AsyncMock(return_value=True)
    mock.get_statistic = AsyncMock(return_value={
        "total_users": 100,
        "inactive_percent": 20.0,
        "subscribed_users": 80
    })
    mock.recommend = AsyncMock(return_value=[{
        "theme_name": "Theme1",
        "specific_theme": "Sub1",
        "experts": [{
            "expert_name": "Expert1",
            "expert_position": "Pos1",
            "book_name": "Book1",
            "description": "Desc1"
        }]
    }])
    mock.get_available_themes = AsyncMock(return_value=["Theme1", "Theme2"])
    mock.get_subthemes = AsyncMock(return_value=["Subtheme1"])
    mock.get_expert_recommendations = AsyncMock(return_value={
        "expert1": {
            "name": "Expert1",
            "position": "Position1",
            "books": [("Book1", "Description1")]
        }
    })
    mock.is_subscribed = AsyncMock(return_value=False)
    mock.log_user_activity = AsyncMock()
    mock.get_subscribed_users = AsyncMock(return_value=[123, 456])
    mock.delete_selection = AsyncMock(return_value=True)
    mock.get_theme_id = AsyncMock(return_value=1)
    return mock


@pytest.fixture
def mock_rec_sys():
    mock = AsyncMock()
    mock.recommend = AsyncMock(return_value=[{
        "theme_name": "Theme1",
        "specific_theme": "Sub1",
        "experts": [{
            "expert_name": "Expert1",
            "expert_position": "Pos1",
            "book_name": "Book1",
            "description": "Desc1"
        }]
    }])
    return mock


@pytest.fixture
def mock_objects(mock_db_utils, mock_rec_sys):
    mock_message = AsyncMock(spec=Message)
    mock_message.from_user = MagicMock(id=123, username="testuser")
    mock_message.text = ""
    mock_message.answer = AsyncMock()
    mock_message.delete = AsyncMock()
    mock_message.edit_text = AsyncMock(return_value=True)

    mock_callback = AsyncMock(spec=CallbackQuery)
    mock_callback.from_user = MagicMock(id=123)
    mock_callback.message = mock_message
    mock_callback.data = ""
    mock_callback.answer = AsyncMock()

    return {
        "message": mock_message,
        "callback": mock_callback,
        "db_utils": mock_db_utils,
        "rec_sys": mock_rec_sys,
        "db": mock_db_utils.db
    }


@pytest.mark.asyncio
class TestStartHandlers:
    async def test_cmd_start_new_user(self, mock_objects):
        with patch('handlers.start.db_utils', mock_objects["db_utils"]), \
                patch('handlers.start.main_kb', MagicMock()):
            from handlers.start import cmd_start
            await cmd_start(mock_objects["message"])

            mock_objects["db_utils"].register_user.assert_awaited_once_with(123, "testuser")
            mock_objects["message"].answer.assert_awaited_once()

    async def test_cmd_recc_success(self, mock_objects):
        with patch('handlers.start.db_utils', mock_objects["db_utils"]), \
                patch('handlers.start.rec_sys', mock_objects["rec_sys"]), \
                patch('handlers.start.main_kb', MagicMock()):
            from handlers.start import cmd_recc
            await cmd_recc(mock_objects["message"])

            mock_objects["rec_sys"].recommend.assert_awaited_once_with(123)
            mock_objects["message"].answer.assert_awaited()

    async def test_cmd_recc_no_recommendations(self, mock_objects):
        mock_objects["rec_sys"].recommend.return_value = []
        with patch('handlers.start.db_utils', mock_objects["db_utils"]), \
                patch('handlers.start.rec_sys', mock_objects["rec_sys"]), \
                patch('handlers.start.main_kb', MagicMock()):
            from handlers.start import cmd_recc
            await cmd_recc(mock_objects["message"])

            mock_objects["message"].answer.assert_awaited_with(
                '**Рекомендации пока недоступны.**',
                reply_markup=ANY,
                parse_mode="Markdown"
            )


    async def test_process_subscription_callback_subscribe(self, mock_objects):
        mock_objects["callback"].data = "subscribe"
        with patch('handlers.start.db_utils', mock_objects["db_utils"]), \
                patch('handlers.start.main_kb', MagicMock()), \
                patch('handlers.start.bot', AsyncMock()), \
                patch('aiogram.exceptions.TelegramBadRequest', Exception):
            from handlers.start import process_subscription_callback
            await process_subscription_callback(mock_objects["callback"])

            mock_objects["db_utils"].log_user_activity.assert_awaited_once_with(
                user_id=123,
                activity_type="subscribe",
                theme_id=None
            )

    async def test_process_callback_back_to_main(self, mock_objects):
        mock_objects["callback"].data = "back_to_main"
        with patch('handlers.start.db_utils', mock_objects["db_utils"]), \
                patch('handlers.start.main_kb', MagicMock()):
            from handlers.start import process_callback_expert_rec
            await process_callback_expert_rec(mock_objects["callback"])

            mock_objects["callback"].message.delete.assert_awaited_once()
            mock_objects["callback"].message.answer.assert_awaited_once()
