"""
DB-функции для SMM-редакции v2.
Таблицы: smm_content_plans, smm_posts, smm_platforms (legacy),
         smm_rubrics, smm_platform_formats, smm_journalists,
         smm_journalist_rubrics, smm_journalist_pformats.
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
    """Создаёт все таблицы если их нет (idempotent)."""
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            -- legacy: площадки (для обратной совместимости)
            CREATE TABLE IF NOT EXISTS smm_platforms (
                id         SERIAL PRIMARY KEY,
                slug       TEXT UNIQUE NOT NULL,
                name       TEXT NOT NULL,
                is_active  BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS smm_rubrics (
                id         SERIAL PRIMARY KEY,
                slug       TEXT UNIQUE NOT NULL,
                name       TEXT NOT NULL,
                is_active  BOOLEAN NOT NULL DEFAULT TRUE,
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );

            -- v2: площадка_формат — единая сущность
            CREATE TABLE IF NOT EXISTS smm_platform_formats (
                id            SERIAL PRIMARY KEY,
                slug          TEXT UNIQUE NOT NULL,
                platform_name TEXT NOT NULL,
                format_name   TEXT NOT NULL,
                is_active     BOOLEAN NOT NULL DEFAULT TRUE,
                sort_order    INTEGER NOT NULL DEFAULT 0,
                created_at    TIMESTAMPTZ DEFAULT NOW()
            );

            -- v2: журналисты
            CREATE TABLE IF NOT EXISTS smm_journalists (
                id         SERIAL PRIMARY KEY,
                slug       TEXT UNIQUE NOT NULL,
                name       TEXT NOT NULL,
                model_provider TEXT NOT NULL DEFAULT 'openai',
                is_active  BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );

            -- v2: назначения журналистов на рубрики (M:N)
            CREATE TABLE IF NOT EXISTS smm_journalist_rubrics (
                journalist_id INTEGER REFERENCES smm_journalists(id) ON DELETE CASCADE,
                rubric_id     INTEGER REFERENCES smm_rubrics(id) ON DELETE CASCADE,
                PRIMARY KEY (journalist_id, rubric_id)
            );

            -- v2: назначения журналистов на площадки_форматы (M:N)
            CREATE TABLE IF NOT EXISTS smm_journalist_pformats (
                journalist_id      INTEGER REFERENCES smm_journalists(id) ON DELETE CASCADE,
                platform_format_id INTEGER REFERENCES smm_platform_formats(id) ON DELETE CASCADE,
                PRIMARY KEY (journalist_id, platform_format_id)
            );

            CREATE TABLE IF NOT EXISTS smm_content_plans (
                id           SERIAL PRIMARY KEY,
                created_at   TIMESTAMPTZ DEFAULT NOW(),
                week_start   DATE,
                status       TEXT NOT NULL DEFAULT 'draft',
                manual_ideas TEXT DEFAULT '',
                raw_plan     JSONB DEFAULT '[]',
                platform_id  INTEGER REFERENCES smm_platforms(id) ON DELETE SET NULL
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

        # Миграции: новые колонки в smm_posts
        for col, typ in [
            ("journalist_id", "INTEGER REFERENCES smm_journalists(id) ON DELETE SET NULL"),
            ("platform_format_id", "INTEGER REFERENCES smm_platform_formats(id) ON DELETE SET NULL"),
            ("rubric_id", "INTEGER REFERENCES smm_rubrics(id) ON DELETE SET NULL"),
            ("publish_date", "DATE"),
            ("last_error", "TEXT DEFAULT ''"),
        ]:
            cur.execute(f"""
                ALTER TABLE smm_posts
                    ADD COLUMN IF NOT EXISTS {col} {typ};
            """)
        cur.execute("""
            ALTER TABLE smm_journalists
                ADD COLUMN IF NOT EXISTS model_provider TEXT NOT NULL DEFAULT 'openai';
        """)

        # Миграция legacy
        cur.execute("""
            ALTER TABLE smm_content_plans
                ADD COLUMN IF NOT EXISTS platform_id INTEGER
                    REFERENCES smm_platforms(id) ON DELETE SET NULL;
        """)

        # Seed: площадка Дзен
        cur.execute("""
            INSERT INTO smm_platforms (slug, name)
            VALUES ('dzen', 'Яндекс Дзен')
            ON CONFLICT (slug) DO NOTHING;
        """)


# ── Площадки/Форматы (v2) ────────────────────────────────────────────────────

def get_all_platform_formats() -> list[dict]:
    ensure_tables()
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM smm_platform_formats ORDER BY sort_order, id")
        return [dict(r) for r in cur.fetchall()]


def get_active_platform_formats(platform_name: Optional[str] = None) -> list[dict]:
    with _conn() as conn:
        cur = conn.cursor()
        if platform_name:
            cur.execute(
                "SELECT * FROM smm_platform_formats WHERE is_active = TRUE AND platform_name = %s ORDER BY sort_order, id",
                (platform_name,),
            )
        else:
            cur.execute(
                "SELECT * FROM smm_platform_formats WHERE is_active = TRUE ORDER BY sort_order, id"
            )
        return [dict(r) for r in cur.fetchall()]


def get_platform_format(pf_id: int) -> Optional[dict]:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM smm_platform_formats WHERE id = %s", (pf_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def get_platform_format_by_slug(slug: str) -> Optional[dict]:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM smm_platform_formats WHERE slug = %s", (slug,))
        row = cur.fetchone()
        return dict(row) if row else None


def upsert_platform_format(slug: str, platform_name: str, format_name: str, sort_order: int = 0) -> int:
    ensure_tables()
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO smm_platform_formats (slug, platform_name, format_name, sort_order)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (slug) DO UPDATE
                SET platform_name = EXCLUDED.platform_name,
                    format_name   = EXCLUDED.format_name,
                    sort_order    = EXCLUDED.sort_order
            RETURNING id
        """, (slug, platform_name, format_name, sort_order))
        return cur.fetchone()["id"]


def toggle_platform_format(pf_id: int, is_active: bool) -> None:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE smm_platform_formats SET is_active = %s WHERE id = %s",
            (is_active, pf_id),
        )


def get_unique_platform_names() -> list[str]:
    """Уникальные названия площадок для фильтрации."""
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT DISTINCT platform_name FROM smm_platform_formats WHERE is_active = TRUE ORDER BY platform_name"
        )
        return [r["platform_name"] for r in cur.fetchall()]


# ── Журналисты (v2) ──────────────────────────────────────────────────────────

def get_all_journalists() -> list[dict]:
    ensure_tables()
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM smm_journalists ORDER BY id")
        return [dict(r) for r in cur.fetchall()]


def get_journalist(j_id: int) -> Optional[dict]:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM smm_journalists WHERE id = %s", (j_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def upsert_journalist(slug: str, name: str, model_provider: str = "openai") -> int:
    ensure_tables()
    allowed = {"openai", "anthropic", "deepseek"}
    model_provider = model_provider if model_provider in allowed else "openai"
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO smm_journalists (slug, name, model_provider)
            VALUES (%s, %s, %s)
            ON CONFLICT (slug) DO UPDATE
                SET name = EXCLUDED.name,
                    model_provider = EXCLUDED.model_provider
            RETURNING id
        """, (slug, name, model_provider))
        return cur.fetchone()["id"]


def toggle_journalist(j_id: int, is_active: bool) -> None:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE smm_journalists SET is_active = %s WHERE id = %s",
            (is_active, j_id),
        )


def get_journalist_assignments(j_id: int) -> dict:
    """Возвращает {rubric_ids: [int], pformat_ids: [int]}."""
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT rubric_id FROM smm_journalist_rubrics WHERE journalist_id = %s", (j_id,))
        rubric_ids = [r["rubric_id"] for r in cur.fetchall()]
        cur.execute("SELECT platform_format_id FROM smm_journalist_pformats WHERE journalist_id = %s", (j_id,))
        pformat_ids = [r["platform_format_id"] for r in cur.fetchall()]
        return {"rubric_ids": rubric_ids, "pformat_ids": pformat_ids}


def set_journalist_rubrics(j_id: int, rubric_ids: list[int]) -> None:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM smm_journalist_rubrics WHERE journalist_id = %s", (j_id,))
        for rid in rubric_ids:
            cur.execute(
                "INSERT INTO smm_journalist_rubrics (journalist_id, rubric_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (j_id, rid),
            )


def set_journalist_pformats(j_id: int, pformat_ids: list[int]) -> None:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM smm_journalist_pformats WHERE journalist_id = %s", (j_id,))
        for pfid in pformat_ids:
            cur.execute(
                "INSERT INTO smm_journalist_pformats (journalist_id, platform_format_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (j_id, pfid),
            )


def find_journalist(rubric_id: Optional[int], platform_format_id: Optional[int]) -> Optional[dict]:
    """
    Ищет активного журналиста, назначенного на рубрику И площадку_формат.
    Fallback-порядок: оба совпадения → только рубрика → только формат → первый активный.
    """
    with _conn() as conn:
        cur = conn.cursor()

        # Точное совпадение: оба
        if rubric_id and platform_format_id:
            cur.execute("""
                SELECT j.* FROM smm_journalists j
                JOIN smm_journalist_rubrics jr   ON jr.journalist_id = j.id AND jr.rubric_id = %s
                JOIN smm_journalist_pformats jp  ON jp.journalist_id = j.id AND jp.platform_format_id = %s
                WHERE j.is_active = TRUE
                ORDER BY j.id LIMIT 1
            """, (rubric_id, platform_format_id))
            row = cur.fetchone()
            if row:
                return dict(row)

        # Fallback: только рубрика
        if rubric_id:
            cur.execute("""
                SELECT j.* FROM smm_journalists j
                JOIN smm_journalist_rubrics jr ON jr.journalist_id = j.id AND jr.rubric_id = %s
                WHERE j.is_active = TRUE
                ORDER BY j.id LIMIT 1
            """, (rubric_id,))
            row = cur.fetchone()
            if row:
                return dict(row)

        # Fallback: только формат
        if platform_format_id:
            cur.execute("""
                SELECT j.* FROM smm_journalists j
                JOIN smm_journalist_pformats jp ON jp.journalist_id = j.id AND jp.platform_format_id = %s
                WHERE j.is_active = TRUE
                ORDER BY j.id LIMIT 1
            """, (platform_format_id,))
            row = cur.fetchone()
            if row:
                return dict(row)

        # Последний fallback: первый активный журналист
        cur.execute("SELECT * FROM smm_journalists WHERE is_active = TRUE ORDER BY id LIMIT 1")
        row = cur.fetchone()
        return dict(row) if row else None


# ── Площадки (legacy, обратная совместимость) ─────────────────────────────────

def get_all_platforms() -> list[dict]:
    ensure_tables()
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM smm_platforms ORDER BY id")
        return [dict(r) for r in cur.fetchall()]


def get_platform(slug: str) -> Optional[dict]:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM smm_platforms WHERE slug = %s", (slug,))
        row = cur.fetchone()
        return dict(row) if row else None


def upsert_platform(slug: str, name: str) -> int:
    ensure_tables()
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO smm_platforms (slug, name)
            VALUES (%s, %s)
            ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name
            RETURNING id
        """, (slug, name))
        return cur.fetchone()["id"]


def toggle_platform(platform_id: int, is_active: bool) -> None:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE smm_platforms SET is_active = %s WHERE id = %s",
            (is_active, platform_id),
        )


# ── Рубрики ────────────────────────────────────────────────────────────────────

def get_all_rubrics() -> list[dict]:
    ensure_tables()
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM smm_rubrics ORDER BY sort_order, id")
        return [dict(r) for r in cur.fetchall()]


def get_active_rubrics() -> list[dict]:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM smm_rubrics WHERE is_active = TRUE ORDER BY sort_order, id"
        )
        return [dict(r) for r in cur.fetchall()]


def upsert_rubric(slug: str, name: str, sort_order: int = 0) -> int:
    ensure_tables()
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO smm_rubrics (slug, name, sort_order)
            VALUES (%s, %s, %s)
            ON CONFLICT (slug) DO UPDATE
                SET name = EXCLUDED.name,
                    sort_order = EXCLUDED.sort_order
            RETURNING id
        """, (slug, name, sort_order))
        return cur.fetchone()["id"]


def toggle_rubric(rubric_id: int, is_active: bool) -> None:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE smm_rubrics SET is_active = %s WHERE id = %s",
            (is_active, rubric_id),
        )


# ── Контент-планы ──────────────────────────────────────────────────────────────

def create_plan(
    week_start: Optional[str] = None,
    manual_ideas: str = "",
    platform_slug: Optional[str] = None,
) -> int:
    ensure_tables()
    platform_id: Optional[int] = None
    if platform_slug:
        p = get_platform(platform_slug)
        if p:
            platform_id = p["id"]
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO smm_content_plans (week_start, status, manual_ideas, platform_id)
            VALUES (%s, 'draft', %s, %s) RETURNING id
        """, (week_start or None, manual_ideas, platform_id))
        return cur.fetchone()["id"]


def get_latest_plans(limit: int = 10) -> list[dict]:
    ensure_tables()
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT cp.*,
                   COUNT(p.id) AS posts_count,
                   pl.name     AS platform_name,
                   pl.slug     AS platform_slug
            FROM smm_content_plans cp
            LEFT JOIN smm_posts p    ON p.plan_id = cp.id
            LEFT JOIN smm_platforms pl ON pl.id = cp.platform_id
            GROUP BY cp.id, pl.name, pl.slug
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

def create_post(
    plan_id: int,
    topic: str,
    channel: str = "dzen",
    rubric_slug: Optional[str] = None,
    platform_format_slug: Optional[str] = None,
) -> int:
    """Создаёт пост, при наличии связывает с рубрикой и площадкой_форматом."""
    ensure_tables()
    rubric_id: Optional[int] = None
    pf_id: Optional[int] = None

    if rubric_slug:
        with _conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM smm_rubrics WHERE slug = %s", (rubric_slug,))
            row = cur.fetchone()
            if row:
                rubric_id = row["id"]

    if platform_format_slug:
        with _conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM smm_platform_formats WHERE slug = %s", (platform_format_slug,))
            row = cur.fetchone()
            if row:
                pf_id = row["id"]

    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO smm_posts (plan_id, topic, channel, status, rubric_id, platform_format_id)
            VALUES (%s, %s, %s, 'draft', %s, %s) RETURNING id
        """, (plan_id, topic, channel, rubric_id, pf_id))
        return cur.fetchone()["id"]


def get_post(post_id: int) -> Optional[dict]:
    ensure_tables()
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT p.*,
                   pl.name AS platform_name, pl.slug AS platform_slug,
                   r.name  AS rubric_name,   r.slug  AS rubric_slug_val,
                   pf.platform_name AS pf_platform, pf.format_name AS pf_format, pf.slug AS pf_slug,
                   j.name  AS journalist_name, j.slug AS journalist_slug,
                   j.model_provider AS journalist_model_provider
            FROM smm_posts p
            LEFT JOIN smm_content_plans cp ON cp.id = p.plan_id
            LEFT JOIN smm_platforms pl     ON pl.id = cp.platform_id
            LEFT JOIN smm_rubrics r        ON r.id  = p.rubric_id
            LEFT JOIN smm_platform_formats pf ON pf.id = p.platform_format_id
            LEFT JOIN smm_journalists j    ON j.id  = p.journalist_id
            WHERE p.id = %s
        """, (post_id,))
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


def get_all_posts(
    limit: int = 50,
    platform_slug: Optional[str] = None,
    platform_name_filter: Optional[str] = None,
) -> list[dict]:
    ensure_tables()
    with _conn() as conn:
        cur = conn.cursor()
        base = """
            SELECT p.*, c.week_start,
                   pl.name AS platform_name, pl.slug AS platform_slug,
                   r.name  AS rubric_name,
                   pf.platform_name AS pf_platform, pf.format_name AS pf_format,
                   j.name  AS journalist_name
            FROM smm_posts p
            LEFT JOIN smm_content_plans c  ON c.id = p.plan_id
            LEFT JOIN smm_platforms pl     ON pl.id = c.platform_id
            LEFT JOIN smm_rubrics r        ON r.id  = p.rubric_id
            LEFT JOIN smm_platform_formats pf ON pf.id = p.platform_format_id
            LEFT JOIN smm_journalists j    ON j.id  = p.journalist_id
            WHERE p.status != 'deleted'
        """
        params: list = []
        if platform_name_filter:
            base += " AND pf.platform_name = %s"
            params.append(platform_name_filter)
        elif platform_slug:
            base += " AND pl.slug = %s"
            params.append(platform_slug)
        base += " ORDER BY COALESCE(p.publish_date, '2099-12-31') ASC, p.created_at DESC LIMIT %s"
        params.append(limit)
        cur.execute(base, params)
        return [dict(r) for r in cur.fetchall()]


_ALLOWED_POST_FIELDS = frozenset({
    "status", "topic", "article_title", "article_body",
    "editor_feedback", "image_prompt", "image_url",
    "published_url", "published_at",
    "journalist_id", "platform_format_id", "rubric_id", "publish_date",
    "last_error",
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


def delete_post(post_id: int) -> None:
    """Мягкое удаление — ставит статус deleted."""
    update_post(post_id, status="deleted")


def set_publish_date(post_id: int, publish_date: Optional[str]) -> None:
    """Назначает или снимает дату публикации."""
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE smm_posts SET publish_date = %s, updated_at = NOW() WHERE id = %s",
            (publish_date or None, post_id),
        )


# ── Отзывы клиентов (источник для Scout) ──────────────────────────────────────

def get_recent_reviews(limit: int = 10) -> list[str]:
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


def get_recent_topic_titles(limit: int = 500, platform_name: Optional[str] = None) -> list[str]:
    """
    Возвращает последние темы/заголовки для анти-дублей у Scout.
    Берём и topic, и article_title, исключая удалённые.
    """
    ensure_tables()
    with _conn() as conn:
        cur = conn.cursor()
        where = "WHERE p.status != 'deleted'"
        params: list = []
        if platform_name:
            where += " AND pf.platform_name = %s"
            params.append(platform_name)
        params.append(limit)
        cur.execute(
            f"""
            SELECT COALESCE(NULLIF(TRIM(p.article_title), ''), TRIM(p.topic)) AS title
            FROM smm_posts p
            LEFT JOIN smm_platform_formats pf ON pf.id = p.platform_format_id
            {where}
            ORDER BY p.created_at DESC
            LIMIT %s
            """,
            params,
        )
        rows = cur.fetchall()
        return [r["title"] for r in rows if r.get("title")]
