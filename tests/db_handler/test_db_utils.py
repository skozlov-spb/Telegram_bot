import unittest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from db_handler.db_utils import DBUtils
from db_handler.db_class import Database

class TestDBUtils(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.mock_db = AsyncMock(Database)
        self.mock_bot = AsyncMock(Bot)
        self.db_utils = DBUtils(db=self.mock_db, bot=self.mock_bot)

    async def test_check_user_subscription_not_subscribed(self):
        user_id = 123
        channel_id = -1001752627981
        self.mock_bot.get_chat_member.side_effect = TelegramBadRequest("user not found", {"error_code": "USER_NOT_PARTICIPANT"})

        result = await self.db_utils.check_user_subscription(user_id, channel_id)
        self.assertFalse(result)
        self.mock_bot.get_chat_member.assert_called_once_with(chat_id=channel_id, user_id=user_id)

    async def test_check_user_subscription_subscribed(self):
        user_id = 123
        channel_id = -1001752627981
        mock_chat_member = MagicMock()
        mock_chat_member.status = "member"
        self.mock_bot.get_chat_member.return_value = mock_chat_member

        result = await self.db_utils.check_user_subscription(user_id, channel_id)
        self.assertTrue(result)
        self.mock_bot.get_chat_member.assert_called_once_with(chat_id=channel_id, user_id=user_id)

    async def test_get_available_themes(self):
        self.mock_db.fetch.return_value = [
            {'theme_name': 'theme1'},
            {'theme_name': 'theme2'}
        ]

        result = await self.db_utils.get_available_themes()
        self.assertEqual(result, ['theme1', 'theme2'])
        self.mock_db.fetch.assert_called_once()

    async def test_get_subthemes(self):
        theme_name = "theme1"
        self.mock_db.fetch.return_value = [
            {'specific_theme': 'subtheme1'},
            {'specific_theme': 'subtheme2'}
        ]

        result = await self.db_utils.get_subthemes(theme_name)
        self.assertEqual(result, ['subtheme1', 'subtheme2'])
        self.mock_db.fetch.assert_called_once()

    async def test_get_statistic(self):
        self.mock_db.fetch.return_value = [
            {'user_id': 123},
            {'user_id': 456}
        ]
        self.db_utils.is_active = AsyncMock(side_effect=[True, False])  # Первый активен, второй нет
        self.db_utils.is_subscribed = AsyncMock(side_effect=[True, False])  # Первый подписан, второй нет

        result = await self.db_utils.get_statistic()
        expected = {
            "total_users": 2,
            "inactive_percent": 50.0,  # 1 из 2 неактивен
            "subscribed_users": 1
        }
        self.assertEqual(result, expected)
        self.mock_db.fetch.assert_called_once()

    async def test_is_active_true(self):
        user_id = 123
        recent_time = datetime.now() - timedelta(days=30)
        self.mock_db.fetchrow.return_value = {'request_time': recent_time}

        result = await self.db_utils.is_active(user_id)
        self.assertTrue(result)
        self.mock_db.fetchrow.assert_called_once()

    async def test_is_active_false(self):
        user_id = 123
        old_time = datetime.now() - timedelta(days=100)
        self.mock_db.fetchrow.return_value = {'request_time': old_time}

        result = await self.db_utils.is_active(user_id)
        self.assertFalse(result)
        self.mock_db.fetchrow.assert_called_once()

    async def test_is_subscribed_true(self):
        user_id = 123
        self.mock_db.fetchrow.return_value = {'request_type': 'subscribe'}

        result = await self.db_utils.is_subscribed(user_id)
        self.assertTrue(result)
        self.mock_db.fetchrow.assert_called_once()

    async def test_is_subscribed_false(self):
        user_id = 123
        self.mock_db.fetchrow.return_value = {'request_type': 'unsubscribe'}

        result = await self.db_utils.is_subscribed(user_id)
        self.assertFalse(result)
        self.mock_db.fetchrow.assert_called_once()

    async def test_log_user_activity_success(self):
        user_id = 123
        activity_type = "start_bot"
        theme_id = None
        self.mock_db.execute.return_value = "INSERT 1"

        result = await self.db_utils.log_user_activity(user_id, activity_type, theme_id)
        self.assertTrue(result)
        self.mock_db.execute.assert_called_once()

    async def test_log_user_activity_invalid_type(self):
        user_id = 123
        activity_type = "invalid_action"
        theme_id = None

        result = await self.db_utils.log_user_activity(user_id, activity_type, theme_id)
        self.assertFalse(result)
        self.mock_db.execute.assert_not_called()

if __name__ == "__main__":
    unittest.main()