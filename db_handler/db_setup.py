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

    if not exists:
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
                    expert_name VARCHAR(40) DEFAULT 'Имя скрыто',
                    expert_position VARCHAR(150) DEFAULT 'Должность скрыта',
                    
                    UNIQUE (expert_name, expert_position)
                );
                
                CREATE TABLE IF NOT EXISTS themes (
                    theme_id SERIAL PRIMARY KEY,

                    theme_name VARCHAR(100) NOT NULL,
                    specific_theme VARCHAR(100) NOT NULL,
                    
                    UNIQUE (theme_name, specific_theme)
                );
                
                CREATE TABLE IF NOT EXISTS books (
                    book_id SERIAL PRIMARY KEY,

                    book_name VARCHAR(400) NOT NULL UNIQUE,
                    book_image VARCHAR(1000) UNIQUE
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
                
                CREATE TYPE user_role AS ENUM ('user', 'admin');

                CREATE TABLE IF NOT EXISTS users (
                    user_id SERIAL PRIMARY KEY,
                    username VARCHAR(50) NOT NULL,
                    registration_date TIMESTAMP DEFAULT NOW(),
                    role user_role DEFAULT 'user'
                );
                
                CREATE TYPE activity_type AS ENUM (
                    'start_bot',                  -- При начале использования бота --
                    'get_expert_recommendation',  -- Получить экспертные рекомендации --
                    'get_recommendation',         -- Получить рекомендации от бота --
                    'subscribe',                  -- Флаг подписки человека --
                    'unsubscribe',                -- Флаг отписки --
                    'subscribed_channels'         -- Подписка на канале --
                );
                
                CREATE TABLE IF NOT EXISTS user_activity_logs (
                    log_id SERIAL PRIMARY KEY,
                    user_id INT NOT NULL,
                    request_time TIMESTAMP DEFAULT NOW(),
                    request_type activity_type,
                    theme_id INT DEFAULT NULL,
    
                    FOREIGN KEY(user_id) REFERENCES users (user_id) ON DELETE CASCADE,
                    FOREIGN KEY(theme_id) REFERENCES themes (theme_id) ON DELETE SET NULL
                );
            """)

            admins_ids = [int(admin_id) for admin_id in config('ADMINS').split(',')]

            for admin_id in admins_ids:
                await conn.execute(
                    """
                    INSERT INTO users 
                    (user_id, username, role)
                    VALUES ($1, $2, $3)
                    ON CONFLICT DO NOTHING
                    """,
                    admin_id, f'user_{admin_id}', 'admin'
                )
