from typing import List, Optional

from decouple import config

import asyncpg
from asyncpg.pool import Pool
from asyncpg import Record


class Database:
    """
    Обертка Pool из библиотеки

    Attributes:
        pool (Pool): Класс Pool из asyncpg для взаимодействия с БД
    """

    def __init__(self) -> None:
        self.pool: Optional[Pool] = None

    async def connect(self) -> None:
        """
        Метод для подсоединения к БД
        """

        self.pool = await asyncpg.create_pool(
            user=config("PG_USER"),
            password=config("PG_PASSWORD"),
            database=config("PG_DB"),
            host=config('PG_HOST', default='localhost'),
            port=config("PG_PORT"),
            min_size=1,
            max_size=30
        )

    async def execute(
            self,
            query: str,
            *args
    ) -> str:

        if self.pool is None:
            raise RuntimeError("База данных не подключена. Вызовите сначала connect()")

        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def fetch(
            self,
            query: str,
            *args
    ) -> List[Record]:

        if self.pool is None:
            raise RuntimeError("База данных не подключена. Вызовите сначала connect()")

        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchval(
            self,
            query: str,
            *args
    ) -> Optional[any]:
        if self.pool is None:
            raise RuntimeError("База данных не подключена. Вызовите сначала connect()")

        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args)

    async def fetchrow(
            self,
            query: str,
            *args
    ) -> Optional[Record]:

        if self.pool is None:
            raise RuntimeError("База данных не подключена. Вызовите сначала connect()")

        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def close(self) -> None:
        """Закрытие БД"""

        if self.pool is not None:
            await self.pool.close()
