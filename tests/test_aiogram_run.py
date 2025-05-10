import unittest
from unittest.mock import Mock, AsyncMock, patch
import asyncio
import threading

# Патчим psycopg2.connect до импорта
with patch('psycopg2.connect') as mock_psycopg2_connect:
    mock_psycopg2_connect.return_value = Mock()
    from aiogram_run import start_bot, main

class TestAiogramRun(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.mock_bot = AsyncMock()
        self.mock_dp = AsyncMock()
        self.mock_scheduler = Mock()
        self.mock_run_flask = Mock()
        self.mock_set_commands = AsyncMock()
        self.mock_start_router = Mock()

        self.patcher_bot = patch('aiogram_run.bot', new=self.mock_bot)
        self.patcher_dp = patch('aiogram_run.dp', new=self.mock_dp)
        self.patcher_scheduler = patch('aiogram_run.scheduler', new=self.mock_scheduler)
        self.patcher_run_flask = patch('aiogram_run.run_flask', new=self.mock_run_flask)
        self.patcher_set_commands = patch('aiogram_run.set_commands', new=self.mock_set_commands)
        self.patcher_start_router = patch('aiogram_run.start_router', new=self.mock_start_router)

        self.patcher_bot.start()
        self.patcher_dp.start()
        self.patcher_scheduler.start()
        self.patcher_run_flask.start()
        self.patcher_set_commands.start()
        self.patcher_start_router.start()

    def tearDown(self):
        self.patcher_bot.stop()
        self.patcher_dp.stop()
        self.patcher_scheduler.stop()
        self.patcher_run_flask.stop()
        self.patcher_set_commands.stop()
        self.patcher_start_router.stop()

    async def test_start_bot(self):
        await start_bot()
        self.mock_set_commands.assert_called_once()

    async def test_main(self):
        self.mock_dp.start_polling = AsyncMock()
        self.mock_bot.delete_webhook = AsyncMock()
        self.mock_bot.session.close = AsyncMock()

        await main()

        self.mock_dp.include_router.assert_called_once_with(self.mock_start_router)
        self.mock_dp.startup.register.assert_called_once_with(start_bot)
        self.mock_bot.delete_webhook.assert_called_once_with(drop_pending_updates=True)
        self.mock_dp.start_polling.assert_called_once()
        self.mock_bot.session.close.assert_called_once()
        self.mock_run_flask.assert_called_once()

    async def test_main_threading(self):
        with patch('threading.Thread') as mock_thread:
            mock_thread_instance = Mock()
            mock_thread.return_value = mock_thread_instance

            await main()

            mock_thread.assert_called_once_with(target=self.mock_run_flask, daemon=True)
            mock_thread_instance.start.assert_called_once()

if __name__ == "__main__":
    unittest.main()