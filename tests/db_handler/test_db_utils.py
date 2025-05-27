import pytest
from unittest.mock import AsyncMock, patch
from aiogram import Bot
from db_handler.db_utils import DBUtils
import pandas as pd

class TestDBUtils:
    def setup_method(self):
        self.mock_db = AsyncMock()
        self.mock_conn = AsyncMock()
        self.mock_db.pool.acquire = AsyncMock(return_value=self.mock_conn)
        self.mock_conn.__aenter__ = AsyncMock(return_value=self.mock_conn)
        self.mock_conn.__aexit__ = AsyncMock()
        self.mock_bot = AsyncMock(spec=Bot)
        self.db_utils = DBUtils(db=self.mock_db, bot=self.mock_bot)

    @pytest.mark.asyncio
    async def test_upload_data_failure(self):
        # Simulate pandas.read_excel failure
        with patch('pandas.read_excel', side_effect=Exception("File error")):
            result = await self.db_utils.upload_data("test.xlsx")
            assert result is False

    @pytest.mark.asyncio
    async def test_register_user_new(self):
        self.mock_db.fetchrow = AsyncMock(return_value={'is_new': True})
        self.mock_db.execute = AsyncMock(return_value="INSERT 0 1")
        result = await self.db_utils.register_user(123, "testuser")
        assert result is True
        self.mock_db.fetchrow.assert_called_once()
        self.mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_user_existing(self):
        self.mock_db.fetchrow = AsyncMock(return_value={'is_new': False})
        self.mock_db.execute = AsyncMock(return_value="INSERT 0 1")
        result = await self.db_utils.register_user(123, "testuser")
        assert result is False
        self.mock_db.fetchrow.assert_called_once()
        self.mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_user_activity_success(self):
        self.mock_db.execute = AsyncMock(return_value="INSERT 0 1")
        result = await self.db_utils.log_user_activity(123, "start_bot")
        assert result is True
        self.mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_user_activity_invalid(self):
        result = await self.db_utils.log_user_activity(123, "invalid_activity")
        assert result is False
        self.mock_db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_available_themes(self):
        self.mock_db.fetch = AsyncMock(return_value=[{'theme_name': 'Theme1'}, {'theme_name': 'Theme2'}])
        result = await self.db_utils.get_available_themes()
        assert result == ["Theme1", "Theme2"]
        self.mock_db.fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_subthemes(self):
        self.mock_db.fetch = AsyncMock(return_value=[{'specific_theme': 'Sub1'}, {'specific_theme': 'Sub2'}])
        result = await self.db_utils.get_subthemes("Theme1")
        assert result == ["Sub1", "Sub2"]
        self.mock_db.fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_expert_recommendations(self):
        self.mock_db.fetch = AsyncMock(return_value=[
            {
                'expert_id': 1,
                'expert_name': 'Expert1',
                'expert_position': 'Position1',
                'book_name': 'Book1',
                'description': 'Desc1'
            }
        ])
        result = await self.db_utils.get_expert_recommendations("Subtheme1")
        assert result == {1: {'name': 'Expert1', 'position': 'Position1', 'books': [('Book1', 'Desc1')]}}
        self.mock_db.fetch.assert_called_once()