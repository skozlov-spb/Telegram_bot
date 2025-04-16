import logging
from typing import List, Optional
from .db_class import Database
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ALLOWED_ACTIVITIES = [
    'start_bot', 
    'get_expert_recommendation', 
    'subscribe',
    'unsubscribe',
    'get_recomendation'
    'check_subscription'
]
CHANNEL_SPBU_ID = -1001752627981
CHANNEL_LANDAU_ID = -1001273779592

class DBUtils:
    
    #инициализация - не асинхронная, если будут проблемы, надо будет исправить
    def __init__(self, db: Database, bot):
        self.db = db
        self.bot = bot
        
        

    async def check_user_subscription(self, user_id: int, channel_id: int) -> bool:
        """Проверка подписки пользователя на канал"""
        try:
            chat_member = await self.bot.get_chat_member(chat_id=channel_id, user_id=user_id) #бот должен быть администратором
            return chat_member.status in ['member', 'administrator', 'creator']
        except Exception as e:
            logger.error(f"Ошибка проверки подписки: {e}")
            return False
        
        

    async def register_user(self, user_id: int, username: str) -> bool:
        """
        Регистрация/проверка пользователя в БД
        :param user_id: ID пользователя Telegram
        :param username: Имя пользователя (или полное имя)
        :return: True если пользователь УЖЕ был зарегистрирован, False если был зарегистрирован только что
        """
        try:
            result = await self.db.query(
                """
                INSERT INTO users (user_id, username, registration_date) 
                VALUES ($1, $2, NOW() AT TIME ZONE 'Europe/Moscow')
                ON CONFLICT (user_id) DO UPDATE SET username = EXCLUDED.username
                RETURNING (xmax = 0) AS is_new
                """,
                (user_id, username),
                fetch=True
            )
            
            is_new = result[0]['is_new'] if result else False
            
            if is_new:
                logger.info(f"Пользователь уже существует: {username} (ID: {user_id})")
                return False
            else:
                logger.info(f"Зарегистрирован новый пользователь: {username} (ID: {user_id})")
                await self.log_user_activity(user_id, 'use_bot')
                return True 
        except Exception as e:
            logger.error(f"Ошибка регистрации пользователя: {e}")
            return False  # Если не получилось - все равно True
        
        

    async def log_user_activity(self, user_id: int, activity_type: str, theme_id: Optional[int] = None) -> bool:
        """Логирование активности пользователя"""
        try:
            if activity_type not in ALLOWED_ACTIVITIES:
                logger.error(f"Недопустимый тип активности: {activity_type}")
                return False
            await self.db.query(
                """INSERT INTO user_activity_logs (user_id, request_type, theme_id) 
                VALUES (%s, %s, %s)""",
                (user_id, activity_type, theme_id)
            )
            return True
        except Exception as e:
            logger.error(f"Ошибка логирования активности: {e}")
            return False
        
        

    async def get_available_themes(self) -> List[str]:
        """Получение списка уникальных названий тем"""
        try:
            result = await self.db.query(
                "SELECT DISTINCT theme_name FROM themes ORDER BY theme_name",
                fetch=True
            )
            return [row['theme_name'] for row in result]  # Извлекаем только названия
        except Exception as e:
            logger.error(f"Ошибка получения тем: {e}")
            return []
        
        
        
    async def get_subthemes(self, theme_name: str) -> List[str]:
        """Получаем список подтем для кнопок"""
        try:
            result = await self.db.query(
                """SELECT specific_theme 
                FROM themes 
                WHERE theme_name = $1 
                ORDER BY specific_theme""",
                (theme_name,),
                fetch=True
            )
            return [row['specific_theme'] for row in result]
        except Exception as e:
            logger.error(f"Ошибка получения подтем: {e}")
            return []
        
        
        
    async def get_expert_recommendations(self, subtheme_name: int) -> Optional[str]:
        """Получение рекомендаций экспертов по подтеме
        return словарь - id_книги -> (название книги, автор книги, имя эксперта, должность эксперта, описание от эксперта)"""
        try:
            recommendations = await self.db.query(
                """SELECT b.book_id, b.book_name, 
                        e.expert_name, e.expert_position, er.description
                FROM experts_recommendations er
                JOIN books b ON er.book_id = b.book_id
                JOIN experts e ON er.expert_id = e.expert_id
                JOIN themes t ON er.theme_id = t.theme_id
                WHERE t.specific_theme = $1""",
                (subtheme_name,),
                fetch=True
            )
            
            if not recommendations:
                return None
            
            return {
                row['book_id']: {
                    "book_name": row['book_name'],
                    "expert_name": row['expert_name'],
                    "expert_position": row['expert_position'],
                    "description": row['description']
                }
                for row in recommendations
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения рекомендаций для подтемы '{subtheme_name}': {e}")
            return None
        
        
        
    async def is_subscribed(self, user_id: int) -> bool:
            """
            Проверка, подписан ли пользователь на рассылку.
            Последняя активность должна быть 'subscribe' для подписки.
            """
            try:
                result = await self.db.query(
                    """
                    SELECT request_type 
                    FROM user_activity_logs 
                    WHERE user_id = $1 AND request_type IN ('subscribe', 'unsubscribe') 
                    ORDER BY request_time DESC 
                    LIMIT 1
                    """,
                    (user_id,),
                    fetch=True
                )

                if result and result[0]['request_type'] == 'subscribe':
                    return True
                return False
            except Exception as e:
                logger.error(f"Ошибка при проверке подписки пользователя {user_id}: {e}")
                return False
            
            

    async def is_active(self, user_id: int) -> bool:
        """
        Пользователь считается активным, если его последняя активность была не более 3 месяцев назад.
        """
        try:
            result = await self.db.query(
                """
                SELECT request_time 
                FROM user_activity_logs 
                WHERE user_id = $1 
                ORDER BY request_time DESC 
                LIMIT 1
                """,
                (user_id,),
                fetch=True
            )

            if not result:
                return False

            last_activity = result[0]['request_time']
            three_months_ago = datetime.now() - timedelta(days=90)
            return last_activity > three_months_ago
        except Exception as e:
            logger.error(f"Ошибка при проверке активности пользователя {user_id}: {e}")
            return False
        
        

    async def get_statistic(self) -> dict:
        """
        Получение статистики:
        1. Общее число пользователей
        2. Процент неактивных пользователей
        3. Число подписанных на рассылку
        """
        try:
            users = await self.db.query("SELECT user_id FROM users", fetch=True)
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

        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return {
                "total_users": 0,
                "inactive_percent": 0.0,
                "subscribed_users": 0
            }
