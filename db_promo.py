"""
Промо-коды: DB-операции.
Используется и ботом (main.py), и админкой (admin/).
"""
import random
import string
from contextlib import contextmanager
from datetime import datetime, timezone

import psycopg2
from psycopg2.extras import RealDictCursor

import config


@contextmanager
def _conn():
    conn = psycopg2.connect(config.DATABASE_URL, cursor_factory=RealDictCursor)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── Генерация кода ────────────────────────────────────────────────────────────

def _generate_code(prefix: str = "GLAVA", length: int = 6) -> str:
    """Генерирует уникальный код вида GLAVA-A3X7K2."""
    chars = string.ascii_uppercase + string.digits
    suffix = "".join(random.choices(chars, k=length))
    return f"{prefix}-{suffix}"


# ── Валидация ─────────────────────────────────────────────────────────────────

def validate_promo(code: str, user_id: int) -> tuple[dict | None, str]:
    """
    Проверяет промо-код для пользователя.
    Возвращает (promo_dict, "") при успехе или (None, error_message) при ошибке.
    """
    code = code.strip().upper()
    if not code:
        return None, "Введите промо-код."

    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, code, type, discount_type, discount_value,
                   max_uses, used_count, expires_at, assigned_user_id, sent_at, is_active
            FROM promo_codes
            WHERE UPPER(code) = %s
            """,
            (code,),
        )
        row = cur.fetchone()

    if not row:
        return None, "Промо-код не найден."

    promo = dict(row)

    if not promo["is_active"]:
        return None, "Промо-код деактивирован."

    now = datetime.now(timezone.utc)

    # Проверка общего срока действия
    if promo["expires_at"]:
        exp = promo["expires_at"]
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if now > exp:
            return None, "Срок действия промо-кода истёк."

    # Для персональных с привязкой к users.id — только этот пользователь
    # (из админки без привязки assigned_user_id = NULL — как «персональный» с лимитом, не авто-рассылка)
    if promo["type"] == "personal":
        if promo["assigned_user_id"] is not None and promo["assigned_user_id"] != user_id:
            return None, "Этот промо-код предназначен другому пользователю."
        if promo["sent_at"]:
            sent = promo["sent_at"]
            if sent.tzinfo is None:
                sent = sent.replace(tzinfo=timezone.utc)
            from datetime import timedelta
            valid_until = sent + timedelta(hours=config.PERSONAL_PROMO_VALID_HOURS)
            if now > valid_until:
                return None, "Срок действия персонального промо-кода истёк."

    # Проверка лимита использований
    if promo["max_uses"] is not None and promo["used_count"] >= promo["max_uses"]:
        return None, "Промо-код уже использован максимальное количество раз."

    # Проверка: не использовал ли этот пользователь уже этот код
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM promo_usages WHERE promo_id = %s AND user_id = %s LIMIT 1",
            (promo["id"], user_id),
        )
        if cur.fetchone():
            return None, "Вы уже использовали этот промо-код."

    return promo, ""


def calc_discount(promo: dict, original_price_kopecks: int) -> int:
    """Рассчитывает скидку в копейках для данного заказа."""
    if promo["discount_type"] == "percent":
        return int(original_price_kopecks * float(promo["discount_value"]) / 100)
    else:
        return min(int(promo["discount_value"]), original_price_kopecks)


# ── Применение ────────────────────────────────────────────────────────────────

def apply_promo(draft_id: int, promo_id: int, user_id: int, discount_kopecks: int) -> None:
    """
    Записывает применение промо-кода:
    - обновляет draft_orders (promo_code_id, discount_amount)
    - создаёт запись в promo_usages
    - инкрементирует used_count
    """
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE draft_orders
            SET promo_code_id = %s, discount_amount = %s, updated_at = NOW()
            WHERE id = %s
            """,
            (promo_id, discount_kopecks, draft_id),
        )
        cur.execute(
            """
            INSERT INTO promo_usages (promo_id, user_id, draft_id, discount_amount)
            VALUES (%s, %s, %s, %s)
            """,
            (promo_id, user_id, draft_id, discount_kopecks),
        )
        cur.execute(
            "UPDATE promo_codes SET used_count = used_count + 1 WHERE id = %s",
            (promo_id,),
        )


def remove_promo_from_draft(draft_id: int) -> None:
    """Убирает промо-код из черновика (если пользователь хочет заменить)."""
    with _conn() as conn:
        cur = conn.cursor()
        # Уменьшаем used_count обратно
        cur.execute(
            """
            UPDATE promo_codes SET used_count = GREATEST(used_count - 1, 0)
            WHERE id = (SELECT promo_code_id FROM draft_orders WHERE id = %s)
            """,
            (draft_id,),
        )
        # Удаляем запись из usages
        cur.execute(
            "DELETE FROM promo_usages WHERE draft_id = %s",
            (draft_id,),
        )
        cur.execute(
            """
            UPDATE draft_orders
            SET promo_code_id = NULL, discount_amount = 0, updated_at = NOW()
            WHERE id = %s
            """,
            (draft_id,),
        )


# ── Персональные промо ────────────────────────────────────────────────────────

def generate_personal_promo(user_id: int) -> dict:
    """
    Создаёт персональный промо-код для пользователя.
    Возвращает словарь с полями id, code.
    """
    from datetime import timedelta

    discount_pct = getattr(config, "PERSONAL_PROMO_DISCOUNT_PERCENT", 15)

    # Генерируем уникальный код
    for _ in range(10):
        code = _generate_code(prefix="GLAVA", length=6)
        with _conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM promo_codes WHERE code = %s", (code,))
            if not cur.fetchone():
                break
    else:
        raise RuntimeError("Не удалось сгенерировать уникальный промо-код")

    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO promo_codes
                (code, type, discount_type, discount_value, max_uses,
                 assigned_user_id, is_active, created_by)
            VALUES (%s, 'personal', 'percent', %s, 1, %s, TRUE, 'auto')
            RETURNING id, code
            """,
            (code, float(discount_pct), user_id),
        )
        row = cur.fetchone()
    return dict(row)


def get_users_needing_personal_promo() -> list[dict]:
    """
    Возвращает пользователей, зарегистрированных ~48ч назад,
    которым ещё не был отправлен персональный промо-код.
    Окно: от 49ч до 47ч назад (чтобы не пропустить и не задвоить).
    """
    delay = getattr(config, "PERSONAL_PROMO_DELAY_HOURS", 48)
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT u.id, u.telegram_id, u.username
            FROM users u
            WHERE u.created_at BETWEEN NOW() - INTERVAL '%s hours' AND NOW() - INTERVAL '%s hours'
              AND u.telegram_id IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1 FROM promo_codes p
                  WHERE p.assigned_user_id = u.id AND p.type = 'personal'
              )
            """,
            (delay + 1, delay - 1),
        )
        return [dict(r) for r in cur.fetchall()]


def mark_promo_sent(promo_id: int) -> None:
    """Проставляет sent_at = NOW() после отправки пользователю."""
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE promo_codes SET sent_at = NOW() WHERE id = %s",
            (promo_id,),
        )


def get_promo_by_draft(draft_id: int) -> dict | None:
    """Возвращает промо-код, применённый к черновику (для отображения в summary)."""
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT p.id, p.code, p.discount_type, p.discount_value, d.discount_amount
            FROM draft_orders d
            JOIN promo_codes p ON p.id = d.promo_code_id
            WHERE d.id = %s
            """,
            (draft_id,),
        )
        row = cur.fetchone()
    return dict(row) if row else None
