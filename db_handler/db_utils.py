import logging
from typing import List, Optional, Tuple
from .db_class import Database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DBUtils:
    
    #инициализация - не асинхронная, если будут проблемы, надо будет исправить
    def __init__(self, db: Database, bot):
        self.db = db
        self.bot = bot
        
        

    async def check_user_subscription(self, user_id: int, channel_id: str) -> bool:
        """Проверка подписки пользователя на канал"""
        try:
            chat_member = await self.bot.get_chat_member(chat_id=channel_id, user_id=user_id)
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
            
            if not is_new:
                logger.info(f"Пользователь уже существует: {username} (ID: {user_id})")
                return True
            else:
                logger.info(f"Зарегистрирован новый пользователь: {username} (ID: {user_id})")
                await self.log_user_activity(user_id, 'use_bot')
                return False
                
        except Exception as e:
            logger.error(f"Ошибка регистрации пользователя: {e}")
            return True  # Если не получилось - все равно True
        
        
        

    async def log_user_activity(self, user_id: int, activity_type: str, theme_id: Optional[int] = None) -> bool:
        """Логирование активности пользователя"""
        try:
            self.db.query(
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
                """SELECT b.book_id, b.book_name, b.author, 
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
                    "author": row['author'],
                    "expert_name": row['expert_name'],
                    "expert_position": row['expert_position'],
                    "description": row['description']
                }
                for row in recommendations
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения рекомендаций для подтемы '{subtheme_name}': {e}")
            return None
