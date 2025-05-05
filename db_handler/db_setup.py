import asyncpg
from decouple import config

from .db_class import Database


async def init_db():
    # Данные для БД
    PG_HOST = config("PG_HOST")
    PG_DB = config("PG_DB")
    PG_USER = config("PG_USER")
    PG_PASSWORD = config("PG_PASSWORD")
    PG_PORT = config("PG_PORT")

    # Подключаемся к существующей БД
    admin_pool = await asyncpg.create_pool(
        user=PG_USER,
        password=PG_PASSWORD,
        database="postgres",
        host=PG_HOST,
        port=PG_PORT,
        min_size=1, max_size=2
    )
    async with admin_pool.acquire() as conn:

        # Проверяем, существует ли наша БД
        exists = await conn.fetchval(
            """
            SELECT 1 FROM pg_database WHERE datname = $1
            """,
            PG_DB
        )

        if not exists:
            # Если нет, создаём базу данных
            await conn.execute(f'CREATE DATABASE "{PG_DB}"')

    # Закрываем административный пул
    await admin_pool.close()

    # Заходим в актуальную БД
    app_pool = await asyncpg.create_pool(
        user=PG_USER,
        password=PG_PASSWORD,
        database=PG_DB,
        host=PG_HOST,
        port=PG_PORT,
        min_size=1, max_size=5
    )

    async with app_pool.acquire() as conn:
        # Если таблицы не существуют, то создаем и заполняем отношениями
        await conn.execute("""
                CREATE TABLE IF NOT EXISTS experts (
                    expert_id SERIAL PRIMARY KEY,
                    expert_name VARCHAR(30) DEFAULT 'Имя скрыто',
                    expert_position VARCHAR(30) DEFAULT 'Должность скрыта'
                );
                
                CREATE TABLE IF NOT EXISTS themes (
                    theme_id SERIAL PRIMARY KEY,
                    theme_name VARCHAR(30) UNIQUE NOT NULL,
                    specific_theme VARCHAR(50) UNIQUE NOT NULL
                );
                
                CREATE TABLE IF NOT EXISTS books (
                    book_id SERIAL PRIMARY KEY,
                    book_name VARCHAR(30) NOT NULL UNIQUE,
                    book_image VARCHAR(100) UNIQUE
                );
                
                CREATE TABLE IF NOT EXISTS experts_recommendations (
                    rec_id SERIAL PRIMARY KEY,
                    expert_id INT NOT NULL,
                    theme_id INT NOT NULL,
                    book_id INT NOT NULL,
                    description TEXT NOT NULL,

                    FOREIGN KEY(expert_id) REFERENCES experts (expert_id) ON DELETE CASCADE,
                    FOREIGN KEY(theme_id) REFERENCES themes (theme_id)ON DELETE CASCADE,
                    FOREIGN KEY(book_id) REFERENCES books (book_id) ON DELETE CASCADE
                );
                
                CREATE TABLE IF NOT EXISTS users (
                    user_id SERIAL PRIMARY KEY,
                    username VARCHAR(50) NOT NULL,
                    registration_date TIMESTAMP DEFAULT NOW()
                );
                
                CREATE TABLE IF NOT EXISTS user_preferences (
                    pref_id SERIAL PRIMARY KEY,
                    user_id INT NOT NULL,
                    theme_id INT NOT NULL,

                    FOREIGN KEY(user_id) REFERENCES users (user_id) ON DELETE CASCADE,
                    FOREIGN KEY(theme_id) REFERENCES themes (theme_id) ON DELETE CASCADE
                );
                
                CREATE TABLE IF NOT EXISTS user_activity_logs (
                    log_id SERIAL PRIMARY KEY,
                    user_id INT NOT NULL,
                    request_time TIMESTAMP DEFAULT NOW(),
                    request_type TEXT NOT NULL CHECK (request_type IN ('use_bot', 'get_recommendation', 'unsubscribe')),
                    theme_id INT DEFAULT NULL,

                    FOREIGN KEY(user_id) REFERENCES users (user_id) ON DELETE CASCADE,
                    FOREIGN KEY(theme_id) REFERENCES themes (theme_id) ON DELETE SET NULL
                );
            """)

    await app_pool.close()
