import unittest
from unittest.mock import patch
from aiogram import Bot, Dispatcher
from create_bot import create_bot, dp

class TestCreateBot(unittest.TestCase):
    @patch("create_bot.Bot")  # Мокаем Bot, чтобы не отправлять реальные запросы в Telegram
    def test_create_bot_success(self, mock_bot):
        mock_bot_instance = mock_bot.return_value
        bot = create_bot()
        self.assertIsInstance(bot, Bot)
        self.assertEqual(bot, mock_bot_instance)

    def test_dispatcher_creation(self):
        self.assertIsInstance(dp, Dispatcher)

    @patch("create_bot.Bot")
    def test_create_bot_invalid_token(self, mock_bot):
        mock_bot.side_effect = Exception("Invalid token")
        with self.assertRaises(Exception):
            create_bot()

if __name__ == "__main__":
    unittest.main()