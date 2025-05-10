import unittest
from unittest.mock import Mock, AsyncMock, patch
from db_handler.db_utils import DBUtils, ALLOWED_ACTIVITIES

class TestDBUtils(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.mock_db = Mock()
        self.mock_bot = Mock()
        self.db_utils = DBUtils(self.mock_db, self.mock_bot)

    async def test_check_user_subscription(self):
        self.mock_bot.get_chat_member = AsyncMock(return_value=Mock(status='member'))
        result = await self.db_utils.check_user_subscription(123, -1001752627981)
        self.assertTrue(result)
        self.mock_bot.get_chat_member.assert_called_once()

    async def test_register_user(self):
        self.mock_db.query = AsyncMock(return_value=[(False,)])
        result = await self.db_utils.register_user(123, "test_user")
        self.assertFalse(result)
        self.mock_db.query.assert_called_once()

    async def test_log_user_activity(self):
        self.mock_db.query = AsyncMock()
        result = await self.db_utils.log_user_activity(123, "start_bot")
        self.assertTrue(result)
        self.mock_db.query.assert_called_once()

if __name__ == "__main__":
    unittest.main()