"""
Работа с базой данных PostgreSQL.
Функции для получения/создания пользователей и сохранения голосовых.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager

import config


@contextmanager
def get_connection():
    """
    Менеджер контекста для подключения к БД.
    Гарантирует закрытие соединения после использования.
    """
    conn = psycopg2.connect(config.DATABASE_URL)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_or_create_user(telegram_id: int, username: str | None) -> dict:
    """
    Находит пользователя по telegram_id или создаёт нового.
    Возвращает словарь с полями: id, telegram_id, username, created_at
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Сначала ищем
            cur.execute(
                "SELECT id, telegram_id, username, created_at FROM users WHERE telegram_id = %s",
                (telegram_id,),
            )
            row = cur.fetchone()
            if row:
                # Обновляем username, чтобы вход по @username работал
                cur.execute(
                    "UPDATE users SET username = %s WHERE telegram_id = %s",
                    (username or "", telegram_id),
                )
                conn.commit()
                return dict(row) | {"username": username or row.get("username") or ""}

            # Не нашли — создаём
            cur.execute(
                "INSERT INTO users (telegram_id, username) VALUES (%s, %s) RETURNING id, telegram_id, username, created_at",
                (telegram_id, username or ""),
            )
            return dict(cur.fetchone())


def save_voice_message(user_id: int, telegram_file_id: str, storage_key: str, duration: int | None) -> dict:
    """
    Сохраняет запись о голосовом сообщении в БД.
    Возвращает созданную запись.
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO voice_messages (user_id, telegram_file_id, storage_key, duration)
                VALUES (%s, %s, %s, %s)
                RETURNING id, user_id, telegram_file_id, storage_key, duration, created_at
                """,
                (user_id, telegram_file_id, storage_key, duration),
            )
            return dict(cur.fetchone())


def save_photo(user_id: int, telegram_file_id: str, storage_key: str, photo_type: str = "photo") -> dict:
    """
    Сохраняет фото в БД (без подписи).
    photo_type: 'photo' (обычное) или 'document' (фото документа).
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO photos (user_id, telegram_file_id, storage_key, photo_type)
                VALUES (%s, %s, %s, %s)
                RETURNING id, user_id, storage_key, caption, photo_type, created_at
                """,
                (user_id, telegram_file_id, storage_key, photo_type),
            )
            return dict(cur.fetchone())


def get_pending_photo(telegram_id: int) -> dict | None:
    """
    Возвращает последнее фото пользователя без подписи.
    Нужно, чтобы связать следующий текст как подпись.
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT p.id, p.user_id, p.storage_key, p.caption, p.created_at
                FROM photos p
                JOIN users u ON p.user_id = u.id
                WHERE u.telegram_id = %s AND p.caption IS NULL
                ORDER BY p.created_at DESC
                LIMIT 1
                """,
                (telegram_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None


def update_voice_transcript(voice_id: int, transcript: str) -> None:
    """Сохраняет транскрипт голосового сообщения."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE voice_messages SET transcript = %s WHERE id = %s", (transcript, voice_id))


def update_photo_caption(photo_id: int, caption: str) -> None:
    """Добавляет подпись к фото."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE photos SET caption = %s WHERE id = %s", (caption, photo_id))


def set_web_password(user_id: int, password_hash: str) -> None:
    """Устанавливает хэш пароля для входа в личный кабинет."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET web_password_hash = %s WHERE id = %s",
                (password_hash, user_id),
            )


def get_user_photos(telegram_id: int, limit: int = 15) -> list[dict]:
    """
    Возвращает последние N фото с подписями (только те, у которых есть подпись).
    Результат — список словарей: id, storage_key, caption, created_at
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT p.id, p.storage_key, p.caption, p.created_at
                FROM photos p
                JOIN users u ON p.user_id = u.id
                WHERE u.telegram_id = %s AND p.caption IS NOT NULL
                ORDER BY p.created_at DESC
                LIMIT %s
                """,
                (telegram_id, limit),
            )
            return [dict(row) for row in cur.fetchall()]


def get_all_clients() -> list[dict]:
    """
    Возвращает всех пользователей с подсчётом голосовых и фото.
    Для списка клиентов при экспорте.
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT u.id, u.telegram_id, u.username, u.created_at,
                    (SELECT COUNT(*) FROM voice_messages v WHERE v.user_id = u.id) as voice_count,
                    (SELECT COUNT(*) FROM photos p WHERE p.user_id = u.id AND p.caption IS NOT NULL) as photo_count
                FROM users u
                ORDER BY u.created_at DESC
                """
            )
            return [dict(row) for row in cur.fetchall()]


def get_user_voice_messages(telegram_id: int, limit: int = 5) -> list[dict]:
    """
    Возвращает последние N голосовых сообщений пользователя.
    Результат — список словарей с полями: id, storage_key, duration, created_at
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT v.id, v.storage_key, v.duration, v.created_at
                FROM voice_messages v
                JOIN users u ON v.user_id = u.id
                WHERE u.telegram_id = %s
                ORDER BY v.created_at DESC
                LIMIT %s
                """,
                (telegram_id, limit),
            )
            return [dict(row) for row in cur.fetchall()]


def get_user_all_data(telegram_id: int) -> tuple[dict, list[dict], list[dict]]:
    """
    Возвращает все данные клиента для экспорта.
    (user, voice_messages, photos)
    Голосовые и фото отсортированы по дате (старые сначала — порядок интервью).
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT id, telegram_id, username, created_at FROM users WHERE telegram_id = %s",
                (telegram_id,),
            )
            row = cur.fetchone()
            if not row:
                return {}, [], []
            user = dict(row)
            cur.execute(
                """
                SELECT id, storage_key, duration, created_at, transcript
                FROM voice_messages WHERE user_id = %s
                ORDER BY created_at ASC
                """,
                (user["id"],),
            )
            voices = [dict(r) for r in cur.fetchall()]
            cur.execute(
                """
                SELECT id, storage_key, caption, created_at
                FROM photos WHERE user_id = %s AND caption IS NOT NULL
                ORDER BY created_at ASC
                """,
                (user["id"],),
            )
            photos = [dict(r) for r in cur.fetchall()]
            return user, voices, photos
