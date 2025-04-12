from flask import Flask
from decouple import config


# Создаем сервер
server = Flask(__name__)


def run_flask():
    # Запускаем сервер
    server.run(host=config('PG_PORT'), port=config('SERVER_PORT'), debug=False)
