import unittest
from unittest.mock import AsyncMock, patch, MagicMock
import pandas as pd
from db_handler.db_setup import init_db

class TestDBSetup(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.mock_admin_pool = MagicMock()
        self.mock_app_pool = MagicMock()
        self.mock_conn_admin = AsyncMock()
        self.mock_conn_app = AsyncMock()

        self.mock_admin_pool.acquire.return_value.__aenter__.return_value = self.mock_conn_admin
        self.mock_admin_pool.acquire.return_value.__aexit__.return_value = None
        self.mock_app_pool.acquire.return_value.__aenter__.return_value = self.mock_conn_app
        self.mock_app_pool.acquire.return_value.__aexit__.return_value = None

        self.patcher_pool = patch('asyncpg.create_pool', new_callable=AsyncMock, side_effect=[self.mock_admin_pool, self.mock_app_pool])
        self.patcher_pool.start()

        self.patcher_pd = patch('db_handler.db_setup.pd.read_excel', return_value=MagicMock())
        self.patcher_pd.start()

        self.patcher_config = patch('db_handler.db_setup.config', side_effect=lambda key: {
            'PG_HOST': 'localhost',
            'PG_DB': 'test_db',
            'PG_USER': 'test_user',
            'PG_PASSWORD': 'test_pass',
            'PG_PORT': '5432'
        }[key])
        self.patcher_config.start()

        self.mock_admin_pool.close = AsyncMock()
        self.mock_app_pool.close = AsyncMock()

    def tearDown(self):
        self.patcher_pool.stop()
        self.patcher_pd.stop()
        self.patcher_config.stop()

    async def test_init_db_database_exists(self):
        self.mock_conn_admin.fetchval.return_value = 1

        await init_db()

        self.mock_conn_admin.execute.assert_not_called()
        self.mock_conn_app.execute.assert_not_called()
        self.mock_conn_app.fetchval.assert_not_called()
        self.mock_admin_pool.close.assert_called_once()
        self.mock_app_pool.close.assert_not_called()

    async def test_init_db_admin_pool_close(self):
        # Настраиваем мок для проверки существования БД
        self.mock_conn_admin.fetchval.return_value = None
        self.mock_conn_admin.execute.return_value = None

        await init_db()

        self.mock_admin_pool.close.assert_called_once()

    async def test_init_db_app_pool_close_on_create(self):
        self.mock_conn_admin.fetchval.return_value = None
        self.mock_conn_admin.execute.return_value = None
        self.mock_conn_app.execute.return_value = None

        mock_df = MagicMock()
        grouped_data = MagicMock()
        mock_df.groupby.return_value = grouped_data
        grouped_data.agg.return_value = MagicMock()
        grouped_data.iterrows.return_value = []
        self.patcher_pd.return_value = mock_df

        await init_db()

        self.mock_app_pool.close.assert_called_once()

    async def test_init_db_no_data_processing(self):
        self.mock_conn_admin.fetchval.return_value = None
        self.mock_conn_admin.execute.return_value = None
        self.mock_conn_app.execute.return_value = None

        mock_df = MagicMock()
        grouped_data = MagicMock()
        mock_df.groupby.return_value = grouped_data
        grouped_data.agg.return_value = MagicMock()
        grouped_data.iterrows.return_value = []
        self.patcher_pd.return_value = mock_df

        await init_db()

        self.mock_conn_app.fetchval.assert_not_called()
        self.mock_conn_app.execute.assert_called_once()

if __name__ == "__main__":
    unittest.main()