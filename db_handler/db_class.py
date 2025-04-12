import psycopg2
from decouple import config


class Database:
    def __init__(self):
        self.conn = psycopg2.connect(
            host=config("PG_HOST"),
            dbname=config("PG_DB"),
            user=config("PG_USER"),
            password=config("PG_PASSWORD"),
            port=config("PG_PORT")
        )
        self.conn.autocommit = True

    def query(self, query):
        cur = self.conn.cursor()
        cur.execute(query)

        cur.close()

    def close(self):
        self.conn.close()
