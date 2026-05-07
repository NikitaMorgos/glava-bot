"""
Заносит нулевые записи по ЮKassa за апрель 2026:
- Выручка 0 ₽ (finance_income)
- Комиссия ЮKassa (апрель 2026) 0 ₽ → Эквайринг
- НДС ЮKassa (апрель 2026) 0 ₽ → Налоги
"""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(os.environ["DATABASE_URL"])
cur = conn.cursor()

# ── Категории ───────────────────────────────────────────────────────
cur.execute("SELECT id, name FROM expense_categories WHERE name IN ('Налоги', 'Эквайринг')")
cats = {r[1]: r[0] for r in cur.fetchall()}

for name in ("Налоги", "Эквайринг"):
    if name not in cats:
        cur.execute(
            "INSERT INTO expense_categories (name, sort_order) "
            "VALUES (%s, (SELECT COALESCE(MAX(sort_order),0)+1 FROM expense_categories)) "
            "ON CONFLICT (name) DO NOTHING RETURNING id, name",
            (name,)
        )
        row = cur.fetchone()
        if row:
            cats[row[1]] = row[0]

cur.execute("SELECT id, name FROM expense_categories WHERE name IN ('Налоги', 'Эквайринг')")
cats = {r[1]: r[0] for r in cur.fetchall()}

# ── Инициатор ───────────────────────────────────────────────────────
cur.execute("SELECT id FROM expense_initiators WHERE name = 'dev'")
row = cur.fetchone()
if not row:
    cur.execute("INSERT INTO expense_initiators (name) VALUES ('dev') RETURNING id")
    row = cur.fetchone()
dev_id = row[0]

# ── Расходы: Эквайринг и Налоги за апрель ──────────────────────────
EXPENSES = [
    ("2026-04-30", 0, cats["Эквайринг"], dev_id, "разовая", "постоянная",
     "Комиссия ЮKassa (апрель 2026)",
     "по данным ЛК ЮKassa за период 01.04—30.04.2026"),
    ("2026-04-30", 0, cats["Налоги"], dev_id, "разовая", "постоянная",
     "НДС ЮKassa (апрель 2026)",
     "по данным ЛК ЮKassa за период 01.04—30.04.2026"),
]

for date, amount, cat_id, init_id, period, behavior, title, comment in EXPENSES:
    cur.execute(
        "SELECT 1 FROM expenses WHERE date = %s::date AND title = %s",
        (date, title)
    )
    if cur.fetchone():
        print(f"  SKIP (уже есть): {title}")
    else:
        cur.execute(
            "INSERT INTO expenses "
            "(date, amount, category_id, initiator_id, periodicity, behavior, title, comment, created_by) "
            "VALUES (%s::date, %s, %s, %s, %s, %s, %s, %s, 'dev')",
            (date, amount, cat_id, init_id, period, behavior, title, comment)
        )
        print(f"  OK: {title} — {amount} ₽")

# ── Доход: выручка за апрель ────────────────────────────────────────
cur.execute(
    "SELECT 1 FROM finance_income WHERE TO_CHAR(date, 'YYYY-MM') = '2026-04' AND title ILIKE '%выручка%'"
)
if cur.fetchone():
    print("  SKIP (уже есть): Выручка апрель 2026")
else:
    cur.execute(
        "INSERT INTO finance_income (date, amount, title, source, comment, created_by) "
        "VALUES ('2026-04-30'::date, 0, 'Выручка (апрель 2026)', 'ЮKassa', "
        "'по данным ЛК ЮKassa за период 01.04—30.04.2026', 'dev')"
    )
    print("  OK: Выручка (апрель 2026) — 0 ₽")

conn.commit()
conn.close()
print("Готово.")
