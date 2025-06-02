import pytest
import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, User, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest
from decouple import config

from handlers.start import (
    start_router,
    cmd_start,
    check_subscription_callback,
    cmd_recc,
    process_subscription_callback,
    display_themes,
    display_subthemes,
    display_expert,
    process_callback_expert_rec,
    db_utils,
    rec_sys,
)


@patch("decouple.config")
def mock_config(mock_config):
    mock_config.side_effect = lambda key: {
        "CHANNEL_SPBU_LINK": "https://t.me/spbu_channel",
        "CHANNEL_LANDAU_LINK": "https://t.me/landau_channel",
    }.get(key, "")


@pytest.fixture
def mock_message():
    message = MagicMock(spec=Message)
    message.from_user = MagicMock(spec=User)
    message.from_user.id = 12345
    message.from_user.username = "test_user"
    message.from_user.full_name = "Test User"
    message.answer = AsyncMock()
    message.text = ""
    return message


@pytest.fixture
def mock_callback():
    callback = MagicMock(spec=CallbackQuery)
    callback.from_user = MagicMock(spec=User)
    callback.from_user.id = 12345
    callback.message = MagicMock(spec=Message)
    callback.message.answer = AsyncMock()
    callback.message.edit_text = AsyncMock()
    callback.message.delete = AsyncMock()
    callback.answer = AsyncMock()
    callback.data = ""
    return callback


@pytest.fixture
def mock_db_utils():
    db_utils_mock = MagicMock()
    db_utils_mock.db.connect = AsyncMock()
    db_utils_mock.db.close = AsyncMock()
    db_utils_mock.register_user = AsyncMock(return_value=True)
    db_utils_mock.is_user_channel_member = AsyncMock(return_value=True)
    db_utils_mock.log_user_activity = AsyncMock()
    db_utils_mock.get_available_themes = AsyncMock(return_value=["Math", "Physics", "Chemistry"])
    db_utils_mock.get_subthemes = AsyncMock(return_value=["Algebra", "Geometry"])
    db_utils_mock.get_expert_recommendations = AsyncMock(return_value={
        "expert1": {
            "name": "Dr. Smith",
            "position": "Professor",
            "books": [("Book1", "Description1"), ("Book2", "Description2")]
        },
        "expert2": {
            "name": "Dr. Jones",
            "position": "Researcher",
            "books": [("Book3", "Description3")]
        }
    })
    db_utils_mock.get_theme_id = AsyncMock(return_value=1)
    return db_utils_mock


@pytest.fixture
def mock_rec_sys():
    rec_sys_mock = MagicMock()
    rec_sys_mock.recommend = AsyncMock(return_value=[
        {
            "theme_name": "Math",
            "specific_theme": "Algebra",
            "experts": [
                {
                    "expert_name": "Dr. Smith",
                    "expert_position": "Professor",
                    "book_name": "Book1",
                    "description": "Description1"
                }
            ]
        }
    ])
    return rec_sys_mock


@pytest.fixture(autouse=True)
def setup_mocks(mock_db_utils, mock_rec_sys, monkeypatch):
    monkeypatch.setattr("handlers.start.db_utils", mock_db_utils)
    monkeypatch.setattr("handlers.start.rec_sys", mock_rec_sys)
    monkeypatch.setattr("handlers.start.bot", MagicMock())


@pytest.mark.asyncio
async def test_check_subscription_callback_subscribed(mock_callback):
    mock_callback.data = "check_subscription"
    await check_subscription_callback(mock_callback)
    mock_callback.message.delete.assert_called()
    mock_callback.message.answer.assert_any_call(
        "Спасибо за подписку! Теперь вы можете пользоваться ботом. 🎉",
        reply_markup=unittest.mock.ANY,
        parse_mode="Markdown"
    )


@pytest.mark.asyncio
async def test_cmd_recc_success(mock_message):
    mock_message.text = "📝 Получить рекомендации"
    await cmd_recc(mock_message)
    mock_message.answer.assert_any_call(
        unittest.mock.ANY,
        reply_markup=unittest.mock.ANY,
        parse_mode="Markdown"
    )
    assert "Рекомендации на основе ваших запросов" in mock_message.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_process_subscription_callback_subscribe(mock_callback):
    mock_callback.data = "subscribe"
    await process_subscription_callback(mock_callback)
    mock_callback.message.delete.assert_called()
    mock_callback.message.answer.assert_any_call("Вы подписались!", reply_markup=unittest.mock.ANY)


@pytest.mark.asyncio
async def test_process_subscription_callback_unsubscribe(mock_callback):
    mock_callback.data = "unsubscribe"
    await process_subscription_callback(mock_callback)
    mock_callback.message.delete.assert_called()
    mock_callback.message.answer.assert_any_call("Вы отписались!", reply_markup=unittest.mock.ANY)


@pytest.mark.asyncio
async def test_process_subscription_callback_telegram_error(mock_callback):
    mock_callback.data = "subscribe"
    mock_callback.message.delete.side_effect = TelegramBadRequest(
        message="Message not found",
        method="deleteMessage"
    )
    await process_subscription_callback(mock_callback)
    mock_callback.message.answer.assert_any_call("Вы подписались!", reply_markup=unittest.mock.ANY)


@pytest.mark.asyncio
async def test_display_themes_first_page(mock_callback):
    mock_callback.data = "get_themes"
    await display_themes(0, mock_callback)
    mock_callback.message.edit_text.assert_called()
    assert "Выберите тему" in mock_callback.message.edit_text.call_args[0][0]


@pytest.mark.asyncio
async def test_display_subthemes_first_page(mock_callback):
    mock_callback.data = "theme_0"
    await display_subthemes(0, 0, mock_callback)
    mock_callback.message.edit_text.assert_called()
    assert "Подтемы для __Math__" in mock_callback.message.edit_text.call_args[0][0]


@pytest.mark.asyncio
async def test_display_subthemes_invalid_theme(mock_callback):
    db_utils.get_available_themes = AsyncMock(return_value=[])
    mock_callback.data = "theme_999"
    await display_subthemes(999, 0, mock_callback)
    mock_callback.message.answer.assert_any_call("⚠️ *Тема не найдена.*", parse_mode="Markdown")


@pytest.mark.asyncio
async def test_display_expert_first_expert(mock_callback):
    mock_callback.data = "subtheme_0_0"
    await display_expert(0, 0, 0, mock_callback)
    mock_callback.message.edit_text.assert_called()
    assert "Dr. Smith" in mock_callback.message.edit_text.call_args[0][0]
