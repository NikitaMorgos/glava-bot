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
                SELECT e.id, e.date, e.amount, e.title, e.comment, e.created_at, e.created_by,
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
                SELECT e.id, e.date, e.amount, e.title, e.comment, e.created_at, e.created_by,
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
                periodicity: str, behavior: str, title: str, comment: str,
                created_by: str) -> None:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO expenses
                (date, amount, category_id, initiator_id, periodicity, behavior,
                 title, comment, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (date, amount, category_id, initiator_id, periodicity, behavior,
              title or None, comment or None, created_by))


def update_expense(expense_id: int, date: str, amount: Decimal, category_id: int,
                   initiator_id: int, periodicity: str, behavior: str,
                   title: str, comment: str) -> None:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE expenses
            SET date=%s, amount=%s, category_id=%s, initiator_id=%s,
                periodicity=%s, behavior=%s, title=%s, comment=%s
            WHERE id=%s
        """, (date, amount, category_id, initiator_id,
              periodicity, behavior, title or None, comment or None, expense_id))


def delete_expense(expense_id: int) -> None:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM expenses WHERE id = %s", (expense_id,))


# ── Доходы (поступления, в т.ч. ЮKassa) ─────────────────────────────

def get_income(month: str | None = None) -> list[dict]:
    """Поступления с полями date, amount, title, source, comment, created_by."""
    with _conn() as conn:
        cur = conn.cursor()
        if month:
            cur.execute("""
                SELECT id, date, amount, title, source, comment, created_at, created_by
                FROM finance_income
                WHERE TO_CHAR(date, 'YYYY-MM') = %s
                ORDER BY date DESC, id DESC
            """, (month,))
        else:
            cur.execute("""
                SELECT id, date, amount, title, source, comment, created_at, created_by
                FROM finance_income
                ORDER BY date DESC, id DESC
                LIMIT 500
            """)
        return [dict(r) for r in cur.fetchall()]


def get_income_row(income_id: int) -> dict | None:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM finance_income WHERE id = %s", (income_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def add_income(
    date: str,
    amount: Decimal,
    title: str,
    source: str,
    comment: str,
    created_by: str,
) -> None:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO finance_income (date, amount, title, source, comment, created_by)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (date, amount, title or None, source.strip() or "ЮKassa", comment or None, created_by))


def update_income(
    income_id: int,
    date: str,
    amount: Decimal,
    title: str,
    source: str,
    comment: str,
) -> None:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE finance_income
            SET date=%s, amount=%s, title=%s, source=%s, comment=%s
            WHERE id=%s
        """, (date, amount, title or None, source.strip() or "ЮKassa", comment or None, income_id))


def delete_income(income_id: int) -> None:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM finance_income WHERE id = %s", (income_id,))


# ── P&L ────────────────────────────────────────────────────────────

def get_pnl(months: int = 6) -> dict:
    """
    P&L за последние N календарных месяцев, встречающихся в расходах или доходах.
    """
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT m FROM (
                SELECT DISTINCT TO_CHAR(date, 'YYYY-MM') AS m FROM expenses
                UNION
                SELECT DISTINCT TO_CHAR(date, 'YYYY-MM') AS m FROM finance_income
            ) u
            ORDER BY m DESC
            LIMIT %s
        """, (months,))
        month_list = list(reversed([r["m"] for r in cur.fetchall()]))

        if not month_list:
            return {
                "months": [],
                "rows": [],
                "expense_totals": [],
                "revenue_rows": [],
                "revenue_totals": [],
                "profit": [],
            }

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
        raw_exp = cur.fetchall()

        # Одна строка выручки в P&L — без детализации по поступлениям
        cur.execute("""
            SELECT TO_CHAR(date, 'YYYY-MM') AS month,
                   SUM(amount) AS total
            FROM finance_income
            WHERE TO_CHAR(date, 'YYYY-MM') = ANY(%s)
            GROUP BY TO_CHAR(date, 'YYYY-MM')
            ORDER BY month
        """, (month_list,))
        raw_rev = cur.fetchall()

    categories: dict[str, dict[str, Decimal]] = {}
    for r in raw_exp:
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

    rev_by_month: dict[str, Decimal] = {m: Decimal(0) for m in month_list}
    for r in raw_rev:
        rev_by_month[r["month"]] = r["total"]

    if raw_rev:
        revenue_rows = [
            {
                "label": "Выручка (тестовая)",
                "totals": [float(rev_by_month.get(m, 0)) for m in month_list],
            }
        ]
    else:
        revenue_rows = []

    revenue_totals = [
        sum(row["totals"][i] for row in revenue_rows)
        for i in range(len(month_list))
    ]

    profit = [revenue_totals[i] - expense_totals[i] for i in range(len(month_list))]

    return {
        "months": month_list,
        "rows": rows,
        "expense_totals": expense_totals,
        "revenue_rows": revenue_rows,
        "revenue_totals": revenue_totals,
        "profit": profit,
    }
