"""
Миграция БД для admin-панели.
Создаёт таблицы: prompts, pipeline_jobs, mailings, mailing_recipients, mailing_triggers.
Запуск: python scripts/migrate_admin.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import psycopg2

DB_URL = os.environ.get("DATABASE_URL", "")
if not DB_URL:
    print("ERROR: DATABASE_URL не задан в .env")
    sys.exit(1)

MIGRATIONS = [
    # Промпты 12 агентов
    """
    CREATE TABLE IF NOT EXISTS prompts (
        id          SERIAL PRIMARY KEY,
        role        VARCHAR(50) NOT NULL,
        version     INT NOT NULL DEFAULT 1,
        prompt_text TEXT NOT NULL,
        is_active   BOOLEAN DEFAULT TRUE,
        updated_at  TIMESTAMP DEFAULT NOW(),
        updated_by  VARCHAR(50)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_prompts_role ON prompts(role)",

    # Статусы пайплайна
    """
    CREATE TABLE IF NOT EXISTS pipeline_jobs (
        id               SERIAL PRIMARY KEY,
        telegram_id      BIGINT NOT NULL,
        phase            VARCHAR(10) NOT NULL DEFAULT 'A',
        current_step     VARCHAR(50),
        status           VARCHAR(20) DEFAULT 'pending',
        n8n_execution_id VARCHAR(100),
        started_at       TIMESTAMP DEFAULT NOW(),
        finished_at      TIMESTAMP,
        error            TEXT
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_pjobs_telegram_id ON pipeline_jobs(telegram_id)",

    # Рассылки
    """
    CREATE TABLE IF NOT EXISTS mailings (
        id            SERIAL PRIMARY KEY,
        name          VARCHAR(200),
        template_text TEXT NOT NULL,
        segment       VARCHAR(50) NOT NULL DEFAULT 'all',
        scheduled_at  TIMESTAMP,
        sent_at       TIMESTAMP,
        sent_count    INT DEFAULT 0,
        created_by    VARCHAR(50),
        created_at    TIMESTAMP DEFAULT NOW()
    )
    """,

    # Получатели рассылок
    """
    CREATE TABLE IF NOT EXISTS mailing_recipients (
        id          SERIAL PRIMARY KEY,
        mailing_id  INT REFERENCES mailings(id) ON DELETE CASCADE,
        telegram_id BIGINT NOT NULL,
        status      VARCHAR(20) DEFAULT 'pending',
        sent_at     TIMESTAMP,
        error       TEXT
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_mrecip_mailing ON mailing_recipients(mailing_id)",

    # Триггерные рассылки
    """
    CREATE TABLE IF NOT EXISTS mailing_triggers (
        id            SERIAL PRIMARY KEY,
        name          VARCHAR(200) NOT NULL,
        description   TEXT,
        event_type    VARCHAR(50) NOT NULL,
        template_text TEXT NOT NULL,
        delay_hours   INT DEFAULT 0,
        is_active     BOOLEAN DEFAULT FALSE,
        created_at    TIMESTAMP DEFAULT NOW()
    )
    """,

    # Добавляем колонку step и уникальный индекс (если их ещё нет)
    """
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name='pipeline_jobs' AND column_name='step'
        ) THEN
            ALTER TABLE pipeline_jobs ADD COLUMN step VARCHAR(50);
        END IF;
    END $$
    """,
    """
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint
            WHERE conname = 'pipeline_jobs_telegram_phase_unique'
        ) THEN
            ALTER TABLE pipeline_jobs
                ADD CONSTRAINT pipeline_jobs_telegram_phase_unique
                UNIQUE (telegram_id, phase);
        END IF;
    END $$
    """,

    # Базовые триггеры
    """
    INSERT INTO mailing_triggers (name, description, event_type, template_text, delay_hours, is_active)
    SELECT 'Книга готова', 'Уведомление когда книга готова к отправке', 'book_ready',
           '🎉 Ваша книга готова! Загляните в кабинет чтобы её посмотреть.', 0, FALSE
    WHERE NOT EXISTS (SELECT 1 FROM mailing_triggers WHERE event_type = 'book_ready')
    """,
    """
    INSERT INTO mailing_triggers (name, description, event_type, template_text, delay_hours, is_active)
    SELECT 'Напоминание через 7 дней', 'Напоминание неактивным пользователям', 'inactive_7d',
           '👋 Привет! Вы не заходили к нам давно. Продолжим работу над семейной историей?', 168, FALSE
    WHERE NOT EXISTS (SELECT 1 FROM mailing_triggers WHERE event_type = 'inactive_7d')
    """,
]


def run():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    for i, sql in enumerate(MIGRATIONS):
        try:
            cur.execute(sql)
            conn.commit()
            print(f"  [{i+1}/{len(MIGRATIONS)}] OK")
        except Exception as e:
            conn.rollback()
            print(f"  [{i+1}/{len(MIGRATIONS)}] ERROR: {e}")
    cur.close()
    conn.close()
    print("Миграция завершена.")


if __name__ == "__main__":
    print(f"Подключение к БД: {DB_URL[:40]}...")
    run()
