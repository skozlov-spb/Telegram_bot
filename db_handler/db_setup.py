import asyncpg
import pandas as pd
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
                
                CREATE TABLE IF NOT EXISTS users (
                    user_id SERIAL PRIMARY KEY,
                    username VARCHAR(50) NOT NULL,
                    registration_date TIMESTAMP DEFAULT NOW()
                );
                
                CREATE TYPE activity_type AS ENUM (
                    'start_bot',                  -- При начале использования бота --
                    'get_expert_recommendation',  -- Получить экспертные рекомендации --
                    'get_recommendation',         -- Получить рекомендации от бота --
                    'subscribe',                  -- Флаг подписки человека --
                    'unsubscribe'                 -- Флаг отписки --
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

        # Импортируем данные
        experts = pd.read_excel(
            'db_handler/data/ExpertsPreferences.xlsx',
            skiprows=7,
            names=[
                "expert_name",       
                "expert_position",   
                "general_theme",     
                "specific_theme",    
                "book_name",         
                "description",       
            ],
        ).dropna(subset=["expert_name"])

        # Группируем по авторам, подтемам и тп
        grouped = experts.groupby([
            'expert_name',
            'expert_position',
            'general_theme',
            'specific_theme'
        ], as_index=False).agg({
            'book_name': list,
            'description': list
        })
        
        cache = {
            'experts': {},
            'themes': {},
            'books': {}
        }

        # Заполняем таблицы
        async with app_pool.acquire() as conn:
            for _, row in grouped.iterrows():
                expert_key = (row['expert_name'].strip(), row['expert_position'].strip())
                if expert_key not in cache['experts']:
                    expert_id = await conn.fetchval("""
                        INSERT INTO experts (expert_name, expert_position)
                        VALUES ($1, $2)
                        ON CONFLICT (expert_name, expert_position) DO NOTHING
                        RETURNING expert_id
                    """, *expert_key)

                    if not expert_id:
                        expert_id = await conn.fetchval(
                            """SELECT expert_id FROM experts 
                            WHERE expert_name = $1 AND expert_position = $2""",
                            *expert_key
                        )
                    cache['experts'][expert_key] = expert_id
                    
                theme_key = (row['general_theme'].strip(), row['specific_theme'].strip())
                if theme_key not in cache['themes']:
                    theme_id = await conn.fetchval("""
                        INSERT INTO themes (theme_name, specific_theme)
                        VALUES ($1, $2)
                        ON CONFLICT (theme_name, specific_theme) DO NOTHING
                        RETURNING theme_id
                    """, *theme_key)
                    
                    if not theme_id:
                        theme_id = await conn.fetchval(
                            "SELECT theme_id FROM themes WHERE theme_name = $1 AND specific_theme = $2",
                            *theme_key
                        )
                    cache['themes'][theme_key] = theme_id

                for book_name, description in zip(row['book_name'], row['description']):
                    book_name = book_name.strip()
                    if book_name not in cache['books']:
                        book_id = await conn.fetchval("""
                            INSERT INTO books (book_name)
                            VALUES ($1)
                            ON CONFLICT (book_name) DO NOTHING
                            RETURNING book_id
                        """, book_name)

                        if not book_id:
                            book_id = await conn.fetchval(
                                "SELECT book_id FROM books WHERE book_name = $1",
                                book_name
                            )
                        cache['books'][book_name] = book_id

                    await conn.execute("""
                        INSERT INTO experts_recommendations 
                        (expert_id, theme_id, book_id, description)
                        VALUES ($1, $2, $3, $4)
                    """, 
                    cache['experts'][expert_key], 
                    cache['themes'][theme_key], 
                    cache['books'][book_name],
                    description.strip())

        await app_pool.close()
