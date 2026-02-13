"""
Проверка БД — видит ли приложение таблицы.
Использует ТОЧНО ту же строку подключения, что и бот.
"""
from dotenv import load_dotenv
load_dotenv()

import config
import psycopg2

url = config.DATABASE_URL
if not url:
    print("DATABASE_URL не задан")
    exit(1)

print("Подключение:", url.split("@")[1].split("/")[0] if "@" in url else "скрыто")
conn = psycopg2.connect(url)
cur = conn.cursor()

# Проверяем, есть ли таблица users
cur.execute("""
    SELECT table_name FROM information_schema.tables 
    WHERE table_schema = 'public' AND table_name IN ('users', 'voice_messages')
""")
tables = cur.fetchall()
print("Таблицы в public:", [t[0] for t in tables])

if not tables:
    print("Таблиц нет! Создаём...")
    with open("sql/init_db.sql", encoding="utf-8") as f:
        sql = f.read()
    for q in (q.strip() for q in sql.split(";") if q.strip() and not q.strip().startswith("--")):
        if q:
            try:
                cur.execute(q)
            except Exception as e:
                if "already exists" not in str(e):
                    print("Ошибка:", e)
    conn.commit()
    print("Готово. Запусти check_db.py снова для проверки.")
else:
    cur.execute("SELECT COUNT(*) FROM users")
    print("Записей в users:", cur.fetchone()[0])

cur.close()
conn.close()
