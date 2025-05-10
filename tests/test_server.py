import unittest
from unittest.mock import patch, MagicMock
from server import run_flask, server


class TestServer(unittest.TestCase):
    @patch('server.config')
    @patch('server.server.run')
    def test_run_flask(self, mock_run, mock_config):
        mock_config.side_effect = lambda key: {
            'PG_PORT': 'localhost',
            'SERVER_PORT': '5000'
        }.get(key)

        run_flask()

        mock_run.assert_called_once_with(
            host='localhost',
            port='5000',
            debug=False
        )


if __name__ == "__main__":
    unittest.main()