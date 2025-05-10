import unittest
import logging
from unittest.mock import Mock, patch
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from decouple import config
import zoneinfo

# Патчим config до импорта
with patch('decouple.config') as mock_config:
    mock_config.return_value = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    mock_config.side_effect = lambda key: {
        'TOKEN': '123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11',
        'ADMINS': '1,2,3'
    }.get(key, 'default')
    from create_bot import bot, dp, scheduler, admins, logger

class TestCreateBot(unittest.TestCase):
    def setUp(self):
        self.original_config = config.__dict__.copy()
        self.original_admins = admins.copy()

    def tearDown(self):
        config.__dict__.update(self.original_config)
        admins[:] = self.original_admins

    def test_bot_initialization(self):
        self.assertIsInstance(bot, Bot)
        self.assertEqual(bot.token, "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")
        self.assertEqual(bot.default.parse_mode, ParseMode.HTML)

    def test_dp_initialization(self):
        self.assertIsInstance(dp, Dispatcher)
        self.assertIsInstance(dp.storage, MemoryStorage)

    def test_scheduler_initialization(self):
        self.assertIsInstance(scheduler, AsyncIOScheduler)
        self.assertEqual(scheduler.timezone, zoneinfo.ZoneInfo('Europe/Moscow'))

    def test_admins_initialization(self):
        self.assertEqual(admins, [1, 2, 3])

    @patch('logging.getLogger')
    def test_logger_initialization(self, mock_get_logger):
        mock_logger = Mock(spec=logging.Logger)
        mock_logger.level = logging.INFO
        mock_logger.handlers = [Mock(formatter=Mock(_fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s'))]
        mock_get_logger.return_value = mock_logger

        self.assertIsInstance(logger, logging.Logger)
        self.assertEqual(logger.level, logging.INFO)
        self.assertEqual(
            logger.handlers[0].formatter._fmt,
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    def test_config_not_modified(self):
        original_config_value = config('TEST_KEY', default='default')
        self.assertEqual(original_config_value, 'default')

if __name__ == "__main__":
    unittest.main()