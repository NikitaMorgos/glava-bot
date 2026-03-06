"""
DraftOrder — черновик заказа до оплаты.
ТЗ: Pre-pay flow.
"""

import json
from contextlib import contextmanager
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

import config


@contextmanager
def get_connection():
    conn = psycopg2.connect(config.DATABASE_URL)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_or_create_draft(telegram_id: int, username: str | None = None) -> dict | None:
    """
    Возвращает активный DraftOrder для пользователя или создаёт новый.
    active = draft или payment_pending.
    """
    import db
    user = db.get_or_create_user(telegram_id, username)
    user_id = user["id"]

    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, user_id, status, email, characters, total_price, currency,
                       payment_provider, payment_id, payment_url, created_at, updated_at
                FROM draft_orders
                WHERE user_id = %s AND status IN ('draft', 'payment_pending')
                ORDER BY updated_at DESC LIMIT 1
                """,
                (user_id,),
            )
            row = cur.fetchone()
            if row:
                d = dict(row)
                if isinstance(d.get("characters"), str):
                    d["characters"] = json.loads(d["characters"] or "[]")
                return d

            cur.execute(
                """
                INSERT INTO draft_orders (user_id, status, characters, total_price, currency)
                VALUES (%s, 'draft', '[]', 0, 'RUB')
                RETURNING id, user_id, status, email, characters, total_price, currency,
                          payment_provider, payment_id, payment_url, created_at, updated_at
                """,
                (user_id,),
            )
            row = cur.fetchone()
            if row:
                d = dict(row)
                if isinstance(d.get("characters"), str):
                    d["characters"] = json.loads(d["characters"] or "[]")
                return d
    return None


def get_draft_by_telegram_id(telegram_id: int) -> dict | None:
    """Возвращает активный DraftOrder по telegram_id."""
    import db
    user = db.get_or_create_user(telegram_id, None)
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, user_id, status, email, characters, total_price, currency,
                       payment_provider, payment_id, payment_url, created_at, updated_at
                FROM draft_orders
                WHERE user_id = %s AND status IN ('draft', 'payment_pending', 'paid')
                ORDER BY updated_at DESC LIMIT 1
                """,
                (user["id"],),
            )
            row = cur.fetchone()
            if row:
                d = dict(row)
                if isinstance(d.get("characters"), str):
                    d["characters"] = json.loads(d["characters"] or "[]")
                return d
    return None


def update_draft_characters(draft_id: int, characters: list[dict]) -> None:
    """Обновляет список персонажей."""
    chars_json = json.dumps(characters, ensure_ascii=False)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE draft_orders
                SET characters = %s::jsonb, total_price = %s, updated_at = NOW()
                WHERE id = %s AND status = 'draft'
                """,
                (chars_json, _calc_total(len(characters)), draft_id),
            )


def add_character(draft_id: int, name: str, relation: str) -> list[dict]:
    """Добавляет персонажа и возвращает обновлённый список."""
    draft = _get_draft_by_id(draft_id)
    if not draft or draft["status"] != "draft":
        return []
    chars = list(draft.get("characters") or [])
    chars.append({"name": name.strip(), "relation": relation.strip()})
    update_draft_characters(draft_id, chars)
    return chars


def remove_character(draft_id: int, index: int) -> list[dict]:
    """Удаляет персонажа по индексу и возвращает обновлённый список."""
    draft = _get_draft_by_id(draft_id)
    if not draft or draft["status"] != "draft":
        return []
    chars = list(draft.get("characters") or [])
    if 0 <= index < len(chars):
        chars.pop(index)
        update_draft_characters(draft_id, chars)
    return chars


def _get_draft_by_id(draft_id: int) -> dict | None:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT id, status, characters FROM draft_orders WHERE id = %s",
                (draft_id,),
            )
            row = cur.fetchone()
            if row:
                d = dict(row)
                if isinstance(d.get("characters"), str):
                    d["characters"] = json.loads(d["characters"] or "[]")
                return d
    return None


def update_draft_email(draft_id: int, email: str) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE draft_orders SET email = %s, updated_at = NOW() WHERE id = %s AND status = 'draft'",
                (email.strip(), draft_id),
            )


def set_draft_payment_pending(draft_id: int, payment_id: str, payment_url: str, provider: str = "stub") -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE draft_orders
                SET status = 'payment_pending', payment_id = %s, payment_url = %s,
                    payment_provider = %s, updated_at = NOW()
                WHERE id = %s AND status = 'draft'
                """,
                (payment_id, payment_url, provider, draft_id),
            )


def set_draft_paid(draft_id: int) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE draft_orders SET status = 'paid', updated_at = NOW() WHERE id = %s",
                (draft_id,),
            )


def cancel_draft(draft_id: int) -> None:
    """Отменяет черновик (status → cancelled). После этого get_or_create_draft создаст новый."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE draft_orders SET status = 'cancelled', updated_at = NOW() WHERE id = %s",
                (draft_id,),
            )


def _calc_total(characters_count: int) -> int:
    """Цена в копейках."""
    price_per_char = getattr(config, "PRICE_PER_CHARACTER", 99000)
    return characters_count * price_per_char
