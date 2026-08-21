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


# ── projects & heroes (для кабинета v3) ──────────────────────────────────────

def get_user_projects(owner_user_id: int) -> list[dict]:
    """
    Возвращает список проектов пользователя со сводкой:
    id, project_type, goal, scenario_type, created_at,
    + agg: hero_count, voice_count, photo_count,
    + первый герой (hero_name, hero_relation) для карточки,
    + book_version, book_created_at — последняя готовая версия книги (или NULL).
    Свежие первыми.
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    p.id, p.project_type, p.goal, p.scenario_type, p.created_at,
                    (SELECT COUNT(*) FROM heroes h WHERE h.project_id = p.id) AS hero_count,
                    (SELECT COUNT(*) FROM voice_messages v WHERE v.project_id = p.id) AS voice_count,
                    (SELECT COUNT(*) FROM photos ph WHERE ph.project_id = p.id) AS photo_count,
                    (SELECT name FROM heroes h WHERE h.project_id = p.id ORDER BY h.id ASC LIMIT 1) AS hero_name,
                    (SELECT relation FROM heroes h WHERE h.project_id = p.id ORDER BY h.id ASC LIMIT 1) AS hero_relation,
                    (SELECT version FROM project_books pb WHERE pb.project_id = p.id ORDER BY version DESC LIMIT 1) AS book_version,
                    (SELECT created_at FROM project_books pb WHERE pb.project_id = p.id ORDER BY version DESC LIMIT 1) AS book_created_at
                FROM projects p
                WHERE p.owner_user_id = %s
                ORDER BY p.created_at DESC
                """,
                (owner_user_id,),
            )
            return [dict(r) for r in cur.fetchall()]


def get_project_owner_email(project_id: int) -> str | None:
    """
    Возвращает email владельца проекта (для уведомлений от worker'a).
    None если проект не найден или у владельца нет email.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT u.email FROM projects p
                JOIN users u ON u.id = p.owner_user_id
                WHERE p.id = %s
                """,
                (project_id,),
            )
            row = cur.fetchone()
            return row[0] if row and row[0] else None


def get_project(project_id: int, owner_user_id: int) -> dict | None:
    """
    Возвращает проект по id, ТОЛЬКО если он принадлежит owner_user_id.
    Защита от чужих project_id.
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, owner_user_id, project_type, goal, collection_strategy,
                       scenario_type, materials_submitted_at, created_at
                FROM projects
                WHERE id = %s AND owner_user_id = %s
                """,
                (project_id, owner_user_id),
            )
            row = cur.fetchone()
            return dict(row) if row else None


def get_current_round_number(project_id: int) -> int:
    """
    Текущий номер раунда обработки. Если стадий ещё нет — 1, иначе MAX+1 если
    предыдущий раунд уже завершён, иначе тот же что и текущий открытый.
    Простая реализация: число опубликованных версий вопросов + 1 (раунд 1 = до первых
    вопросов; раунд 2 = после первых вопросов).
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM project_questions WHERE project_id = %s",
                (project_id,),
            )
            n = cur.fetchone()[0]
            return n + 1


def init_job_stages(project_id: int, round_number: int, stages: list[tuple[str, str]]) -> None:
    """
    Создаёт записи для всех стадий раунда (status='pending').
    stages: [(stage_key, stage_label), ...] — в порядке выполнения.
    Не падает если стадия уже есть (UNIQUE constraint — DO NOTHING).
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            for ordering, (key, label) in enumerate(stages):
                cur.execute(
                    """
                    INSERT INTO project_job_stages
                        (project_id, round_number, stage_key, stage_label, ordering, status)
                    VALUES (%s, %s, %s, %s, %s, 'pending')
                    ON CONFLICT (project_id, round_number, stage_key) DO NOTHING
                    """,
                    (project_id, round_number, key, label, ordering),
                )


def update_job_stage(
    project_id: int,
    round_number: int,
    stage_key: str,
    status: str,
    error_message: str | None = None,
) -> None:
    """
    Обновляет статус стадии. При status='running' ставит started_at = NOW(),
    при 'done'/'failed' — finished_at = NOW().
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            if status == "running":
                cur.execute(
                    """
                    UPDATE project_job_stages
                    SET status = 'running', started_at = COALESCE(started_at, NOW())
                    WHERE project_id = %s AND round_number = %s AND stage_key = %s
                    """,
                    (project_id, round_number, stage_key),
                )
            elif status in ("done", "failed"):
                cur.execute(
                    """
                    UPDATE project_job_stages
                    SET status = %s, finished_at = NOW(), error_message = %s
                    WHERE project_id = %s AND round_number = %s AND stage_key = %s
                    """,
                    (status, error_message, project_id, round_number, stage_key),
                )
            else:
                cur.execute(
                    """
                    UPDATE project_job_stages SET status = %s
                    WHERE project_id = %s AND round_number = %s AND stage_key = %s
                    """,
                    (status, project_id, round_number, stage_key),
                )


def get_job_stages(project_id: int, round_number: int | None = None) -> list[dict]:
    """
    Все стадии раунда обработки в порядке ordering.
    Если round_number=None — берёт текущий раунд (последний MAX).
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if round_number is None:
                cur.execute(
                    "SELECT COALESCE(MAX(round_number), 1) AS r FROM project_job_stages "
                    "WHERE project_id = %s",
                    (project_id,),
                )
                round_number = cur.fetchone()["r"]
            cur.execute(
                """
                SELECT id, round_number, stage_key, stage_label, status, ordering,
                       started_at, finished_at, error_message
                FROM project_job_stages
                WHERE project_id = %s AND round_number = %s
                ORDER BY ordering ASC
                """,
                (project_id, round_number),
            )
            return [dict(r) for r in cur.fetchall()]


def submit_project_materials(project_id: int, owner_user_id: int) -> bool:
    """
    Клиент подтверждает «всё загружено, начинайте». Ставит materials_submitted_at = NOW().
    Возвращает True если успешно (проект принадлежит owner'у).
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE projects
                SET materials_submitted_at = NOW()
                WHERE id = %s AND owner_user_id = %s
                """,
                (project_id, owner_user_id),
            )
            return cur.rowcount > 0


def reset_project_submission(project_id: int) -> None:
    """
    Сбрасывает materials_submitted_at в NULL. Вызывается при публикации новой
    версии questions: начинается новый раунд догрузки, клиент снова должен
    нажать «готово».
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE projects SET materials_submitted_at = NULL WHERE id = %s",
                (project_id,),
            )


def get_project_heroes(project_id: int) -> list[dict]:
    """Все герои проекта (subject + narrators) по порядку создания."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, project_id, name, relation, role, years, place, created_at
                FROM heroes
                WHERE project_id = %s
                ORDER BY id ASC
                """,
                (project_id,),
            )
            return [dict(r) for r in cur.fetchall()]


def get_project_subject(project_id: int) -> dict | None:
    """Главный персонаж книги (о ком). Может не быть, если ещё не создавался."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, project_id, name, relation, role, years, place, created_at
                FROM heroes
                WHERE project_id = %s AND role = 'subject'
                ORDER BY id ASC LIMIT 1
                """,
                (project_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None


def get_project_narrators(project_id: int) -> list[dict]:
    """Рассказчики (кто даёт интервью). Сюда добавляются через UI."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, project_id, name, relation, role, years, place, created_at
                FROM heroes
                WHERE project_id = %s AND role = 'narrator'
                ORDER BY id ASC
                """,
                (project_id,),
            )
            return [dict(r) for r in cur.fetchall()]


def get_project_voices(project_id: int) -> list[dict]:
    """
    Все голосовые проекта (по project_id). Включает hero_id для группировки.
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, hero_id, storage_key, duration, transcript,
                       original_filename, created_at
                FROM voice_messages
                WHERE project_id = %s
                ORDER BY created_at ASC
                """,
                (project_id,),
            )
            return [dict(r) for r in cur.fetchall()]


def get_project_photos(project_id: int) -> list[dict]:
    """Все фото проекта (по project_id)."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, hero_id, storage_key, caption, photo_type, created_at
                FROM photos
                WHERE project_id = %s
                ORDER BY created_at ASC
                """,
                (project_id,),
            )
            return [dict(r) for r in cur.fetchall()]


def create_project(
    owner_user_id: int,
    project_type: str = "one_person",
    goal: str | None = None,
    scenario_type: str = "basic",
) -> dict:
    """Создаёт новый проект, возвращает запись."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO projects (owner_user_id, project_type, goal, scenario_type)
                VALUES (%s, %s, %s, %s)
                RETURNING id, owner_user_id, project_type, goal, scenario_type, created_at
                """,
                (owner_user_id, project_type, goal, scenario_type),
            )
            return dict(cur.fetchone())


def create_hero(
    project_id: int,
    name: str,
    relation: str | None = None,
    years: str | None = None,
    place: str | None = None,
    role: str = "narrator",
) -> dict:
    """
    Создаёт нового героя проекта.
    role='subject' — главный персонаж книги (о ком). Один на проект.
    role='narrator' — рассказчик (кто даёт интервью). Несколько на проект.
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO heroes (project_id, name, relation, years, place, role)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, project_id, name, relation, role, years, place, created_at
                """,
                (project_id, name, relation, years, place, role),
            )
            return dict(cur.fetchone())


def update_hero(
    hero_id: int,
    project_id: int,
    name: str,
    relation: str | None = None,
    years: str | None = None,
    place: str | None = None,
) -> dict | None:
    """
    Обновляет данные героя ТОЛЬКО если он принадлежит указанному проекту.
    Возвращает обновлённую запись или None если не нашёл / не его проект.
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                UPDATE heroes
                SET name = %s, relation = %s, years = %s, place = %s
                WHERE id = %s AND project_id = %s
                RETURNING id, project_id, name, relation, years, place, created_at
                """,
                (name, relation, years, place, hero_id, project_id),
            )
            row = cur.fetchone()
            return dict(row) if row else None


def delete_hero(hero_id: int, project_id: int) -> bool:
    """
    Удаляет рассказчика ТОЛЬКО если он принадлежит указанному проекту И его role='narrator'.
    Главный персонаж книги (role='subject') удалить нельзя — только редактировать.
    Голосовые/фото НЕ удаляются — у них hero_id обнуляется (ON DELETE SET NULL).
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM heroes WHERE id = %s AND project_id = %s AND role = 'narrator'",
                (hero_id, project_id),
            )
            return cur.rowcount > 0


# ── email & magic-link авторизация ────────────────────────────────────────────

def get_user_by_email(email: str) -> dict | None:
    """Находит пользователя по email (case-insensitive)."""
    email = (email or "").strip().lower()
    if not email:
        return None
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, telegram_id, username, email, email_verified_at, created_at
                FROM users
                WHERE LOWER(email) = %s
                LIMIT 1
                """,
                (email,),
            )
            row = cur.fetchone()
            return dict(row) if row else None


def create_user_with_email(email: str) -> dict:
    """
    Создаёт нового пользователя только с email (без telegram).
    telegram_id остаётся NULL — это web-only клиент.
    """
    email_normalized = (email or "").strip().lower()
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO users (email, username)
                VALUES (%s, %s)
                RETURNING id, telegram_id, username, email, email_verified_at, created_at
                """,
                (email_normalized, ""),
            )
            return dict(cur.fetchone())


def mark_user_email_verified(user_id: int) -> None:
    """Помечает email пользователя как подтверждённый (после первого magic-link клика)."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET email_verified_at = NOW() WHERE id = %s AND email_verified_at IS NULL",
                (user_id,),
            )


def create_magic_link_token(
    user_id: int,
    token: str,
    purpose: str = "login",
    ttl_minutes: int = 30,
    requested_ip: str | None = None,
) -> dict:
    """
    Создаёт magic-link токен для пользователя.
    Возвращает запись со сроком истечения.
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO magic_link_tokens (token, user_id, purpose, expires_at, requested_ip)
                VALUES (%s, %s, %s, NOW() + (%s || ' minutes')::interval, %s)
                RETURNING token, user_id, purpose, expires_at, created_at
                """,
                (token, user_id, purpose, str(ttl_minutes), requested_ip),
            )
            return dict(cur.fetchone())


def delete_voice_in_project(voice_id: int, project_id: int, owner_user_id: int) -> dict | None:
    """
    Удаляет голосовое сообщение ТОЛЬКО если оно в проекте указанного owner'а.
    Возвращает {"storage_key": ...} удалённой записи, чтобы вызывающий удалил из S3.
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                DELETE FROM voice_messages
                WHERE id = %s AND project_id = %s
                  AND project_id IN (SELECT id FROM projects WHERE owner_user_id = %s)
                RETURNING storage_key
                """,
                (voice_id, project_id, owner_user_id),
            )
            row = cur.fetchone()
            return dict(row) if row else None


def update_photo_caption_in_project(
    photo_id: int, project_id: int, owner_user_id: int, caption: str | None
) -> dict | None:
    """
    Обновляет подпись фото ТОЛЬКО если оно в проекте указанного owner'а.
    Возвращает обновлённую запись или None.
    """
    caption = (caption or "").strip() or None
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                UPDATE photos
                SET caption = %s
                WHERE id = %s AND project_id = %s
                  AND project_id IN (SELECT id FROM projects WHERE owner_user_id = %s)
                RETURNING id, caption, photo_type
                """,
                (caption, photo_id, project_id, owner_user_id),
            )
            row = cur.fetchone()
            return dict(row) if row else None


def delete_photo_in_project(photo_id: int, project_id: int, owner_user_id: int) -> dict | None:
    """
    Удаляет фото ТОЛЬКО если оно в проекте указанного owner'а.
    Возвращает {"storage_key": ...} для удаления из S3.
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                DELETE FROM photos
                WHERE id = %s AND project_id = %s
                  AND project_id IN (SELECT id FROM projects WHERE owner_user_id = %s)
                RETURNING storage_key
                """,
                (photo_id, project_id, owner_user_id),
            )
            row = cur.fetchone()
            return dict(row) if row else None


def save_voice_for_project(
    user_id: int,
    project_id: int,
    hero_id: int | None,
    storage_key: str,
    duration: int | None = None,
    source: str = "web",
    original_filename: str | None = None,
) -> dict:
    """
    Сохраняет голосовое сообщение в БД с привязкой к проекту и рассказчику.
    original_filename — оригинальное имя файла (для отображения).
    """
    import uuid as _uuid
    web_id = f"{source}_upload_{_uuid.uuid4().hex[:8]}"
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO voice_messages
                    (user_id, telegram_file_id, storage_key, duration,
                     project_id, hero_id, original_filename)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id, user_id, project_id, hero_id, storage_key, duration,
                          original_filename, created_at
                """,
                (user_id, web_id, storage_key, duration, project_id, hero_id, original_filename),
            )
            return dict(cur.fetchone())


def save_photo_for_project(
    user_id: int,
    project_id: int,
    hero_id: int | None,
    storage_key: str,
    caption: str | None = None,
    photo_type: str = "photo",
    source: str = "web",
) -> dict:
    """
    Сохраняет фото с привязкой к проекту и рассказчику.
    photo_type: 'photo' (обычное) или 'document' (грамота/удостоверение).
    """
    import uuid as _uuid
    web_id = f"{source}_upload_{_uuid.uuid4().hex[:8]}"
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO photos
                    (user_id, telegram_file_id, storage_key, caption, photo_type, project_id, hero_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id, user_id, project_id, hero_id, storage_key, caption, photo_type, created_at
                """,
                (user_id, web_id, storage_key, caption, photo_type, project_id, hero_id),
            )
            return dict(cur.fetchone())


def save_project_questions(
    project_id: int,
    blocks: list[dict],
    blitz: list[str] | None = None,
    notes: str | None = None,
) -> dict:
    """
    Сохраняет новую версию доп. вопросов проекта. Версия инкрементируется.
    blocks: [{"title": "О детстве", "questions": ["...", "..."]}]
    blitz:  ["Любимое блюдо?", ...]
    """
    import json as _json
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT COALESCE(MAX(version), 0) + 1 AS v "
                "FROM project_questions WHERE project_id = %s",
                (project_id,),
            )
            v = cur.fetchone()["v"]
            cur.execute(
                """
                INSERT INTO project_questions (project_id, version, blocks_json, blitz_json, notes)
                VALUES (%s, %s, %s::jsonb, %s::jsonb, %s)
                RETURNING id, project_id, version, blocks_json, blitz_json, notes, created_at
                """,
                (project_id, v,
                 _json.dumps(blocks, ensure_ascii=False),
                 _json.dumps(blitz or [], ensure_ascii=False),
                 notes),
            )
            return dict(cur.fetchone())


def get_latest_project_questions(project_id: int) -> dict | None:
    """Последняя версия доп. вопросов или None."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, project_id, version, blocks_json, blitz_json, notes, created_at
                FROM project_questions
                WHERE project_id = %s
                ORDER BY version DESC LIMIT 1
                """,
                (project_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None


def get_project_questions(project_id: int) -> list[dict]:
    """Все версии вопросов для проекта."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, project_id, version, blocks_json, blitz_json, notes, created_at
                FROM project_questions
                WHERE project_id = %s
                ORDER BY version DESC
                """,
                (project_id,),
            )
            return [dict(r) for r in cur.fetchall()]


def save_project_book(
    project_id: int,
    storage_key: str,
    size_bytes: int | None = None,
    page_count: int | None = None,
    notes: str | None = None,
    html_storage_key: str | None = None,
    blocks_json: dict | list | None = None,
) -> dict:
    """
    Сохраняет новую версию книги для проекта. Версия инкрементируется автоматически.
    - storage_key       — ключ PDF в S3
    - html_storage_key  — ключ HTML-исходника (для fallback-редактора)
    - blocks_json       — структура книги (главы/блоки) из pipeline glava,
                          используется веб-редактором
    """
    import json as _json
    blocks_payload = _json.dumps(blocks_json, ensure_ascii=False) if blocks_json is not None else None
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT COALESCE(MAX(version), 0) + 1 AS next_version "
                "FROM project_books WHERE project_id = %s",
                (project_id,),
            )
            next_version = cur.fetchone()["next_version"]
            cur.execute(
                """
                INSERT INTO project_books
                    (project_id, version, storage_key, html_storage_key,
                     size_bytes, page_count, notes, blocks_json)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                RETURNING id, project_id, version, storage_key, html_storage_key,
                          size_bytes, page_count, status, notes, blocks_json, created_at
                """,
                (project_id, next_version, storage_key, html_storage_key,
                 size_bytes, page_count, notes, blocks_payload),
            )
            return dict(cur.fetchone())


def save_edited_book_version(
    project_id: int,
    pdf_storage_key: str,
    html_storage_key: str,
    size_bytes: int | None,
    page_count: int | None,
    edited_by_user_id: int,
    notes: str | None = None,
    blocks_json: dict | list | None = None,
) -> dict:
    """
    Сохраняет новую версию книги после редактирования клиентом в кабинете.
    Помечает edited_at = NOW(), edited_by_user_id. Сохраняет blocks_json если задан.
    """
    import json as _json
    blocks_payload = _json.dumps(blocks_json, ensure_ascii=False) if blocks_json is not None else None
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT COALESCE(MAX(version), 0) + 1 AS v "
                "FROM project_books WHERE project_id = %s",
                (project_id,),
            )
            v = cur.fetchone()["v"]
            cur.execute(
                """
                INSERT INTO project_books
                    (project_id, version, storage_key, html_storage_key,
                     size_bytes, page_count, notes, blocks_json,
                     edited_at, edited_by_user_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, NOW(), %s)
                RETURNING id, project_id, version, storage_key, html_storage_key,
                          size_bytes, page_count, status, notes, blocks_json,
                          edited_at, edited_by_user_id, created_at
                """,
                (project_id, v, pdf_storage_key, html_storage_key,
                 size_bytes, page_count, notes, blocks_payload, edited_by_user_id),
            )
            return dict(cur.fetchone())


def get_latest_project_book(project_id: int) -> dict | None:
    """Возвращает последнюю (по version) книгу проекта или None."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, project_id, version, storage_key, html_storage_key,
                       size_bytes, page_count, status, notes, blocks_json,
                       edited_at, edited_by_user_id, created_at
                FROM project_books
                WHERE project_id = %s
                ORDER BY version DESC
                LIMIT 1
                """,
                (project_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None


def get_project_books(project_id: int) -> list[dict]:
    """Все версии книги для проекта (свежие первыми). blocks_json НЕ включаем
    (тяжёлое поле; для конкретной версии — get_latest_project_book или get_project_book_version)."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT pb.id, pb.project_id, pb.version, pb.storage_key, pb.html_storage_key,
                       pb.size_bytes, pb.page_count, pb.status, pb.notes,
                       pb.edited_at, pb.edited_by_user_id, pb.created_at,
                       (pb.blocks_json IS NOT NULL) AS has_blocks_json,
                       u.email AS edited_by_email
                FROM project_books pb
                LEFT JOIN users u ON u.id = pb.edited_by_user_id
                WHERE pb.project_id = %s
                ORDER BY pb.version DESC
                """,
                (project_id,),
            )
            return [dict(r) for r in cur.fetchall()]


def get_project_book_version(project_id: int, version: int) -> dict | None:
    """Одна конкретная версия книги с blocks_json."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, project_id, version, storage_key, html_storage_key,
                       size_bytes, page_count, status, notes, blocks_json,
                       edited_at, edited_by_user_id, created_at
                FROM project_books
                WHERE project_id = %s AND version = %s
                """,
                (project_id, version),
            )
            row = cur.fetchone()
            return dict(row) if row else None


def consume_magic_link_token(token: str) -> dict | None:
    """
    Проверяет токен и помечает использованным.
    Возвращает {user_id, purpose} если токен валиден и не истёк, иначе None.
    Атомарно: повторный вызов с тем же токеном вернёт None.
    """
    if not token:
        return None
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Атомарно: помечаем used_at только если не использован и не истёк
            cur.execute(
                """
                UPDATE magic_link_tokens
                SET used_at = NOW()
                WHERE token = %s
                  AND used_at IS NULL
                  AND expires_at > NOW()
                RETURNING user_id, purpose
                """,
                (token,),
            )
            row = cur.fetchone()
            return dict(row) if row else None
