# Telegram-бот для сбора статистики и продвижения

## Описание проекта

Телеграм-бот предназначен для упрощения поиска качественной литературы на основе экспертных подборок и рекомендательной системы, а также для продвижения Telegram-каналов СПбГУ. Бот предоставляет:

* **Подборки от экспертов** по заранее заданным темам и специальным темам.
* **Персонализированные рекомендации** с использованием модели BERT для анализа взаимодействия пользователей.
* **Административную панель** для управления контентом, просмотра статистики, добавления и удаления администраторов, загрузки новых подборок и удаления устаревших данных.
* **Сбор статистики** о пользователях: общее число, процент неактивных (не заходили более 30 минут), число подписавшихся/отписавшихся, месячная активность (WAU), процент повторных обращений.
* **Обязательную подписку** на каналы «Что там в СПбГУ» и «Ландау позвонит» для доступа к основному функционалу.

## Ключевые технологии

* Python 3.9, Aiogram (асинхронная библиотека для Telegram Bot API)
* Flask для сервера
* PostgreSQL в качестве СУБД
* asyncpg для асинхронного взаимодействия с БД
* SentenceTransformers + PyTorch для рекомендательной системы (BERT + косинусное расстояние)
* APScheduler для периодических задач (резервное копирование, сохранение статистики, проверка статуса)
* Docker + Docker Compose для локальной разработки и развёртывания

## Структура проекта

```text
my_telegram_bot/
├── aiogram_run.py               # Точка входа для запуска Telegram-бота
├── create_bot.py                # Инициализация бота, загрузка администраторов, задачи планировщика
├── server.py                    # Запуск сервера (Flask)
├── Dockerfile                   # Описание образа для Python-приложений (бот и web)
├── requirements.txt             # Список зависимостей Python
├── docker-compose.yml           # Описание сервисов: db, bot, web
├── .env                         # Переменные окружения (PG_USER, PG_PASSWORD, PG_DB, BOT_TOKEN, ADMINS и др.)
├── handlers/                    # Папка с маршрутизаторами хэндлеров (main_panel, admin_panel)
│   ├── main_panel           
│   │  ├───── __init__.py
│   │  ├───── callbacks.py
│   │  ├───── lists.py   
│   │  ├───── menu.py    
│   │  ├───── newsletter.py
│   │  ├───── recommendation.py 
│   │  ├───── start.py           
│   │  └───── subscription.py
│   └── admin_panel.py    
│      ├───── __init__.py
│      ├───── add_admin.py
│      ├───── broadcast.py   
│      ├───── data_upload.py    
│      ├───── delete_book.py
│      ├───── delete_expert.py 
│      ├───── delete_subtheme.py           
│      ├───── menu.py
│      ├───── states.py
│      └───── stats.py   
├── keyboards/                   # Определение клавиатур
│   └── all_keyboards.py
└── db_handler/                  # Логика работы с БД
    ├── db_setup.py              # Инициализация схемы, миграции
    ├── db_utils.py              # Методы для получения статистики, работы с пользователями и админами
    ├── db_class.py              # Класс методов, для более чистого кода
    └── data/                    # Папка для бэкапов и CSV-файлов со статистикой
```

## Начало работы

### Предварительные требования

1. Установлен Docker и Docker Compose.
2. Наличие файла `.env` в корне проекта с заполненными переменными окружения.
3. Для локального запуска (без Docker) необходим Python ≥3.9 и установленный PostgreSQL.
4. После окончания всех тестов в файле по пути `handlers\start.py` надо заменить строки 23-24
для корректной проверки подписки пользователя на каналы СПбГУ (обязательно, чтобы бот был администратором каналов):
```bash
- # is_spbu_member = await db_utils.is_user_channel_member(user_id)  # До вывода в прод лучше закоммитить функцию
- is_spbu_member = True

+ is_spbu_member = await db_utils.is_user_channel_member(user_id)  # До вывода в прод лучше закоммитить функцию
```
5. При необходимости можно вернуть функцию рассылки. Для этого нужно раскомментировать 37 строчку `aiogram_run.py`,
21 строчку в `handlers\admin_panel\__init__.py`, 14 строчку в `handlers\main_panel\__init__.py`.

### Переменные окружения (`.env`)

```text
# .env

# PostgreSQL
PG_USER=my_pg_user
PG_PASSWORD=my_pg_password
PG_DB=my_database
PG_HOST=db  # Для запуска с Docker'ом, иначе localhost
PG_PORT=5432  # В локальном запуске можно использовать свой порт

# Telegram Bot
TOKEN=your_bot_token
ADMINS=список_ID_админов_через_запятую

# Веб-сервер (если используется)
SERVER_PORT=8000

# ID Telegram каналов СПбГУ
CHANNEL_SPBU_ID=-1001752627981
CHANNEL_LANDAU_ID=-1001273779592
```

### Запуск с помощью Docker Compose

1. Перейдите в корневую папку проекта:

   ```bash
   cd path/to/my_telegram_bot
   ```
2. Постройте (или обновите) образы и запустите сервисы в фоновом режиме:

   ```bash
   docker-compose up -d --build
   ```
3. Проверьте, что контейнеры запущены:

   ```bash
   docker-compose ps
   ```
4. Проверьте логи бота:

   ```bash
   docker-compose logs -f bot
   ```
5. Для остановки и удаления контейнеров:

   ```bash
   docker-compose down
   ```
6. Для полного сброса БД (удаление volume `pgdata`):

   ```bash
   docker-compose down -v
   ```

### Локальный запуск без Docker

> **Только при установленном локальном PostgreSQL**

1. Установите Python-зависимости:

   ```bash
   pip install -r requirements.txt
   ```
2. Убедитесь, что в `.env` указана `PG_HOST=localhost`.
3. Запустите бот:

   ```bash
   python aiogram_run.py
   ```

## Основные возможности бота

### Навигация

* При вводе `/start` бот проверяет подписку на каналы СПбГУ. Если подписка отсутствует, вы получаете сообщение с призывом подписаться.
* После подписки появляются кнопки:

  * «Подборки от экспертов»
  * «Рекомендации»
  * «Подписаться на рассылку» (скрыта)
  * (для администраторов) «Админ панель»

### Подборки от экспертов

1. Пользователь выбирает тему и (если доступно) конкретного эксперта.
2. Бот выводит список книг с названием и кратким описанием (при наличии).
3. Можно вернуться назад или выйти в главное меню.

### Рекомендации (ИИ-система)

1. Пользователь должен выбрать хотя бы одну подборку (бот хранит до 12 последних взаимодействий).
2. На основе истории взаимодействий применяется модель BERT с косинусным расстоянием: бот подбирает схожие книги.
3. Если история пуста, выводится сообщение-приглашение сначала выбрать подборку от эксперта.

### Админ-панель

Эта кнопка видна только тем пользователям, чей `user_id` содержится в таблице `admins`.

#### 1. Статистика

* **Общее число пользователей**
* **Процент неактивных пользователей** (не заходили более 30 минут)
* **Число подписавшихся/отписавшихся**
* **Активные пользователи за неделю (WAU, Weekly Active Users)**
* **Процент повторных обращений** (повторное использование спустя ≥30 минут)

#### 2. Загрузка данных

* Администратор загружает новые экспертные подборки через специально отформатированный файл (.xlsx/.xls).
* Формат данных: тема, спецтема, эксперт, список книг.

#### 3. Удаление данных

* Удаление книги: удаляется сама книга и связи (`experts_recommendation`).
* Удаление подборки: удаляется только запись подборки (книга остаётся в БД, если привязана к другим подборкам).
* Удаление эксперта: удаляется эксперт и все его подборки.
* Бот запрашивает подтверждение перед финальным удалением.

#### 4. Добавление администратора

* Администратор вводит `user_id` нового admin (он должен быть зарегистрирован в боте).
* Если `user_id` отсутствует в `users`, бот выдаёт ошибку.
* После добавления бот автоматически обновляет глобальный список `admins` (вызов `update_admins`).

#### 5. Рассылка (скрыта):

* Администратор вводит сообщение для рассылки (принимает текст, фото).
* Приходит сообщение для подтверждения рассылки.
* После отправки бот сообщает успешность проведения рассылки. 

## Планировщик задач (APScheduler)

В `create_bot.py` определены следующие задачи:

1. `save_stats(db_utils)` — ежедневно в 04:00 собирает статистику и записывает в `db_handler/data/stats.csv`.
2. `check_users_status_task(db_utils)` — ежедневно в 04:01 проверяет статусы пользователей (интервалы, блокировки).
3. `create_backup()` — ежедневно в 04:02 создаёт дамп базы данных и сохраняет в `db_handler/data/backup_<timestamp>.sql`.

## Разработка и отладка

```bash
# После изменения кода хэндлеров/логики:
docker-compose restart bot
```

---

Автор: Команда Cтудентов СПбГУ
2025
