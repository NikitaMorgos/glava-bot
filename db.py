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


def get_user_photos(telegram_id: int, limit: int = 15, since=None) -> list[dict]:
    """
    Возвращает последние N фото пользователя.
    since: если задан datetime — возвращает только фото, загруженные после этой даты.
    Результат — список словарей: id, storage_key, caption, created_at
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if since is not None:
                cur.execute(
                    """
                    SELECT p.id, p.storage_key, p.caption, p.created_at
                    FROM photos p
                    JOIN users u ON p.user_id = u.id
                    WHERE u.telegram_id = %s AND p.created_at >= %s
                    ORDER BY p.created_at ASC
                    LIMIT %s
                    """,
                    (telegram_id, since, limit),
                )
            else:
                cur.execute(
                    """
                    SELECT p.id, p.storage_key, p.caption, p.created_at
                    FROM photos p
                    JOIN users u ON p.user_id = u.id
                    WHERE u.telegram_id = %s
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


def get_user_transcripts(telegram_id: int) -> str:
    """
    Собирает все готовые транскрипты голосовых для пользователя (по telegram_id),
    объединяет в одну строку. Используется перед запуском Phase A.
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT v.transcript, v.created_at
                FROM voice_messages v
                JOIN users u ON v.user_id = u.id
                WHERE u.telegram_id = %s
                  AND v.transcript IS NOT NULL
                  AND v.transcript <> ''
                ORDER BY v.created_at ASC
                """,
                (telegram_id,),
            )
            rows = cur.fetchall()
    parts = [row["transcript"].strip() for row in rows if row["transcript"]]
    return "\n\n".join(parts)


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


# ── book_versions ─────────────────────────────────────────────────────────────

def save_book_version(
    telegram_id: int,
    bio_text: str,
    character_name: str = "",
    transcript_hash: str = "",
    pipeline_source: str = "python",
) -> dict:
    """
    Сохраняет новую версию биографии в book_versions.

    Защита: если у пользователя уже есть версия с is_approved=TRUE,
    новая версия сохраняется как НЕ одобренная (is_approved=FALSE),
    что позволяет редактору сравнить и принять решение вручную.

    Возвращает {"id": int, "version": int, "is_approved": bool}.
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Проверяем наличие одобренной версии
            cur.execute(
                "SELECT id, version FROM book_versions "
                "WHERE telegram_id = %s AND is_approved = TRUE "
                "ORDER BY version DESC LIMIT 1",
                (telegram_id,),
            )
            has_approved = cur.fetchone()

            # Следующий номер версии
            cur.execute(
                "SELECT COALESCE(MAX(version), 0) FROM book_versions WHERE telegram_id = %s",
                (telegram_id,),
            )
            max_v = cur.fetchone()["coalesce"]
            new_version = max_v + 1

            cur.execute(
                """INSERT INTO book_versions
                   (telegram_id, version, bio_text, character_name,
                    is_approved, transcript_hash, pipeline_source, created_at)
                   VALUES (%s, %s, %s, %s, FALSE, %s, %s, NOW())
                   RETURNING id, version, is_approved""",
                (telegram_id, new_version, bio_text,
                 character_name or "Герой книги",
                 transcript_hash or None, pipeline_source),
            )
            row = dict(cur.fetchone())

        conn.commit()

    if has_approved:
        import logging as _logging
        _logging.getLogger(__name__).warning(
            "db.save_book_version: tg=%s имеет одобренную версию v=%s; "
            "новая v=%s сохранена без одобрения",
            telegram_id, has_approved["version"], new_version,
        )
    return row


def approve_book_version(version_id: int) -> bool:
    """
    Помечает конкретную версию как одобренную (is_approved=TRUE).
    Все предыдущие одобрения для этого пользователя снимаются.
    Возвращает True при успехе.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Определяем telegram_id для этой версии
            cur.execute(
                "SELECT telegram_id FROM book_versions WHERE id = %s", (version_id,)
            )
            row = cur.fetchone()
            if not row:
                return False
            telegram_id = row[0]

            # Снимаем все предыдущие одобрения
            cur.execute(
                "UPDATE book_versions SET is_approved = FALSE WHERE telegram_id = %s",
                (telegram_id,),
            )
            # Одобряем нужную версию
            cur.execute(
                "UPDATE book_versions SET is_approved = TRUE WHERE id = %s",
                (version_id,),
            )
        conn.commit()
    return True


def get_approved_book_version(telegram_id: int) -> dict | None:
    """Возвращает одобренную версию книги или None."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """SELECT id, version, bio_text, character_name, created_at,
                          transcript_hash, pipeline_source
                   FROM book_versions
                   WHERE telegram_id = %s AND is_approved = TRUE
                   ORDER BY version DESC LIMIT 1""",
                (telegram_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None


def get_latest_book_version(telegram_id: int) -> dict | None:
    """Возвращает последнюю версию книги (одобренную или нет)."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """SELECT id, version, bio_text, character_name, created_at,
                          is_approved, transcript_hash, pipeline_source
                   FROM book_versions
                   WHERE telegram_id = %s
                   ORDER BY version DESC LIMIT 1""",
                (telegram_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None
