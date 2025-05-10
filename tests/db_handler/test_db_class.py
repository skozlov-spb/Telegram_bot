import unittest
from unittest.mock import Mock, patch
from db_handler.db_class import Database

class TestDatabase(unittest.TestCase):
    @patch('psycopg2.connect')
    def test_db_connection(self, mock_connect):
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        db = Database()
        self.assertEqual(db.conn, mock_conn)
        self.assertTrue(mock_conn.autocommit)

    @patch('psycopg2.connect')
    def test_query_execution(self, mock_connect):
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        db = Database()
        db.query("SELECT 1")
        mock_conn.cursor.assert_called_once()
        mock_cursor.execute.assert_called_once_with("SELECT 1")
        mock_cursor.close.assert_called_once()

    @patch('psycopg2.connect')
    def test_close_connection(self, mock_connect):
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        db = Database()
        db.close()
        mock_conn.close.assert_called_once()

if __name__ == "__main__":
    unittest.main()