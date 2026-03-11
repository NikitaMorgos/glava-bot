"""
Сброс черновика (и опционально голосовых/фото) тестового пользователя.

Использование:
    python scripts/reset_user_draft.py @dmorgos
    python scripts/reset_user_draft.py 123456789
    python scripts/reset_user_draft.py @dmorgos @another 123456789   # несколько
    python scripts/reset_user_draft.py @dmorgos --full      # + удалить голосовые и фото

После сброса при следующем /start пользователь увидит чистый экран как новый.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402 — загружает .env
import db_draft  # noqa: E402
from db_draft import get_connection  # noqa: E402
from psycopg2.extras import RealDictCursor  # noqa: E402


def find_telegram_id_by_username(username: str) -> int | None:
    """Ищет telegram_id по username (без @). Возвращает None если не найден."""
    username = username.lstrip("@").lower()
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT telegram_id FROM users WHERE LOWER(username) = %s LIMIT 1",
                (username,),
            )
            row = cur.fetchone()
            return row["telegram_id"] if row else None


def resolve_id(arg: str) -> int | None:
    """Принимает telegram_id (число) или @username, возвращает telegram_id."""
    if arg.startswith("@") or not arg.lstrip("-").isdigit():
        tid = find_telegram_id_by_username(arg)
        if tid is None:
            print(f"  [!] Пользователь '{arg}' не найден в БД (ещё не писал боту?)")
        return tid
    return int(arg)


def reset_drafts(telegram_id: int) -> int:
    """
    Отменяет все активные черновики пользователя (draft / payment_pending / paid).
    Возвращает количество сброшенных черновиков.
    """
    import db
    user = db.get_or_create_user(telegram_id, None)
    user_id = user["id"]

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE draft_orders
                SET status = 'cancelled', updated_at = NOW()
                WHERE user_id = %s AND status IN ('draft', 'payment_pending', 'paid')
                """,
                (user_id,),
            )
            count = cur.rowcount
    return count


def reset_voices_and_photos(telegram_id: int) -> tuple[int, int]:
    """
    Удаляет все голосовые и фото пользователя из БД (не из S3).
    Возвращает (voices_deleted, photos_deleted).
    """
    import db
    user = db.get_or_create_user(telegram_id, None)
    user_id = user["id"]

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM voice_messages WHERE user_id = %s", (user_id,))
            voices = cur.rowcount
            cur.execute("DELETE FROM photos WHERE user_id = %s", (user_id,))
            photos = cur.rowcount
    return voices, photos


def show_user_state(telegram_id: int) -> None:
    """Показывает текущее состояние пользователя перед сбросом."""
    import db
    user = db.get_or_create_user(telegram_id, None)
    user_id = user["id"]

    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, status, characters, email, payment_id
                FROM draft_orders
                WHERE user_id = %s
                ORDER BY updated_at DESC LIMIT 5
                """,
                (user_id,),
            )
            drafts = cur.fetchall()

            cur.execute("SELECT COUNT(*) AS cnt FROM voice_messages WHERE user_id = %s", (user_id,))
            voices = cur.fetchone()["cnt"]

            cur.execute("SELECT COUNT(*) AS cnt FROM photos WHERE user_id = %s", (user_id,))
            photos = cur.fetchone()["cnt"]

    print(f"\n  Пользователь telegram_id={telegram_id} (user_id={user_id})")
    print(f"  Голосовых: {voices}, Фото: {photos}")
    print(f"  Черновики (последние 5):")
    if drafts:
        for d in drafts:
            chars = d.get("characters") or []
            print(f"    id={d['id']} status={d['status']} персонажей={len(chars) if isinstance(chars, list) else '?'} email={d.get('email') or '-'}")
    else:
        print("    нет черновиков")


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]
    full_reset = "--full" in flags

    if not args:
        print(__doc__)
        sys.exit(1)

    telegram_ids = []
    for a in args:
        tid = resolve_id(a)
        if tid is not None:
            telegram_ids.append((a, tid))

    if not telegram_ids:
        print("Не передано ни одного корректного пользователя.")
        sys.exit(1)

    for arg, tid in telegram_ids:
        print(f"\n{'='*50}")
        print(f"Пользователь: {arg} (telegram_id={tid})")
        show_user_state(tid)

        count = reset_drafts(tid)
        print(f"\n  ✓ Черновиков сброшено: {count}")

        if full_reset:
            voices, photos = reset_voices_and_photos(tid)
            print(f"  ✓ Удалено голосовых: {voices}, фото: {photos}")
            print("  [!] Файлы в S3 не удалены (только записи в БД)")

        print(f"\n  Готово. При следующем /start пользователь увидит чистый экран.")

    print(f"\n{'='*50}")


if __name__ == "__main__":
    main()
