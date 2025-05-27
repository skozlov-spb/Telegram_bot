import unittest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from unittest import IsolatedAsyncioTestCase
import sys
import importlib


class TestAiogramRun(IsolatedAsyncioTestCase):
    def setUp(self):
        self.mock_thread = patch('threading.Thread').start()
        self.mock_run_flask = patch('server.run_flask').start()

        self.mock_bot = AsyncMock()
        self.mock_dp = MagicMock()

        self.patch_create_bot = patch.dict('sys.modules', {
            'create_bot': MagicMock(
                bot=self.mock_bot,
                dp=self.mock_dp,
                scheduler=MagicMock()
            )
        }).start()

        self.mock_init_db = patch('db_handler.db_setup.init_db', AsyncMock()).start()
        self.mock_set_commands = patch('keyboards.all_keyboards.set_commands', AsyncMock()).start()
        self.mock_start_router = patch('handlers.start.start_router').start()

        self.mock_dp.startup = MagicMock()
        self.mock_dp.resolve_used_update_types = MagicMock(return_value=['message'])
        self.mock_dp.start_polling = AsyncMock()

        self.mock_bot.delete_webhook = AsyncMock()
        self.mock_bot.session = MagicMock()
        self.mock_bot.session.close = AsyncMock()

        self.addCleanup(patch.stopall)

    async def test_start_bot_success(self):
        from aiogram_run import start_bot

        await start_bot()
        self.mock_set_commands.assert_awaited_once()

    async def test_bot_session_closed_on_error(self):
        from aiogram_run import main

        self.mock_dp.start_polling.side_effect = Exception("Test error")

        try:
            await main()
        except Exception:
            pass

        self.mock_bot.session.close.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()