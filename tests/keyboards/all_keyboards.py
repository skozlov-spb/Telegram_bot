import unittest
from unittest.mock import Mock, patch
from keyboards.all_keyboards import set_commands

class TestKeyboards(unittest.TestCase):
    def test_set_commands(self):
        mock_bot = Mock()
        with patch('keyboards.all_keyboards.Bot', return_value=mock_bot):
            asyncio.run(set_commands())  # Если set_commands асинхронный
            mock_bot.set_my_commands.assert_called_once()

if __name__ == "__main__":
    unittest.main()