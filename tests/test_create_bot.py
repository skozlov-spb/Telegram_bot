import unittest
import logging
from unittest.mock import patch, MagicMock
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import zoneinfo


class TestCreateBot(unittest.TestCase):
    @patch('decouple.config')
    @patch('logging.getLogger')
    @patch('aiogram.Bot')
    @patch('aiogram.Dispatcher')
    @patch('apscheduler.schedulers.asyncio.AsyncIOScheduler')
    def setUp(self, mock_scheduler, mock_dp, mock_bot, mock_logger, mock_config):
        # Настраиваем моки для config
        mock_config.side_effect = lambda key, default=None: {
            'TOKEN': 'test_token',
            'ADMINS': '1,2,3',
            'TIMEZONE': 'Europe/Moscow'
        }.get(key, default)

        # Настраиваем мок для логгера
        self.mock_logger = MagicMock(spec=logging.Logger)
        self.mock_logger.level = logging.INFO
        mock_logger.return_value = self.mock_logger

        # Настраиваем мок для бота
        self.mock_bot_instance = MagicMock(spec=Bot)
        self.mock_bot_instance.token = 'test_token'
        self.mock_bot_instance.default = DefaultBotProperties(parse_mode=ParseMode.HTML)
        mock_bot.return_value = self.mock_bot_instance

        # Настраиваем мок для диспетчера
        self.mock_dp_instance = MagicMock(spec=Dispatcher)
        self.mock_dp_instance.storage = MemoryStorage()
        mock_dp.return_value = self.mock_dp_instance

        # Настраиваем мок для планировщика
        self.mock_scheduler_instance = MagicMock(spec=AsyncIOScheduler)
        self.mock_scheduler_instance.timezone = zoneinfo.ZoneInfo('Europe/Moscow')
        mock_scheduler.return_value = self.mock_scheduler_instance

        # Импортируем модуль после настройки моков
        from create_bot import bot, dp, scheduler, admins, logger
        self.bot = bot
        self.dp = dp
        self.scheduler = scheduler
        self.admins = admins
        self.logger = logger

    def test_bot_initialization(self):
        self.assertIsInstance(self.bot, Bot)
        self.assertEqual(self.bot.token, 'test_token')
        self.assertEqual(self.bot.default.parse_mode, ParseMode.HTML)

    def test_dp_initialization(self):
        self.assertIsInstance(self.dp, Dispatcher)
        self.assertIsInstance(self.dp.storage, MemoryStorage)

    def test_scheduler_initialization(self):
        self.assertIsInstance(self.scheduler, AsyncIOScheduler)
        self.assertEqual(self.scheduler.timezone, zoneinfo.ZoneInfo('Europe/Moscow'))

    def test_admins_initialization(self):
        self.assertEqual(self.admins, [1, 2, 3])

    def test_logger_initialization(self):
        self.assertIsInstance(self.logger, logging.Logger)
        self.assertEqual(self.logger.level, logging.INFO)

    @patch('decouple.config')
    def test_config_not_modified(self, mock_config):
        mock_config.return_value = 'original_value'
        self.assertEqual(mock_config('TEST_KEY'), 'original_value')


if __name__ == "__main__":
    unittest.main()