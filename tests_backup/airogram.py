import unittest
from unittest.mock import patch
from aiogram.utils import executor
from aiogram_RUN import start_bot

class TestAiogramRun(unittest.TestCase):
    @patch("aiogram.utils.executor.start_polling")
    def test_start_bot_success(self, mock_start_polling):
        start_bot()
        mock_start_polling.assert_called_once()

    @patch("aiogram.utils.executor.start_polling")
    def test_start_bot_failure(self, mock_start_polling):
        mock_start_polling.side_effect = Exception("Network error")
        with self.assertRaises(Exception):
            start_bot()

if __name__ == "__main__":
    unittest.main()