"""
Функции для работы с БД в admin-панели.
Использует прямое подключение psycopg2 (не через db.py основного модуля).
"""
import os
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any

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


# ── Промпты агентов ───────────────────────────────────────────────

def get_all_prompts() -> list[dict]:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT ON (role) role, version, prompt_text, updated_at, updated_by
            FROM prompts
            WHERE is_active = TRUE
            ORDER BY role, version DESC
        """)
        return [dict(r) for r in cur.fetchall()]


def get_prompt(role: str) -> dict | None:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT role, version, prompt_text, updated_at, updated_by
            FROM prompts WHERE role = %s AND is_active = TRUE
            ORDER BY version DESC LIMIT 1
        """, (role,))
        row = cur.fetchone()
        return dict(row) if row else None


def get_prompt_history(role: str, limit: int = 10) -> list[dict]:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT version, LEFT(prompt_text, 100) AS preview, updated_at, updated_by
            FROM prompts WHERE role = %s
            ORDER BY version DESC LIMIT %s
        """, (role, limit))
        return [dict(r) for r in cur.fetchall()]


def get_bot_messages() -> list[dict]:
    """Сообщения бота (role LIKE 'bot_%')."""
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT ON (role) role, version, prompt_text, updated_at, updated_by
            FROM prompts
            WHERE role LIKE 'bot_%%'
            ORDER BY role, version DESC
        """)
        return [dict(r) for r in cur.fetchall()]


def save_prompt(role: str, text: str, author: str) -> None:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COALESCE(MAX(version), 0) AS max_ver FROM prompts WHERE role = %s", (role,))
        max_ver = cur.fetchone()["max_ver"]
        cur.execute("""
            INSERT INTO prompts (role, version, prompt_text, is_active, updated_at, updated_by)
            VALUES (%s, %s, %s, TRUE, NOW(), %s)
        """, (role, max_ver + 1, text, author))


# ── Pipeline jobs ─────────────────────────────────────────────────

def get_pipeline_jobs() -> list[dict]:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT pj.*, u.username
            FROM pipeline_jobs pj
            LEFT JOIN users u ON u.telegram_id = pj.telegram_id
            ORDER BY pj.started_at DESC LIMIT 100
        """)
        return [dict(r) for r in cur.fetchall()]


def get_pipeline_job(telegram_id: int) -> dict | None:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT pj.*, u.username
            FROM pipeline_jobs pj
            LEFT JOIN users u ON u.telegram_id = pj.telegram_id
            WHERE pj.telegram_id = %s
            ORDER BY pj.started_at DESC LIMIT 1
        """, (telegram_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def upsert_pipeline_job(telegram_id: int, phase: str, step: str, status: str, error=None) -> None:
    """Создаёт или обновляет запись о выполнении пайплайна для telegram_id + phase."""
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO pipeline_jobs (telegram_id, phase, step, status, started_at, finished_at, error)
            VALUES (%s, %s, %s, %s, NOW(),
                CASE WHEN %s IN ('done', 'error') THEN NOW() ELSE NULL END,
                %s)
            ON CONFLICT (telegram_id, phase) DO UPDATE
                SET step       = EXCLUDED.step,
                    status     = EXCLUDED.status,
                    finished_at = CASE
                        WHEN EXCLUDED.status IN ('done', 'error') THEN NOW()
                        ELSE pipeline_jobs.finished_at END,
                    error      = EXCLUDED.error,
                    started_at = CASE
                        WHEN pipeline_jobs.status NOT IN ('running') THEN NOW()
                        ELSE pipeline_jobs.started_at END
        """, (telegram_id, phase, step, status, status, error))
        conn.commit()


def get_pipeline_stats() -> dict:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT status, COUNT(*) FROM pipeline_jobs GROUP BY status")
        by_status = {r["status"]: r["count"] for r in cur.fetchall()}
        cur.execute("""
            SELECT AVG(EXTRACT(EPOCH FROM (finished_at - started_at))/3600) AS avg_hours
            FROM pipeline_jobs WHERE status = 'done'
        """)
        avg_hours = (cur.fetchone() or {}).get("avg_hours")
        return {"by_status": by_status, "avg_hours": round(avg_hours or 0, 1)}


# ── Рассылки ─────────────────────────────────────────────────────

def get_mailings() -> list[dict]:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM mailings ORDER BY created_at DESC LIMIT 50")
        return [dict(r) for r in cur.fetchall()]


def create_mailing(name: str, text: str, segment: str, author: str) -> int:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO mailings (name, template_text, segment, created_by, created_at)
            VALUES (%s, %s, %s, %s, NOW()) RETURNING id
        """, (name, text, segment, author))
        mailing_id = cur.fetchone()["id"]
        # Добавляем получателей
        users = get_users_by_segment(segment)
        for u in users:
            cur.execute("""
                INSERT INTO mailing_recipients (mailing_id, telegram_id, status)
                VALUES (%s, %s, 'pending')
            """, (mailing_id, u["telegram_id"]))
        return mailing_id


def mark_recipient_sent(mailing_id: int, telegram_id: int) -> None:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE mailing_recipients SET status = 'sent', sent_at = NOW()
            WHERE mailing_id = %s AND telegram_id = %s
        """, (mailing_id, telegram_id))


def mark_recipient_error(mailing_id: int, telegram_id: int, error: str) -> None:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE mailing_recipients SET status = 'error', error = %s
            WHERE mailing_id = %s AND telegram_id = %s
        """, (error, mailing_id, telegram_id))


def finish_mailing(mailing_id: int, sent_count: int) -> None:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE mailings SET sent_at = NOW(), sent_count = %s WHERE id = %s
        """, (sent_count, mailing_id))


# ── Пользователи / сегменты ───────────────────────────────────────

def get_users_by_segment(segment: str) -> list[dict]:
    with _conn() as conn:
        cur = conn.cursor()
        if segment == "all":
            cur.execute("SELECT telegram_id, username, created_at FROM users ORDER BY created_at DESC")
        elif segment == "paid":
            cur.execute("""
                SELECT u.telegram_id, u.username, u.created_at
                FROM users u JOIN drafts d ON d.telegram_id = u.telegram_id
                WHERE d.status = 'paid'
            """)
        elif segment == "no_payment":
            cur.execute("""
                SELECT u.telegram_id, u.username, u.created_at FROM users u
                WHERE u.telegram_id NOT IN (
                    SELECT telegram_id FROM drafts WHERE status = 'paid'
                )
            """)
        elif segment == "inactive_7":
            cutoff = datetime.utcnow() - timedelta(days=7)
            cur.execute("""
                SELECT telegram_id, username, created_at FROM users
                WHERE last_active < %s OR last_active IS NULL
            """, (cutoff,))
        elif segment == "inactive_30":
            cutoff = datetime.utcnow() - timedelta(days=30)
            cur.execute("""
                SELECT telegram_id, username, created_at FROM users
                WHERE last_active < %s OR last_active IS NULL
            """, (cutoff,))
        elif segment == "book_ready":
            cur.execute("""
                SELECT u.telegram_id, u.username, u.created_at FROM users u
                JOIN pipeline_jobs pj ON pj.telegram_id = u.telegram_id
                WHERE pj.status = 'done'
            """)
        else:
            cur.execute("SELECT telegram_id, username, created_at FROM users LIMIT 200")
        return [dict(r) for r in cur.fetchall()]


# ── Триггеры ─────────────────────────────────────────────────────

def get_triggers() -> list[dict]:
    try:
        with _conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM mailing_triggers ORDER BY id")
            return [dict(r) for r in cur.fetchall()]
    except Exception:
        return []


def toggle_trigger(trigger_id: int) -> None:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE mailing_triggers SET is_active = NOT is_active WHERE id = %s
        """, (trigger_id,))


# ── Предложения по флоу бота ──────────────────────────────────────

def ensure_flow_suggestions_table() -> None:
    """Создаёт таблицу flow_suggestions если её нет."""
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS flow_suggestions (
                id          SERIAL PRIMARY KEY,
                screen_id   TEXT NOT NULL,
                screen_title TEXT,
                suggestion  TEXT NOT NULL,
                author      TEXT NOT NULL DEFAULT 'dasha',
                status      TEXT NOT NULL DEFAULT 'new',
                dev_comment TEXT,
                created_at  TIMESTAMP DEFAULT NOW(),
                updated_at  TIMESTAMP DEFAULT NOW()
            )
        """)


def add_flow_suggestion(screen_id: str, screen_title: str,
                        suggestion: str, author: str = "dasha") -> int:
    ensure_flow_suggestions_table()
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO flow_suggestions (screen_id, screen_title, suggestion, author)
            VALUES (%s, %s, %s, %s) RETURNING id
        """, (screen_id, screen_title, suggestion, author))
        return cur.fetchone()["id"]


def get_flow_suggestions(status: str | None = None) -> list[dict]:
    ensure_flow_suggestions_table()
    with _conn() as conn:
        cur = conn.cursor()
        if status:
            cur.execute("""
                SELECT * FROM flow_suggestions WHERE status = %s
                ORDER BY created_at DESC
            """, (status,))
        else:
            cur.execute("SELECT * FROM flow_suggestions ORDER BY created_at DESC")
        return [dict(r) for r in cur.fetchall()]


def update_flow_suggestion(suggestion_id: int, status: str,
                            dev_comment: str = "") -> None:
    ensure_flow_suggestions_table()
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE flow_suggestions
            SET status = %s, dev_comment = %s, updated_at = NOW()
            WHERE id = %s
        """, (status, dev_comment, suggestion_id))
