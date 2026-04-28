"""
Миграция БД: промо-коды.
Создаёт таблицы promo_codes, promo_usages.
Добавляет столбцы promo_code_id и discount_amount в draft_orders.
Запуск: python scripts/migrate_promo.py
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
    # Таблица промо-кодов
    """
    CREATE TABLE IF NOT EXISTS promo_codes (
        id                SERIAL PRIMARY KEY,
        code              VARCHAR(50) UNIQUE NOT NULL,
        type              VARCHAR(20) NOT NULL DEFAULT 'general',
        discount_type     VARCHAR(10) NOT NULL DEFAULT 'percent',
        discount_value    NUMERIC(10,2) NOT NULL,
        max_uses          INT,
        used_count        INT NOT NULL DEFAULT 0,
        expires_at        TIMESTAMP,
        assigned_user_id  INT REFERENCES users(id) ON DELETE SET NULL,
        sent_at           TIMESTAMP,
        created_by        VARCHAR(50),
        created_at        TIMESTAMP NOT NULL DEFAULT NOW(),
        is_active         BOOLEAN NOT NULL DEFAULT TRUE
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_promo_codes_code ON promo_codes(code)",
    "CREATE INDEX IF NOT EXISTS idx_promo_codes_user ON promo_codes(assigned_user_id)",
    "CREATE INDEX IF NOT EXISTS idx_promo_codes_active ON promo_codes(is_active, expires_at)",

    # Таблица применений промо-кодов
    """
    CREATE TABLE IF NOT EXISTS promo_usages (
        id               SERIAL PRIMARY KEY,
        promo_id         INT NOT NULL REFERENCES promo_codes(id) ON DELETE CASCADE,
        user_id          INT REFERENCES users(id) ON DELETE SET NULL,
        draft_id         INT REFERENCES draft_orders(id) ON DELETE SET NULL,
        discount_amount  INT NOT NULL,
        used_at          TIMESTAMP NOT NULL DEFAULT NOW()
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_promo_usages_promo ON promo_usages(promo_id)",
    "CREATE INDEX IF NOT EXISTS idx_promo_usages_user ON promo_usages(user_id)",

    # Столбцы в draft_orders
    """
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'draft_orders' AND column_name = 'promo_code_id'
        ) THEN
            ALTER TABLE draft_orders ADD COLUMN promo_code_id INT REFERENCES promo_codes(id) ON DELETE SET NULL;
        END IF;
    END $$
    """,
    """
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'draft_orders' AND column_name = 'discount_amount'
        ) THEN
            ALTER TABLE draft_orders ADD COLUMN discount_amount INT NOT NULL DEFAULT 0;
        END IF;
    END $$
    """,
]


def run():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    for i, sql in enumerate(MIGRATIONS, 1):
        try:
            cur.execute(sql)
            conn.commit()
            print(f"  [{i}/{len(MIGRATIONS)}] OK")
        except Exception as e:
            conn.rollback()
            print(f"  [{i}/{len(MIGRATIONS)}] ERROR: {e}")
    cur.close()
    conn.close()
    print("Миграция промо-кодов завершена.")


if __name__ == "__main__":
    print(f"Подключение к БД: {DB_URL[:40]}...")
    run()
