"""
Создание таблиц — с подробным выводом.
"""
import config
import psycopg2

url = config.DATABASE_URL
# Показываем хост без пароля
host = url.split("@")[1].split("/")[0] if "@" in url else "?"
print("Подключение к:", host)

conn = psycopg2.connect(url)
conn.autocommit = True  # DDL без явного commit
cur = conn.cursor()

sqls = [
    """CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        telegram_id BIGINT UNIQUE NOT NULL,
        username VARCHAR(255),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )""",
    "CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id)",
    """CREATE TABLE IF NOT EXISTS voice_messages (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        telegram_file_id VARCHAR(255) NOT NULL,
        storage_key VARCHAR(512) NOT NULL,
        duration INTEGER,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )""",
    "CREATE INDEX IF NOT EXISTS idx_voice_messages_user_id ON voice_messages(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_voice_messages_created_at ON voice_messages(created_at DESC)",
    """CREATE TABLE IF NOT EXISTS photos (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        telegram_file_id VARCHAR(255) NOT NULL,
        storage_key VARCHAR(512) NOT NULL,
        caption TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )""",
    "CREATE INDEX IF NOT EXISTS idx_photos_user_id ON photos(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_photos_created_at ON photos(created_at DESC)",
    "ALTER TABLE voice_messages ADD COLUMN IF NOT EXISTS transcript TEXT",
]

for i, sql in enumerate(sqls):
    try:
        cur.execute(sql)
        print(f"OK: запрос {i+1}")
    except Exception as e:
        print(f"ОШИБКА запрос {i+1}: {e}")

# Проверка
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name IN ('users','voice_messages','photos')")
tables = cur.fetchall()
print("Таблицы:", [t[0] for t in tables])

cur.close()
conn.close()
print("Готово.")
