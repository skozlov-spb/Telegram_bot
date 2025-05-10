import unittest
from db_handler.db_setup import setup_database

class TestDbSetup(unittest.TestCase):
    def test_setup_database(self):
        db = setup_database(":memory:")
        result = db.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchone()
        self.assertIsNotNone(result)

if __name__ == "__main__":
    unittest.main()