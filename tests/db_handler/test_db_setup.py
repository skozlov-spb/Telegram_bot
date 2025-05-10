import unittest
from unittest.mock import AsyncMock, patch, MagicMock
import pandas as pd
from db_handler.db_init import init_db
import asyncpg


class TestDBInit(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Мокируем конфигурационные переменные
        self.patcher_config = patch('db_handler.db_init.config', return_value="test_value")
        self.mock_config = self.patcher_config.start()

        # Мокируем пулы соединений
        self.mock_admin_pool = AsyncMock()
        self.mock_app_pool = AsyncMock()

        # Мокируем соединения
        self.mock_conn_admin = AsyncMock()
        self.mock_conn_app = AsyncMock()

        # Настраиваем поведение моков
        self.mock_admin_pool.acquire.return_value.__aenter__.return_value = self.mock_conn_admin
        self.mock_app_pool.acquire.return_value.__aenter__.return_value = self.mock_conn_app

        # Мокируем создание пулов
        self.patcher_create_pool = patch('asyncpg.create_pool', side_effect=[self.mock_admin_pool, self.mock_app_pool])
        self.mock_create_pool = self.patcher_create_pool.start()

        # Мокируем pandas
        self.mock_df = MagicMock()
        self.patcher_pd = patch('pandas.read_excel', return_value=self.mock_df)
        self.mock_pd = self.patcher_pd.start()

        # Настраиваем тестовые данные
        self.test_data = {
            'Имя эксперта': ['Expert1'],
            'Должность эксперта в СПбГУ': ['Position1'],
            'Общая тема подборки': ['Theme1'],
            'Конкретная тема подборки': ['Subtheme1'],
            'Название книги': [['Book1', 'Book2']],
            'Короткое описание от эксперта': [['Desc1', 'Desc2']]
        }

        # Мокируем группировку данных
        self.mock_grouped = MagicMock()
        self.mock_df.groupby.return_value = self.mock_grouped
        self.mock_grouped.agg.return_value = self.mock_df
        self.mock_df.iterrows.return_value = [(0, self.test_data)]

    def tearDown(self):
        self.patcher_config.stop()
        self.patcher_create_pool.stop()
        self.patcher_pd.stop()

    async def test_init_db_database_does_not_exist(self):
        # Настраиваем моки для случая, когда БД не существует
        self.mock_conn_admin.fetchval.return_value = None
        self.mock_conn_app.fetchval.side_effect = [1, 1, 1, 1]  # IDs для эксперта, темы и книг

        await init_db()

        # Проверяем вызовы для создания БД
        self.mock_conn_admin.fetchval.assert_called_once()
        self.mock_conn_admin.execute.assert_called_once_with('CREATE DATABASE "test_value"')

        # Проверяем вызовы для создания таблиц
        self.mock_conn_app.execute.assert_called_once()

        # Проверяем вызовы для вставки данных
        self.assertEqual(self.mock_conn_app.fetchval.call_count, 4)
        self.assertEqual(self.mock_conn_app.execute.call_count, 3)  # 1 для таблиц + 2 для рекомендаций

        # Проверяем закрытие пулов
        self.mock_admin_pool.close.assert_called_once()
        self.mock_app_pool.close.assert_called_once()

    async def test_init_db_database_exists(self):
        # Настраиваем моки для случая, когда БД существует
        self.mock_conn_admin.fetchval.return_value = 1

        await init_db()

        # Проверяем, что БД не создавалась
        self.mock_conn_admin.execute.assert_not_called()

        # Проверяем, что не было попыток создания таблиц и вставки данных
        self.mock_conn_app.execute.assert_not_called()
        self.mock_conn_app.fetchval.assert_not_called()

        # Проверяем закрытие только admin пула
        self.mock_admin_pool.close.assert_called_once()
        self.mock_app_pool.close.assert_not_called()

    async def test_init_db_with_empty_data(self):
        # Настраиваем моки для пустых данных
        self.mock_conn_admin.fetchval.return_value = None
        self.mock_df.iterrows.return_value = []

        await init_db()

        # Проверяем создание БД и таблиц
        self.mock_conn_admin.execute.assert_called_once()
        self.mock_conn_app.execute.assert_called_once()

        # Проверяем, что не было попыток вставки данных
        self.mock_conn_app.fetchval.assert_not_called()


if __name__ == "__main__":
    unittest.main()