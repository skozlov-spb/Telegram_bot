import logging
from typing import List, Optional, Dict
from datetime import datetime, timedelta
import pandas as pd
import psycopg2
import asyncpg
from asyncpg.pool import Pool
from decouple import config

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramAPIError
from aiogram.enums import ChatMemberStatus

from .db_class import Database


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ALLOWED_ACTIVITIES = [
    'start_bot',
    'get_expert_recommendation',
    'get_recommendation',
    'subscribe',
    'unsubscribe',
    'subscribed_channels'
]


def get_admin_ids():
    try:
        conn = psycopg2.connect(
            dbname=config("PG_DB"),
            user=config("PG_USER"),
            password=config("PG_PASSWORD"),
            host=config("PG_HOST"),
            port=config("PG_PORT")
        )
    except psycopg2.OperationalError as e:
        logger.error(f"Не удалось подключиться к БД")
        return [int(admin_id) for admin_id in config('ADMINS').split(',')]

    with conn.cursor() as cur:
        cur.execute("SELECT user_id FROM users WHERE role = 'admin'")
        rows = cur.fetchall()
    conn.close()

    return [row[0] for row in rows]


class DBUtils:
    """
    Класс с методами для работы бота

    Attributes:
        db (Database): Класс нашей БД
        bot (Bot): Телеграмм бот
    """
    def __init__(
            self,
            db: Database,
            bot: Bot
    ) -> None:

        self.db: Database = db
        self.bot: Bot = bot

    async def get_admin_ids(self):
        rows = await self.db.fetch("SELECT user_id FROM users WHERE role = 'admin'")
        return [row['user_id'] for row in rows]

    async def register_user(
            self,
            user_id: int,
            username: str
    ) -> bool:
        """
        Регистрация/проверка пользователя в БД

        :param user_id: ID пользователя Telegram
        :param username: Имя пользователя (или полное имя)
        :return: True если пользователь УЖЕ был зарегистрирован, False если был зарегистрирован только что
        """

        try:
            result = await self.db.fetchrow(
                """
                    INSERT INTO users (user_id, username, registration_date, role) 
                    VALUES 
                        ($1, $2, NOW() AT TIME ZONE 'Europe/Moscow', 'user')
                        ON CONFLICT (user_id)
                        DO UPDATE SET username = EXCLUDED.username
                        RETURNING (xmax = 0) AS is_new
                """,
                user_id,
                username
            )
            
            is_new = result['is_new'] if result else False

            if is_new:
                logger.info(f"Зарегистрирован новый пользователь: {username} (ID: {user_id})")
                await self.log_user_activity(user_id, 'start_bot')
                return True

            else:
                logger.info(f"Пользователь уже существует: {username} (ID: {user_id})")
                await self.log_user_activity(user_id, 'start_bot')
                return False

        except Exception as exc:
            logger.error(f"Ошибка регистрации пользователя: {exc}")
            return False

    async def log_user_activity(
            self,
            user_id: int,
            activity_type: str,
            theme_id: Optional[int] = None
    ) -> bool:
        """Логирование активности пользователя"""

        try:
            if activity_type not in ALLOWED_ACTIVITIES:
                logger.error(f"Недопустимый тип активности: {activity_type}")
                return False

            await self.db.execute(
                """
                INSERT INTO user_activity_logs (user_id, request_type, theme_id) 
                VALUES ($1, $2, $3)
                """,
                user_id,
                activity_type,
                theme_id
            )

            return True

        except Exception as exc:
            logger.error(f"Ошибка логирования активности: {exc}")
            return False

    async def get_available_themes(self) -> List[str]:
        """Получение списка уникальных названий тем"""

        try:
            result = await self.db.fetch(
                """
                SELECT DISTINCT 
                    theme_name 
                FROM themes 
                ORDER BY theme_name
                """
            )
            return [row['theme_name'] for row in result]  # Извлекаем только названия

        except Exception as exc:
            logger.error(f"Ошибка получения тем: {exc}")
            return []

    async def get_subthemes(
            self,
            theme_name: str
    ) -> List[str]:
        """Получаем список подтем для кнопок"""

        try:
            result = await self.db.fetch(
                """
                SELECT 
                    specific_theme 
                FROM themes 
                WHERE theme_name = $1 
                ORDER BY specific_theme
                """,
                theme_name
            )
            return [row['specific_theme'] for row in result]

        except Exception as exc:
            logger.error(f"Ошибка получения подтем: {exc}")
            return []

    async def get_expert_recommendations(
            self,
            subtheme_name: str
    ) -> Optional[Dict[str, Dict]]:
        """
        Получение рекомендаций экспертов по подтеме

        :return selections: Возвращает словарь ID автора - (имя автора, должность, список книг и описаний)
        """
        try:
            recommendations = await self.db.fetch(
                """
                SELECT
                    e.expert_id,
                    e.expert_name, 
                    e.expert_position, 
                    b.book_name,  
                    er.description
                FROM
                    experts_recommendations er
                    JOIN books b ON er.book_id = b.book_id
                    JOIN experts e ON er.expert_id = e.expert_id
                    JOIN themes t ON er.theme_id = t.theme_id
                WHERE t.specific_theme = $1
                """,
                subtheme_name
            )
            
            if not recommendations:
                return None

            selections = {
                row['expert_id']: {
                    'name': row['expert_name'],
                    'position': row['expert_position'],
                    'books': []
                }
                for row in recommendations
            }
            for row in recommendations:
                selections[row['expert_id']]['books'].append(
                    (row['book_name'], row['description'])
                )

            return selections
            
        except Exception as exc:
            logger.error(f"Ошибка получения рекомендаций для подтемы '{subtheme_name}': {exc}")
            return None

    async def is_active(
            self,
            user_id: int
    ) -> bool:
        """
        Пользователь считается активным, если его последняя активность была не более 3 месяцев назад.
        """
        try:
            result = await self.db.fetchrow(
                """
                SELECT 
                    request_time 
                FROM user_activity_logs 
                WHERE user_id = $1 
                ORDER BY request_time DESC 
                LIMIT 1
                """,
                user_id
            )

            if not result:
                return False

            last_activity = result['request_time']
            three_months_ago = datetime.now() - timedelta(days=90)

            return last_activity > three_months_ago

        except Exception as exc:
            logger.error(f"Ошибка при проверке активности пользователя {user_id}: {exc}")
            return False

    async def get_statistic(self) -> dict:
        """
        Получение статистики:
        1. Общее число пользователей
        2. Процент неактивных пользователей
        3. Число подписанных на рассылку
        """
        try:
            
            total_users = await self.db.fetchrow("SELECT COUNT(*) FROM users")

            if total_users == 0:
                return {
                "total_users": total_users,
                "inactive_percent": 0.0,
                "subscribed_users": 0,
            }

            inactive_count = await self.db.fetchrow(
                """
                SELECT COUNT(*)
                FROM users 
                WHERE user_id NOT IN (
                    SELECT user_id 
                    FROM user_activity_logs 
                    WHERE request_time > NOW() - INTERVAL '3 months'
                )
                """
            )
            inactive_percent = round((inactive_count['count'] / total_users['count']) * 100, 2)

            subscribed_count = await self.db.fetchrow(
                """
                SELECT COUNT(DISTINCT user_id)
                FROM (
                    SELECT 
                        user_id,
                        request_type,
                        ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY request_time DESC) AS rn
                    FROM user_activity_logs
                    WHERE request_type IN ('subscribe', 'unsubscribe')
                ) AS sub
                WHERE rn = 1 AND request_type = 'subscribe'
                """
            )

            return {
                "total_users": total_users['count'],
                "inactive_percent": inactive_percent,
                "subscribed_users": subscribed_count['count'],
            }

        except Exception as exc:
            logger.error(f"Ошибка получения статистики: {exc}")
            return {
                "total_users": 0,
                "inactive_percent": 0.0,
                "subscribed_users": 0,
            }

    async def get_theme_id(
            self,
            theme_name: str,
            subtheme_name: str
    ) -> Optional[int]:
        """
        Получение ID темы по названию темы и подтемы.

        :param theme_name: Название общей темы (например, 'Физика')
        :param subtheme_name: Конкретная подтема (например, 'Квантовая механика')
        :return: ID темы или None, если не найдено
        """
        try:
            result = await self.db.fetchrow(
                """
                SELECT 
                    theme_id 
                FROM themes 
                WHERE theme_name = $1 
                    AND specific_theme = $2
                """,
                theme_name,
                subtheme_name
            )
            return result["theme_id"] if result else None

        except Exception as exc:
            logger.error(f"Ошибка получения theme_id для {theme_name}/{subtheme_name}: {exc}")
            return None

    async def upload_data(self, file_path: str) -> bool:
        """
        Загрузка данных из Excel-файла в базу данных.

        :param file_path: Путь к Excel-файлу с данными
        :return: True при успешной загрузке, False при ошибке
        """
        try:
            experts = pd.read_excel(
                file_path,
                names=[
                    "expert_name",
                    "expert_position",
                    "general_theme",
                    "specific_theme",
                    "book_name",
                    "description",
                ],
            ).dropna(subset=["expert_name"])

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

            async with self.db.pool.acquire() as conn:
                async with conn.transaction():
                    for _, row in grouped.iterrows():
                        expert_key = (row['expert_name'].strip(), row['expert_position'].strip())
                        if expert_key not in cache['experts']:
                            expert_id = await conn.fetchval(
                                """
                                INSERT INTO experts (expert_name, expert_position)
                                VALUES ($1, $2)
                                ON CONFLICT (expert_name, expert_position) DO NOTHING
                                RETURNING expert_id
                                """,
                                *expert_key
                            )
                            if not expert_id:
                                expert_id = await conn.fetchval(
                                    "SELECT expert_id FROM experts WHERE expert_name = $1 AND expert_position = $2",
                                    *expert_key
                                )
                            cache['experts'][expert_key] = expert_id

                        theme_key = (row['general_theme'].strip(), row['specific_theme'].strip())
                        if theme_key not in cache['themes']:
                            theme_id = await conn.fetchval(
                                """
                                INSERT INTO themes (theme_name, specific_theme)
                                VALUES ($1, $2)
                                ON CONFLICT (theme_name, specific_theme) DO NOTHING
                                RETURNING theme_id
                                """,
                                *theme_key
                            )
                            if not theme_id:
                                theme_id = await conn.fetchval(
                                    "SELECT theme_id FROM themes WHERE theme_name = $1 AND specific_theme = $2",
                                    *theme_key
                                )
                            cache['themes'][theme_key] = theme_id

                        for book_name, description in zip(row['book_name'], row['description']):
                            book_name = book_name.strip()
                            if book_name not in cache['books']:
                                book_id = await conn.fetchval(
                                    """
                                    INSERT INTO books (book_name)
                                    VALUES ($1)
                                    ON CONFLICT (book_name) DO NOTHING
                                    RETURNING book_id
                                    """,
                                    book_name
                                )
                                if not book_id:
                                    book_id = await conn.fetchval(
                                        "SELECT book_id FROM books WHERE book_name = $1",
                                        book_name
                                    )
                                cache['books'][book_name] = book_id

                            await conn.execute(
                                """
                                INSERT INTO experts_recommendations 
                                (expert_id, theme_id, book_id, description)
                                VALUES ($1, $2, $3, $4)
                                ON CONFLICT DO NOTHING
                                """,
                                cache['experts'][expert_key],
                                cache['themes'][theme_key],
                                cache['books'][book_name],
                                description.strip()
                            )
            return True
        except Exception as e:
            logger.error(f"Ошибка загрузки данных: {e}")
            return False

    async def delete_book(self, book_name: str) -> bool:
        """
        Удаление книги по названию.

        :param book_name: Название книги для удаления
        :return: True при успешном удалении, False при ошибке или если книга не найдена
        """
        try:
            async with self.db.pool.acquire() as conn:
                async with conn.transaction():
                    await conn.execute(
                        """
                        DELETE FROM experts_recommendations 
                        WHERE book_id IN (
                            SELECT book_id FROM books WHERE book_name = $1
                        )
                        """,
                        book_name
                    )
                    
                    result = await conn.execute(
                        """
                        DELETE FROM books 
                        WHERE book_name = $1
                        """,
                        book_name
                    )
                    await conn.execute(
                        """
                        DELETE FROM themes
                        WHERE theme_id NOT IN (
                            SELECT theme_id FROM experts_recommendations
                        )
                        """
                    )
                    if result == "DELETE 0":
                        logger.warning(f"Книга '{book_name}' не найдена")
                        return False
                    logger.info(f"Книга '{book_name}' успешно удалена")
                    return True
        except Exception as exc:
            logger.error(f"Ошибка при удалении книги '{book_name}': {exc}")
            return False

    async def delete_selection(self, theme_name: str, subtheme_name: str) -> bool:
        """
        Удаление подборки по названию темы и подтемы.

        :param theme_name: Название общей темы
        :param subtheme_name: Название подтемы
        :return: True при успешном удалении, False при ошибке или если подборка не найдена
        """
        try:
            async with self.db.pool.acquire() as conn:
                async with conn.transaction():
                    await conn.execute(
                        """
                        DELETE FROM experts_recommendations 
                        WHERE theme_id IN (
                            SELECT theme_id FROM themes 
                            WHERE theme_name = $1 AND specific_theme = $2
                        )
                        """,
                        theme_name, subtheme_name
                    )
                    result = await conn.execute(
                        """
                        DELETE FROM themes 
                        WHERE theme_name = $1 AND specific_theme = $2
                        """,
                        theme_name, subtheme_name
                    )
                    if result == "DELETE 0":
                        logger.warning(f"Подборка '{theme_name}/{subtheme_name}' не найдена")
                        return False
                    logger.info(f"Подборка '{theme_name}/{subtheme_name}' успешно удалена")
                    return True
        except Exception as exc:
            logger.error(f"Ошибка при удалении подборки '{theme_name}/{subtheme_name}': {exc}")
            return False

    async def delete_expert(self, expert_name: str, expert_position: str) -> bool:
        """
        Удаление эксперта по имени и должности.

        :param expert_name: Имя эксперта
        :param expert_position: Должность эксперта
        :return: True при успешном удалении, False при ошибке или если эксперт не найден
        """
        try:
            async with self.db.pool.acquire() as conn:
                async with conn.transaction():
                    await conn.execute(
                        """
                        DELETE FROM experts_recommendations 
                        WHERE expert_id IN (
                            SELECT expert_id FROM experts 
                            WHERE expert_name = $1 AND expert_position = $2
                        )
                        """,
                        expert_name, expert_position
                    )
                    result = await conn.execute(
                        """
                        DELETE FROM experts 
                        WHERE expert_name = $1 AND expert_position = $2
                        """,
                        expert_name, expert_position
                    )
                    await conn.execute(
                    """
                    DELETE FROM themes
                    WHERE theme_id NOT IN (
                        SELECT theme_id FROM experts_recommendations
                    )
                    """
                )
                    if result == "DELETE 0":
                        logger.warning(f"Эксперт '{expert_name}, {expert_position}' не найден")
                        return False
                    logger.info(f"Эксперт '{expert_name}, {expert_position}' успешно удален")
                    return True
        except Exception as exc:
            logger.error(f"Ошибка при удалении эксперта '{expert_name}, {expert_position}': {exc}")
            return False

    async def get_subscribed_users(self) -> List[int]:
        """
        Получение списка ID подписанных пользователей.

        :return: Список ID пользователей, у которых последняя активность 'subscribe'
        """
        try:
            result = await self.db.fetch(
                """
                SELECT DISTINCT user_id
                FROM (
                    SELECT 
                        user_id,
                        request_type,
                        ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY request_time DESC) AS rn
                    FROM user_activity_logs
                    WHERE request_type IN ('subscribe', 'unsubscribe')
                ) AS sub
                WHERE rn = 1 AND request_type = 'subscribe'
                """
            )
            return [row['user_id'] for row in result]
        except Exception as exc:
            logger.error(f"Ошибка при получении списка подписанных пользователей: {exc}")
            return []
        
    async def get_available_experts(self) -> List[List[str]]:
        """Получение списка экспертов + должностей
            return: [[имя, должность]...]
        """

        try:
            result = await self.db.fetch(
                """
                SELECT 
                    expert_name, expert_position
                FROM experts
                ORDER BY expert_name
                """
            )
            return [[row['expert_name'], row['expert_position']] for row in result]

        except Exception as exc:
            logger.error(f"Ошибка получения тем: {exc}")
            return []

    async def is_subscribed(
            self,
            user_id: int
            ) -> bool:
        """
        Проверка, подписан ли пользователь на рассылку.
        Последняя активность должна быть 'subscribe' для подписки.
        """
        try:
            result = await self.db.fetchrow(
                """
                SELECT 
                    request_type 
                FROM user_activity_logs 
                WHERE user_id = $1 AND request_type IN ('subscribe', 'unsubscribe') 
                ORDER BY request_time DESC 
                LIMIT 1
                """,
                user_id
            )

            if result and result['request_type'] == 'subscribe':
                return True

            return False

        except Exception as exc:
            logger.error(f"Ошибка при проверке подписки пользователя {user_id}: {exc}")
            return False

    async def assign_admin_role(
            self,
            user_id: int
    ) -> None:
        """
        Обновляет статус пользователя
        """
        await self.db.execute(
            """
            UPDATE users
            SET role='admin'
            WHERE user_id=$1
            """,
            user_id
        )

    async def is_user_channel_member(self, user_id: int) -> bool:
        """
        Проверяет, является ли пользователь участником каналов.
        """
        try:
            chat_member_spbu = await self.bot.get_chat_member(chat_id=config('CHANNEL_SPBU_ID'), user_id=user_id)
            chat_member_landau = await self.bot.get_chat_member(chat_id=config('CHANNEL_LANDAU_ID'), user_id=user_id)
            return chat_member_spbu.status in [
                ChatMemberStatus.MEMBER,
                ChatMemberStatus.ADMINISTRATOR,
                ChatMemberStatus.CREATOR
            ] and chat_member_landau.status in [
                ChatMemberStatus.MEMBER,
                ChatMemberStatus.ADMINISTRATOR,
                ChatMemberStatus.CREATOR
            ]
        except TelegramForbiddenError:
            logger.info(f"Бот не является членом или не имеет прав администратора в каналах.")
            return False
        except TelegramBadRequest as e:
            logger.warning(
                f"Не удалось получить информацию о членстве пользователя {user_id} в каналах: {e}")
            return False
        except Exception as e:
            logger.error(f"Неизвестная ошибка при проверке членства пользователя {user_id} в каналах: {e}")
            return False
