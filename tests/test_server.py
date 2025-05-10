import unittest
from unittest.mock import Mock, patch
from server import run_flask

class TestServer(unittest.TestCase):
    def test_run_flask(self):
        with patch('server.flask.run') as mock_run:
            run_flask()
            mock_run.assert_called_once()

if __name__ == "__main__":
    unittest.main()