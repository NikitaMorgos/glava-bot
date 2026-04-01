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
    ("Эквайринг", 5),
    ("Налоги", 6),
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

        # Удаляем ошибочный тестовый сид 1000 ₽ (реальная выручка в ЮKassa — 30 ₽ за 3 платежа)
        cur.execute("""
            DELETE FROM finance_income
            WHERE created_by = 'migrate'
              AND amount = 1000.00
              AND COALESCE(title, '') = 'тестовая выручка'
              AND date = '2026-03-15'
        """)

        # Поступления по ЮKassa за март 2026 (как в личном кабинете): заказы #6, #7, #8
        income_rows = [
            ("2026-03-17", "10.00", "GLAVA — заказ #6", "314a9ef6-000f-5001-8000-1406cdf20e0e"),
            ("2026-03-17", "10.00", "GLAVA — заказ #7", "314b8350-000f-5001-9000-1fcf556b6791"),
            ("2026-03-19", "10.00", "GLAVA — заказ #8", "314e32c7-000f-5001-9000-10441192f04a"),
        ]
        for d, amt, title, yk_id in income_rows:
            cur.execute("""
                INSERT INTO finance_income (date, amount, title, source, comment, created_by)
                SELECT %s::date, %s::numeric, %s, 'ЮKassa', %s, 'migrate'
                WHERE NOT EXISTS (
                    SELECT 1 FROM finance_income
                    WHERE comment = %s OR (date = %s::date AND title = %s AND amount = %s::numeric)
                )
            """, (d, amt, title, yk_id, yk_id, d, title, amt))

        # Затраты по отчёту ЮKassa за март 2026: комиссия и НДС
        cur.execute("""
            INSERT INTO expenses
                (date, amount, category_id, initiator_id, periodicity, behavior, title, comment, created_by)
            SELECT '2026-03-31'::date, 1.05, c.id, i.id, 'разовая', 'переменная',
                   'Комиссия ЮKassa (март 2026)', 'по данным ЛК ЮKassa за период 01.03—31.03.2026', 'migrate'
            FROM expense_categories c, expense_initiators i
            WHERE c.name = 'Эквайринг' AND i.name = 'dev'
              AND NOT EXISTS (
                  SELECT 1 FROM expenses e
                  JOIN expense_categories ec ON ec.id = e.category_id
                  WHERE ec.name = 'Эквайринг'
                    AND e.title = 'Комиссия ЮKassa (март 2026)'
                    AND TO_CHAR(e.date, 'YYYY-MM') = '2026-03'
              )
        """)
        cur.execute("""
            INSERT INTO expenses
                (date, amount, category_id, initiator_id, periodicity, behavior, title, comment, created_by)
            SELECT '2026-03-31'::date, 0.24, c.id, i.id, 'разовая', 'переменная',
                   'НДС ЮKassa (март 2026)', 'по данным ЛК ЮKassa за период 01.03—31.03.2026', 'migrate'
            FROM expense_categories c, expense_initiators i
            WHERE c.name = 'Налоги' AND i.name = 'dev'
              AND NOT EXISTS (
                  SELECT 1 FROM expenses e
                  JOIN expense_categories ec ON ec.id = e.category_id
                  WHERE ec.name = 'Налоги'
                    AND e.title = 'НДС ЮKassa (март 2026)'
                    AND TO_CHAR(e.date, 'YYYY-MM') = '2026-03'
              )
        """)
    conn.commit()
    print("✅ Таблицы expense_categories, expense_initiators, expenses, finance_income созданы.")
    print("✅ Базовые категории и инициаторы добавлены.")
finally:
    conn.close()
