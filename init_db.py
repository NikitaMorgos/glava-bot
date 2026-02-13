"""
Скрипт создания таблиц в облачной PostgreSQL.
Запусти один раз после того, как создашь базу в Neon/Supabase и укажешь DATABASE_URL в .env.

Запуск: python init_db.py
"""

import os
import sys

# Загружаем .env и config — используем ТУ ЖЕ строку подключения, что и бот
from dotenv import load_dotenv
load_dotenv()

import config
import psycopg2

DATABASE_URL = config.DATABASE_URL
# Читаем SQL-скрипт
script_path = os.path.join(os.path.dirname(__file__), "sql", "init_db.sql")
with open(script_path, encoding="utf-8") as f:
    sql = f.read()

# Убираем комментарии и пустые строки, выполняем по одному запросу
# (некоторые облака не любят несколько запросов в одном execute)
queries = [
    q.strip() for q in sql.split(";")
    if q.strip() and not q.strip().startswith("--")
]

conn = psycopg2.connect(DATABASE_URL)
try:
    with conn.cursor() as cur:
        for i, query in enumerate(queries):
            if not query:
                continue
            try:
                cur.execute(query)
            except psycopg2.Error as e:
                if "already exists" in str(e):
                    pass  # Уже создано — пропускаем
                else:
                    print(f"Ошибка в запросе {i+1}: {query[:80]}...")
                    raise
    conn.commit()
    print("Таблицы успешно созданы.")
except psycopg2.Error as e:
    conn.rollback()
    print(f"Ошибка: {e}")
    sys.exit(1)
finally:
    conn.close()
