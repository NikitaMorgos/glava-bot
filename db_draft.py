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


_DRAFT_COLS = """id, user_id, status, email, characters, total_price, currency,
                  payment_provider, payment_id, payment_url,
                  character_relation, narrators, bot_state, revision_count,
                  pending_revision, revision_deadline,
                  promo_code_id, discount_amount,
                  created_at, updated_at"""


def _hydrate(row: dict) -> dict:
    d = dict(row)
    for field in ("characters", "narrators"):
        if isinstance(d.get(field), str):
            d[field] = json.loads(d[field] or "[]")
    return d


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
                f"""
                SELECT {_DRAFT_COLS}
                FROM draft_orders
                WHERE user_id = %s AND status IN ('draft', 'payment_pending')
                ORDER BY updated_at DESC LIMIT 1
                """,
                (user_id,),
            )
            row = cur.fetchone()
            if row:
                return _hydrate(row)

            cur.execute(
                f"""
                INSERT INTO draft_orders (user_id, status, characters, total_price, currency, bot_state)
                VALUES (%s, 'draft', '[]', 0, 'RUB', 'draft')
                RETURNING {_DRAFT_COLS}
                """,
                (user_id,),
            )
            row = cur.fetchone()
            return _hydrate(row) if row else None
    return None


def get_draft_by_id(draft_id: int) -> dict | None:
    """Возвращает DraftOrder по его id."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                f"SELECT {_DRAFT_COLS} FROM draft_orders WHERE id = %s",
                (draft_id,),
            )
            row = cur.fetchone()
            return _hydrate(row) if row else None


def get_draft_by_telegram_id(telegram_id: int) -> dict | None:
    """Возвращает активный DraftOrder по telegram_id."""
    import db
    user = db.get_or_create_user(telegram_id, None)
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                f"""
                SELECT {_DRAFT_COLS}
                FROM draft_orders
                WHERE user_id = %s AND status IN ('draft', 'payment_pending', 'paid')
                ORDER BY updated_at DESC LIMIT 1
                """,
                (user["id"],),
            )
            row = cur.fetchone()
            return _hydrate(row) if row else None
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
                f"SELECT {_DRAFT_COLS} FROM draft_orders WHERE id = %s",
                (draft_id,),
            )
            row = cur.fetchone()
            return _hydrate(row) if row else None
    return None


def update_draft_email(draft_id: int, email: str) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE draft_orders SET email = %s, updated_at = NOW() WHERE id = %s AND status = 'draft'",
                (email.strip(), draft_id),
            )


def reset_draft_after_price_change(draft_id: int) -> None:
    """
    После смены суммы (промо): сбрасывает незавершённый платёж,
    чтобы пользователь создал новый с актуальной суммой.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE draft_orders
                SET status = 'draft', payment_id = NULL, payment_url = NULL,
                    payment_provider = NULL, updated_at = NOW()
                WHERE id = %s AND status = 'payment_pending'
                """,
                (draft_id,),
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


def _calc_total(characters_count: int, discount_amount: int = 0) -> int:
    """Цена в копейках с учётом скидки."""
    price_per_char = getattr(config, "PRICE_PER_CHARACTER", 1000)
    total = characters_count * price_per_char
    return max(0, total - discount_amount)


def get_final_price(draft: dict) -> int:
    """Итоговая цена заказа с учётом скидки (в копейках)."""
    total = int(draft.get("total_price") or 0)
    discount = int(draft.get("discount_amount") or 0)
    return max(0, total - discount)


# ── Расширения bot_scenario_v2 ──────────────────────────────────────────────

def update_character_relation(draft_id: int, relation: str) -> None:
    """Обновляет родство персонажа (character_relation)."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE draft_orders SET character_relation = %s, updated_at = NOW() WHERE id = %s",
                (relation.strip(), draft_id),
            )


def set_bot_state(draft_id: int, state: str) -> None:
    """Устанавливает состояние бота (bot_state) по spec v2."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE draft_orders SET bot_state = %s, updated_at = NOW() WHERE id = %s",
                (state, draft_id),
            )


def get_bot_state(telegram_id: int) -> str:
    """Возвращает bot_state для пользователя (или 'no_project')."""
    draft = get_draft_by_telegram_id(telegram_id)
    if not draft:
        return "no_project"
    return draft.get("bot_state") or draft.get("status") or "no_project"


# ── Нарраторы ────────────────────────────────────────────────────────────────

def get_narrators(draft_id: int) -> list[dict]:
    draft = _get_draft_by_id(draft_id)
    if not draft:
        return []
    return list(draft.get("narrators") or [])


def add_narrator(draft_id: int, name: str, relation: str) -> list[dict]:
    """Добавляет нарратора и возвращает обновлённый список."""
    draft = _get_draft_by_id(draft_id)
    if not draft:
        return []
    narrators = list(draft.get("narrators") or [])
    narrator_id = f"n{len(narrators) + 1}"
    narrators.append({"id": narrator_id, "name": name.strip(), "relation": relation.strip()})
    _save_narrators(draft_id, narrators)
    return narrators


def remove_narrator(draft_id: int, narrator_id: str) -> list[dict]:
    """Удаляет нарратора по id и возвращает обновлённый список."""
    draft = _get_draft_by_id(draft_id)
    if not draft:
        return []
    narrators = [n for n in (draft.get("narrators") or []) if n.get("id") != narrator_id]
    _save_narrators(draft_id, narrators)
    return narrators


def _save_narrators(draft_id: int, narrators: list[dict]) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE draft_orders SET narrators = %s::jsonb, updated_at = NOW() WHERE id = %s",
                (json.dumps(narrators, ensure_ascii=False), draft_id),
            )


# ── Ревизии ─────────────────────────────────────────────────────────────────

def increment_revision_count(draft_id: int) -> int:
    """Увеличивает счётчик ревизий и возвращает новое значение."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE draft_orders
                SET revision_count = COALESCE(revision_count, 0) + 1, updated_at = NOW()
                WHERE id = %s
                RETURNING revision_count
                """,
                (draft_id,),
            )
            row = cur.fetchone()
            return row[0] if row else 0


def get_revision_count(draft_id: int) -> int:
    draft = _get_draft_by_id(draft_id)
    return int(draft.get("revision_count") or 0) if draft else 0


def set_pending_revision(draft_id: int, text: str, deadline_minutes: int = 3) -> None:
    """Сохраняет текст ожидающей ревизии с дедлайном debounce."""
    from datetime import datetime, timezone, timedelta
    deadline = datetime.now(timezone.utc) + timedelta(minutes=deadline_minutes)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE draft_orders
                SET pending_revision = %s, revision_deadline = %s, updated_at = NOW()
                WHERE id = %s
                """,
                (text, deadline, draft_id),
            )


def get_pending_revision(draft_id: int) -> tuple[str | None, bool]:
    """
    Возвращает (text, is_ready).
    is_ready=True если debounce истёк (deadline < NOW()).
    """
    from datetime import datetime, timezone
    draft = _get_draft_by_id(draft_id)
    if not draft:
        return None, False
    text = draft.get("pending_revision")
    deadline = draft.get("revision_deadline")
    if not text:
        return None, False
    if deadline is None:
        return text, True
    now = datetime.now(timezone.utc)
    if hasattr(deadline, 'tzinfo') and deadline.tzinfo is None:
        from datetime import timezone as tz
        deadline = deadline.replace(tzinfo=tz.utc)
    return text, now >= deadline


def clear_pending_revision(draft_id: int) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE draft_orders SET pending_revision = NULL, revision_deadline = NULL, updated_at = NOW() WHERE id = %s",
                (draft_id,),
            )
