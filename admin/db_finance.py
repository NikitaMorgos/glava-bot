"""
SQL-функции для раздела «Финансы»: расходы, категории, инициаторы, P&L.
"""
from __future__ import annotations
from contextlib import contextmanager
import os
from decimal import Decimal

import psycopg2
import psycopg2.extras


@contextmanager
def _conn():
    db_url = os.environ.get("DATABASE_URL", "")
    conn = psycopg2.connect(db_url, cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── Категории ──────────────────────────────────────────────────────

def get_categories() -> list[dict]:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM expense_categories ORDER BY sort_order, name")
        return [dict(r) for r in cur.fetchall()]


def add_category(name: str) -> None:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO expense_categories (name, sort_order)
            VALUES (%s, (SELECT COALESCE(MAX(sort_order), 0) + 1 FROM expense_categories))
            ON CONFLICT (name) DO NOTHING
        """, (name.strip(),))


def delete_category(cat_id: int) -> bool:
    """Удаляет категорию, если нет связанных расходов. Возвращает True при успехе."""
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) AS n FROM expenses WHERE category_id = %s", (cat_id,))
        if cur.fetchone()["n"] > 0:
            return False
        cur.execute("DELETE FROM expense_categories WHERE id = %s", (cat_id,))
        return True


# ── Инициаторы ─────────────────────────────────────────────────────

def get_initiators() -> list[dict]:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM expense_initiators ORDER BY name")
        return [dict(r) for r in cur.fetchall()]


def add_initiator(name: str) -> None:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO expense_initiators (name) VALUES (%s) ON CONFLICT (name) DO NOTHING
        """, (name.strip(),))


def delete_initiator(init_id: int) -> bool:
    """Удаляет инициатора, если нет связанных расходов."""
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) AS n FROM expenses WHERE initiator_id = %s", (init_id,))
        if cur.fetchone()["n"] > 0:
            return False
        cur.execute("DELETE FROM expense_initiators WHERE id = %s", (init_id,))
        return True


# ── Расходы ────────────────────────────────────────────────────────

def get_expenses(month: str | None = None) -> list[dict]:
    """
    Возвращает расходы с именами категории и инициатора.
    month: 'YYYY-MM' для фильтрации, None — все.
    """
    with _conn() as conn:
        cur = conn.cursor()
        if month:
            cur.execute("""
                SELECT e.id, e.date, e.amount, e.comment, e.created_at, e.created_by,
                       e.periodicity, e.behavior,
                       c.name AS category, i.name AS initiator
                FROM expenses e
                JOIN expense_categories c ON c.id = e.category_id
                JOIN expense_initiators i ON i.id = e.initiator_id
                WHERE TO_CHAR(e.date, 'YYYY-MM') = %s
                ORDER BY e.date DESC, e.id DESC
            """, (month,))
        else:
            cur.execute("""
                SELECT e.id, e.date, e.amount, e.comment, e.created_at, e.created_by,
                       e.periodicity, e.behavior,
                       c.name AS category, i.name AS initiator
                FROM expenses e
                JOIN expense_categories c ON c.id = e.category_id
                JOIN expense_initiators i ON i.id = e.initiator_id
                ORDER BY e.date DESC, e.id DESC
                LIMIT 500
            """)
        return [dict(r) for r in cur.fetchall()]


def get_expense(expense_id: int) -> dict | None:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM expenses WHERE id = %s", (expense_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def add_expense(date: str, amount: Decimal, category_id: int, initiator_id: int,
                periodicity: str, behavior: str, comment: str, created_by: str) -> None:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO expenses
                (date, amount, category_id, initiator_id, periodicity, behavior, comment, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (date, amount, category_id, initiator_id, periodicity, behavior,
              comment or None, created_by))


def update_expense(expense_id: int, date: str, amount: Decimal, category_id: int,
                   initiator_id: int, periodicity: str, behavior: str, comment: str) -> None:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE expenses
            SET date=%s, amount=%s, category_id=%s, initiator_id=%s,
                periodicity=%s, behavior=%s, comment=%s
            WHERE id=%s
        """, (date, amount, category_id, initiator_id,
              periodicity, behavior, comment or None, expense_id))


def delete_expense(expense_id: int) -> None:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM expenses WHERE id = %s", (expense_id,))


# ── P&L ────────────────────────────────────────────────────────────

def get_pnl(months: int = 6) -> dict:
    """
    Возвращает P&L за последние N месяцев.
    Структура:
      {
        "months": ["2026-01", "2026-02", ...],
        "rows": [{"category": "...", "totals": [100, 200, ...]}, ...],
        "expense_totals": [300, 400, ...],   # итого расходов по месяцу
        "revenue": [0, 0, ...],              # заглушка (будет из заказов)
        "profit": [-300, -400, ...],
      }
    """
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT TO_CHAR(date, 'YYYY-MM') AS month
            FROM expenses
            ORDER BY month DESC
            LIMIT %s
        """, (months,))
        month_list = [r["month"] for r in cur.fetchall()]
        month_list = list(reversed(month_list))

        if not month_list:
            return {"months": [], "rows": [], "expense_totals": [],
                    "revenue": [], "profit": []}

        cur.execute("""
            SELECT c.name AS category,
                   TO_CHAR(e.date, 'YYYY-MM') AS month,
                   SUM(e.amount) AS total
            FROM expenses e
            JOIN expense_categories c ON c.id = e.category_id
            WHERE TO_CHAR(e.date, 'YYYY-MM') = ANY(%s)
            GROUP BY c.name, month
            ORDER BY c.name, month
        """, (month_list,))
        raw = cur.fetchall()

    # Pivot
    categories: dict[str, dict[str, Decimal]] = {}
    for r in raw:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = {m: Decimal(0) for m in month_list}
        categories[cat][r["month"]] = r["total"]

    rows = [
        {"category": cat, "totals": [float(categories[cat].get(m, 0)) for m in month_list]}
        for cat in sorted(categories)
    ]

    expense_totals = [
        sum(row["totals"][i] for row in rows)
        for i in range(len(month_list))
    ]
    revenue = [0.0] * len(month_list)
    profit = [revenue[i] - expense_totals[i] for i in range(len(month_list))]

    return {
        "months": month_list,
        "rows": rows,
        "expense_totals": expense_totals,
        "revenue": revenue,
        "profit": profit,
    }
