"""
Миграция: создаёт таблицы для раздела «Финансы» в админке.
Запуск: python scripts/migrate_finance.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import psycopg2

db_url = os.environ.get("DATABASE_URL", "")
if not db_url:
    print("ERROR: DATABASE_URL не задан")
    sys.exit(1)

DDL = """
CREATE TABLE IF NOT EXISTS expense_categories (
    id         SERIAL PRIMARY KEY,
    name       TEXT NOT NULL UNIQUE,
    sort_order INT  NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS expense_initiators (
    id         SERIAL PRIMARY KEY,
    name       TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS expenses (
    id            SERIAL PRIMARY KEY,
    date          DATE          NOT NULL,
    amount        NUMERIC(12,2) NOT NULL,
    category_id   INT           NOT NULL REFERENCES expense_categories(id),
    initiator_id  INT           NOT NULL REFERENCES expense_initiators(id),
    periodicity   TEXT          NOT NULL DEFAULT 'разовая' CHECK (periodicity IN ('разовая', 'подписка')),
    behavior      TEXT          NOT NULL DEFAULT 'переменная' CHECK (behavior IN ('постоянная', 'переменная')),
    comment       TEXT,
    created_at    TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    created_by    TEXT
);

-- Добавляем колонки если таблица уже существовала
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='expenses' AND column_name='periodicity') THEN
        ALTER TABLE expenses ADD COLUMN periodicity TEXT NOT NULL DEFAULT 'разовая'
            CHECK (periodicity IN ('разовая', 'подписка'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='expenses' AND column_name='behavior') THEN
        ALTER TABLE expenses ADD COLUMN behavior TEXT NOT NULL DEFAULT 'переменная'
            CHECK (behavior IN ('постоянная', 'переменная'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='expenses' AND column_name='title') THEN
        ALTER TABLE expenses ADD COLUMN title TEXT;
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS finance_income (
    id            SERIAL PRIMARY KEY,
    date          DATE          NOT NULL,
    amount        NUMERIC(12,2) NOT NULL,
    title         TEXT,
    source        TEXT          NOT NULL DEFAULT 'ЮKassa',
    comment       TEXT,
    created_at    TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    created_by    TEXT
);
"""

SEED_CATEGORIES = [
    ("Инфраструктура", 1),
    ("Маркетинг", 2),
    ("Подрядчики", 3),
    ("Офис и прочее", 4),
]

SEED_INITIATORS = ["dev", "dasha", "lena"]

conn = psycopg2.connect(db_url)
try:
    with conn.cursor() as cur:
        cur.execute(DDL)
        for name, order in SEED_CATEGORIES:
            cur.execute("""
                INSERT INTO expense_categories (name, sort_order)
                VALUES (%s, %s) ON CONFLICT (name) DO NOTHING
            """, (name, order))
        for name in SEED_INITIATORS:
            cur.execute("""
                INSERT INTO expense_initiators (name)
                VALUES (%s) ON CONFLICT (name) DO NOTHING
            """, (name,))
        cur.execute("""
            INSERT INTO finance_income (date, amount, title, source, created_by)
            SELECT '2026-03-15'::date, 1000.00, 'тестовая выручка', 'ЮKassa', 'migrate'
            WHERE NOT EXISTS (
                SELECT 1 FROM finance_income
                WHERE TO_CHAR(date, 'YYYY-MM') = '2026-03'
                  AND COALESCE(title, '') = 'тестовая выручка'
                  AND source = 'ЮKassa'
            )
        """)
    conn.commit()
    print("✅ Таблицы expense_categories, expense_initiators, expenses, finance_income созданы.")
    print("✅ Базовые категории и инициаторы добавлены.")
finally:
    conn.close()
