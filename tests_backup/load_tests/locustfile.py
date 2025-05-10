from locust import HttpUser, task, between

class TelegramBotUser(HttpUser):
    wait_time = between(1, 5)

    @task
    def start_command(self):
        # Симуляция отправки команды /start через Telegram API
        self.client.post("/bot<YOUR_BOT_TOKEN>/sendMessage", json={
            "chat_id": 12345,
            "text": "/start"
        })

    @task
    def select_topic(self):
        self.client.post("/bot<YOUR_BOT_TOKEN>/sendMessage", json={
            "chat_id": 12345,
            "text": "История"  # Симуляция выбора темы
        })