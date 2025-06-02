import unittest
from unittest.mock import AsyncMock, patch, MagicMock
from db_handler.db_class import Database


class TestDatabase(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db = Database()
        self.mock_pool = MagicMock()
        self.mock_conn = AsyncMock()
        self.patcher = patch('asyncpg.create_pool', new_callable=AsyncMock, return_value=self.mock_pool)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    async def test_connect(self):
        await self.db.connect()
        self.assertEqual(self.db.pool, self.mock_pool)

    async def test_execute_success(self):
        self.db.pool = MagicMock()
        self.db.pool.acquire.return_value.__aenter__.return_value = self.mock_conn
        self.db.pool.acquire.return_value.__aexit__.return_value = None
        self.mock_conn.execute.return_value = "INSERT 1"

        result = await self.db.execute("INSERT INTO test_table (id) VALUES (1)")
        self.assertEqual(result, "INSERT 1")
        self.mock_conn.execute.assert_called_once_with("INSERT INTO test_table (id) VALUES (1)")

    async def test_execute_not_connected(self):
        self.db.pool = None
        with self.assertRaises(RuntimeError) as context:
            await self.db.execute("SELECT 1")
        self.assertEqual(str(context.exception), "База данных не подключена. Вызовите сначала connect()")

    async def test_execute_with_args(self):
        self.db.pool = MagicMock()
        self.db.pool.acquire.return_value.__aenter__.return_value = self.mock_conn
        self.db.pool.acquire.return_value.__aexit__.return_value = None
        self.mock_conn.execute.return_value = "UPDATE 1"

        result = await self.db.execute("UPDATE test_table SET name = $1 WHERE id = $2", "test", 1)
        self.assertEqual(result, "UPDATE 1")
        self.mock_conn.execute.assert_called_once_with("UPDATE test_table SET name = $1 WHERE id = $2", "test", 1)

    async def test_fetch_success(self):
        self.db.pool = MagicMock()
        self.db.pool.acquire.return_value.__aenter__.return_value = self.mock_conn
        self.db.pool.acquire.return_value.__aexit__.return_value = None
        self.mock_conn.fetch.return_value = [{'id': 1, 'name': 'test'}]

        result = await self.db.fetch("SELECT * FROM test_table")
        self.assertEqual(result, [{'id': 1, 'name': 'test'}])
        self.mock_conn.fetch.assert_called_once_with("SELECT * FROM test_table")

    async def test_fetch_not_connected(self):
        self.db.pool = None
        with self.assertRaises(RuntimeError) as context:
            await self.db.fetch("SELECT 1")
        self.assertEqual(str(context.exception), "База данных не подключена. Вызовите сначала connect()")

    async def test_fetch_with_args(self):
        self.db.pool = MagicMock()
        self.db.pool.acquire.return_value.__aenter__.return_value = self.mock_conn
        self.db.pool.acquire.return_value.__aexit__.return_value = None
        self.mock_conn.fetch.return_value = [{'id': 1, 'name': 'test'}]

        result = await self.db.fetch("SELECT * FROM test_table WHERE id = $1", 1)
        self.assertEqual(result, [{'id': 1, 'name': 'test'}])
        self.mock_conn.fetch.assert_called_once_with("SELECT * FROM test_table WHERE id = $1", 1)

    async def test_fetchrow_success(self):
        self.db.pool = MagicMock()
        self.db.pool.acquire.return_value.__aenter__.return_value = self.mock_conn
        self.db.pool.acquire.return_value.__aexit__.return_value = None
        self.mock_conn.fetchrow.return_value = {'id': 1, 'name': 'test'}

        result = await self.db.fetchrow("SELECT * FROM test_table WHERE id = 1")
        self.assertEqual(result, {'id': 1, 'name': 'test'})
        self.mock_conn.fetchrow.assert_called_once_with("SELECT * FROM test_table WHERE id = 1")

    async def test_fetchrow_not_connected(self):
        self.db.pool = None
        with self.assertRaises(RuntimeError) as context:
            await self.db.fetchrow("SELECT 1")
        self.assertEqual(str(context.exception), "База данных не подключена. Вызовите сначала connect()")

    async def test_fetchrow_with_args(self):
        self.db.pool = MagicMock()
        self.db.pool.acquire.return_value.__aenter__.return_value = self.mock_conn
        self.db.pool.acquire.return_value.__aexit__.return_value = None
        self.mock_conn.fetchrow.return_value = {'id': 1, 'name': 'test'}

        result = await self.db.fetchrow("SELECT * FROM test_table WHERE id = $1", 1)
        self.assertEqual(result, {'id': 1, 'name': 'test'})
        self.mock_conn.fetchrow.assert_called_once_with("SELECT * FROM test_table WHERE id = $1", 1)

    async def test_close_connected(self):
        self.db.pool = MagicMock()
        self.db.pool.close = AsyncMock()
        await self.db.close()
        self.db.pool.close.assert_called_once()

    async def test_close_not_connected(self):
        self.db.pool = None
        await self.db.close()  # Не должно вызывать ошибок


if __name__ == "__main__":
    unittest.main()
