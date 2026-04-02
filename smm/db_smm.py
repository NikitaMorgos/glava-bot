"""
DB-функции для SMM-редакции.
Таблицы: smm_content_plans, smm_posts.
Паттерн: psycopg2 + RealDictCursor (как admin/db_admin.py).
"""
import json
import os
from contextlib import contextmanager
from typing import Optional

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


def ensure_tables() -> None:
    """Создаёт таблицы если их нет (idempotent)."""
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS smm_content_plans (
                id           SERIAL PRIMARY KEY,
                created_at   TIMESTAMPTZ DEFAULT NOW(),
                week_start   DATE,
                status       TEXT NOT NULL DEFAULT 'draft',
                manual_ideas TEXT DEFAULT '',
                raw_plan     JSONB DEFAULT '[]'
            );

            CREATE TABLE IF NOT EXISTS smm_posts (
                id              SERIAL PRIMARY KEY,
                plan_id         INTEGER REFERENCES smm_content_plans(id) ON DELETE SET NULL,
                channel         TEXT NOT NULL DEFAULT 'dzen',
                status          TEXT NOT NULL DEFAULT 'draft',
                topic           TEXT DEFAULT '',
                article_title   TEXT DEFAULT '',
                article_body    TEXT DEFAULT '',
                editor_feedback TEXT DEFAULT '',
                image_prompt    TEXT DEFAULT '',
                image_url       TEXT DEFAULT '',
                published_url   TEXT DEFAULT '',
                published_at    TIMESTAMPTZ,
                created_at      TIMESTAMPTZ DEFAULT NOW(),
                updated_at      TIMESTAMPTZ DEFAULT NOW()
            );

            CREATE INDEX IF NOT EXISTS idx_smm_posts_plan_id ON smm_posts(plan_id);
            CREATE INDEX IF NOT EXISTS idx_smm_posts_status  ON smm_posts(status);
        """)


# ── Контент-планы ──────────────────────────────────────────────────────────────

def create_plan(week_start: Optional[str] = None, manual_ideas: str = "") -> int:
    ensure_tables()
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO smm_content_plans (week_start, status, manual_ideas)
            VALUES (%s, 'draft', %s) RETURNING id
        """, (week_start or None, manual_ideas))
        return cur.fetchone()["id"]


def get_latest_plans(limit: int = 10) -> list[dict]:
    ensure_tables()
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT cp.*,
                   COUNT(p.id) AS posts_count
            FROM smm_content_plans cp
            LEFT JOIN smm_posts p ON p.plan_id = cp.id
            GROUP BY cp.id
            ORDER BY cp.created_at DESC LIMIT %s
        """, (limit,))
        return [dict(r) for r in cur.fetchall()]


def get_plan(plan_id: int) -> Optional[dict]:
    ensure_tables()
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM smm_content_plans WHERE id = %s", (plan_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def update_plan_status(plan_id: int, status: str) -> None:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE smm_content_plans SET status = %s WHERE id = %s", (status, plan_id))


def set_plan_raw(plan_id: int, raw_plan: list) -> None:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE smm_content_plans SET raw_plan = %s WHERE id = %s",
            (json.dumps(raw_plan, ensure_ascii=False), plan_id),
        )


# ── Посты ──────────────────────────────────────────────────────────────────────

def create_post(plan_id: int, topic: str, channel: str = "dzen") -> int:
    ensure_tables()
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO smm_posts (plan_id, topic, channel, status)
            VALUES (%s, %s, %s, 'draft') RETURNING id
        """, (plan_id, topic, channel))
        return cur.fetchone()["id"]


def get_post(post_id: int) -> Optional[dict]:
    ensure_tables()
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM smm_posts WHERE id = %s", (post_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def get_posts_by_plan(plan_id: int) -> list[dict]:
    ensure_tables()
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM smm_posts WHERE plan_id = %s ORDER BY id",
            (plan_id,),
        )
        return [dict(r) for r in cur.fetchall()]


def get_all_posts(limit: int = 50) -> list[dict]:
    ensure_tables()
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT p.*, c.week_start
            FROM smm_posts p
            LEFT JOIN smm_content_plans c ON c.id = p.plan_id
            ORDER BY p.created_at DESC LIMIT %s
        """, (limit,))
        return [dict(r) for r in cur.fetchall()]


_ALLOWED_POST_FIELDS = frozenset({
    "status", "topic", "article_title", "article_body",
    "editor_feedback", "image_prompt", "image_url",
    "published_url", "published_at",
})


def update_post(post_id: int, **fields) -> None:
    cols = {k: v for k, v in fields.items() if k in _ALLOWED_POST_FIELDS}
    if not cols:
        return
    set_clause = ", ".join(f"{k} = %s" for k in cols)
    values = list(cols.values()) + [post_id]
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(
            f"UPDATE smm_posts SET {set_clause}, updated_at = NOW() WHERE id = %s",
            values,
        )


# ── Отзывы клиентов (источник для Scout) ─────────────────────────────────────

def get_recent_reviews(limit: int = 10) -> list[str]:
    """
    Пробует получить отзывы из БД.
    Проверяет несколько возможных таблиц/столбцов.
    Возвращает пустой список если таблица не найдена.
    """
    candidates = [
        "SELECT review_text AS txt FROM reviews ORDER BY created_at DESC LIMIT %s",
        "SELECT text AS txt FROM feedback ORDER BY created_at DESC LIMIT %s",
        "SELECT content AS txt FROM testimonials ORDER BY created_at DESC LIMIT %s",
        "SELECT notes AS txt FROM draft_orders WHERE notes IS NOT NULL AND notes != '' ORDER BY created_at DESC LIMIT %s",
    ]
    try:
        with _conn() as conn:
            for sql in candidates:
                try:
                    cur = conn.cursor()
                    cur.execute(sql, (limit,))
                    rows = cur.fetchall()
                    if rows:
                        return [r["txt"] for r in rows if r.get("txt")]
                except Exception:
                    pass
    except Exception:
        pass
    return []
