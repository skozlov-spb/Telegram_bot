import unittest
import logging
from unittest.mock import patch, MagicMock
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import zoneinfo
from decouple import config
from create_bot import bot, dp, scheduler, admins, logger


class TestCreateBot(unittest.TestCase):
    @patch('decouple.config')
    @patch('logging.getLogger')
    @patch('aiogram.Bot')
    @patch('aiogram.Dispatcher')
    @patch('apscheduler.schedulers.asyncio.AsyncIOScheduler')
    def setUp(self, mock_scheduler, mock_dp, mock_bot, mock_logger, mock_config):
        mock_config.side_effect = lambda key: {
            'TOKEN': '7543327903:AAGhzCID6Q9cjsRS87Yb504pkEqMESIk-HY',
            'ADMINS': '1024650317',
            'TIMEZONE': 'Europe/Moscow'
        }.get(key)

        self.mock_logger = MagicMock(spec=logging.Logger)
        self.mock_logger.level = logging.INFO
        mock_logger.return_value = self.mock_logger

        self.mock_bot_instance = MagicMock(spec=Bot)
        self.mock_bot_instance.token = '7543327903:AAGhzCID6Q9cjsRS87Yb504pkEqMESIk-HY'
        self.mock_bot_instance.default = DefaultBotProperties(parse_mode=ParseMode.HTML)
        mock_bot.return_value = self.mock_bot_instance

        self.mock_dp_instance = MagicMock(spec=Dispatcher)
        self.mock_dp_instance.storage = MemoryStorage()
        mock_dp.return_value = self.mock_dp_instance

        self.mock_scheduler_instance = MagicMock(spec=AsyncIOScheduler)
        self.mock_scheduler_instance.timezone = zoneinfo.ZoneInfo('Europe/Moscow')
        mock_scheduler.return_value = self.mock_scheduler_instance

        self.bot = bot
        self.dp = dp
        self.scheduler = scheduler
        self.admins = admins
        self.logger = logger

    def test_bot_initialization(self):
        self.assertIsInstance(self.bot, Bot)
        self.assertEqual(self.bot.token, '7543327903:AAGhzCID6Q9cjsRS87Yb504pkEqMESIk-HY')
        self.assertEqual(self.bot.default.parse_mode, ParseMode.HTML)

    def test_dp_initialization(self):
        self.assertIsInstance(self.dp, Dispatcher)
        self.assertIsInstance(self.dp.storage, MemoryStorage)

    def test_scheduler_initialization(self):
        self.assertIsInstance(self.scheduler, AsyncIOScheduler)
        self.assertEqual(str(self.scheduler.timezone), 'Europe/Moscow')

    def test_admins_initialization(self):
        self.assertEqual(self.admins, [1024650317])

    def test_config_not_modified(self):
        self.assertEqual(config('TOKEN'), '7543327903:AAGhzCID6Q9cjsRS87Yb504pkEqMESIk-HY')
        self.assertEqual(config('ADMINS'), '1024650317')


if __name__ == "__main__":
    unittest.main()
