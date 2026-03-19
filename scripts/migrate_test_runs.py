"""Миграция: создать таблицу test_runs для хранения результатов авто-тестов."""
import os
import psycopg2

conn = psycopg2.connect(os.environ["DATABASE_URL"])
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS test_runs (
    id          SERIAL PRIMARY KEY,
    ran_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    duration_s  FLOAT NOT NULL DEFAULT 0,
    total       INTEGER NOT NULL DEFAULT 0,
    passed      INTEGER NOT NULL DEFAULT 0,
    failed      INTEGER NOT NULL DEFAULT 0,
    results     JSONB NOT NULL DEFAULT '[]',
    summary     TEXT
);
""")

conn.commit()
conn.close()
print("test_runs table — OK")
