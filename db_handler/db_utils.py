import logging
from typing import List, Optional, Dict, Union, Tuple
from datetime import datetime, timedelta

import asyncpg
from asyncpg.pool import Pool

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramAPIError

from .db_class import Database


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ALLOWED_ACTIVITIES = [
    'start_bot',
    'get_expert_recommendation',
    'get_recommendation',
    'subscribe',
    'unsubscribe',
    'presubscribed_spbu_true',
    'presubscribed_landau_true'
]

CHANNEL_SPBU_ID = -1001752627981
CHANNEL_LANDAU_ID = -1001273779592


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

    async def check_user_subscription(
            self,
            user_id: int,
            channel_id: int
    ) -> bool:
        """Проверка подписки пользователя на канал"""

        try:
            # Бот должен быть администратором
            chat_member = await self.bot.get_chat_member(
                chat_id=channel_id,
                user_id=user_id
            )
            is_subscribe = chat_member.status in ['member', 'administrator', 'creator']
            return is_subscribe

        except TelegramBadRequest as exp:
            # Пользователь не подписан
            if "USER_NOT_PARTICIPANT" in str(exp):
                return False

            raise

        except TelegramForbiddenError:
            logger.error(f"Бот не является администратором в чате {channel_id}")
            return False

        except TelegramAPIError as exc:
            logger.error(f"Telegram API error: {exc}")
            raise

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
                    INSERT INTO users (user_id, username, registration_date) 
                    VALUES 
                        ($1, $2, NOW() AT TIME ZONE 'Europe/Moscow')
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
            users = await self.db.fetch(
                """
                SELECT user_id FROM users
                """
            )
            total_users = len(users)

            if total_users == 0:
                return {
                    "total_users": 0,
                    "inactive_percent": 0.0,
                    "subscribed_users": 0
                }

            inactive_count = 0
            subscribed_count = 0

            for user in users:
                user_id = user['user_id']
                if not await self.is_active(user_id):
                    inactive_count += 1
                if await self.is_subscribed(user_id):
                    subscribed_count += 1

            inactive_percent = round((inactive_count / total_users) * 100, 2)

            return {
                "total_users": total_users,
                "inactive_percent": inactive_percent,
                "subscribed_users": subscribed_count
            }

        except Exception as exc:
            logger.error(f"Ошибка получения статистики: {exc}")
            return {
                "total_users": 0,
                "inactive_percent": 0.0,
                "subscribed_users": 0
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