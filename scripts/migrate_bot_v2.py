"""
Миграция БД для bot scenario v2 (spec Даши).

Добавляет поля:
  draft_orders: character_relation, narrators, bot_state, revision_count,
                pending_revision, revision_deadline
  photos:       photo_type, narrator_id
  voice_messages: narrator_id, interview_round

Запуск:
  cd /opt/glava && set -a && source .env && set +a
  source .venv/bin/activate
  python scripts/migrate_bot_v2.py
"""
import os
import psycopg2

DATABASE_URL = os.environ["DATABASE_URL"]


def run():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    cur = conn.cursor()

    print("Миграция bot_v2: добавляем поля в draft_orders...")
    cur.execute("""
        ALTER TABLE draft_orders
            ADD COLUMN IF NOT EXISTS character_relation TEXT,
            ADD COLUMN IF NOT EXISTS narrators           JSONB DEFAULT '[]',
            ADD COLUMN IF NOT EXISTS bot_state           VARCHAR(50) DEFAULT 'no_project',
            ADD COLUMN IF NOT EXISTS revision_count      INTEGER DEFAULT 0,
            ADD COLUMN IF NOT EXISTS pending_revision    TEXT,
            ADD COLUMN IF NOT EXISTS revision_deadline   TIMESTAMPTZ;
    """)
    print("  draft_orders OK")

    print("Добавляем поля в photos...")
    cur.execute("""
        ALTER TABLE photos
            ADD COLUMN IF NOT EXISTS photo_type  VARCHAR(20) DEFAULT 'photo',
            ADD COLUMN IF NOT EXISTS narrator_id VARCHAR(50);
    """)
    print("  photos OK")

    print("Добавляем поля в voice_messages...")
    cur.execute("""
        ALTER TABLE voice_messages
            ADD COLUMN IF NOT EXISTS narrator_id     VARCHAR(50),
            ADD COLUMN IF NOT EXISTS interview_round INTEGER DEFAULT 1;
    """)
    print("  voice_messages OK")

    print("Обновляем VALID_STATES в project_states: добавляем новые состояния...")
    # Таблица project_states уже существует — просто убедимся что поле state VARCHAR достаточно
    cur.execute("""
        ALTER TABLE project_states
            ALTER COLUMN state TYPE VARCHAR(60);
    """)
    print("  project_states OK")

    conn.commit()
    cur.close()
    conn.close()
    print("Миграция bot_v2 завершена успешно.")


if __name__ == "__main__":
    run()
