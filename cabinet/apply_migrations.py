"""
Применяет SQL-миграции кабинета к боевой БД через psycopg2.
Использует тот же DATABASE_URL что и бот (читает из .env).

Запуск:
  python -m cabinet.apply_migrations

Применяет в порядке:
  1. add_email_and_magic_links.sql
  2. add_project_books.sql
  3. add_project_books_html.sql
  4. add_project_questions.sql

Все миграции написаны с IF NOT EXISTS — повторное применение безопасно.
Каждая миграция — отдельная транзакция (если упадёт одна — другие не пострадают).
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

import db

MIGRATIONS = [
    "add_email_and_magic_links.sql",
    "add_project_books.sql",
    "add_project_books_html.sql",
    "add_project_questions.sql",
    "add_heroes_role.sql",
    "add_project_submission.sql",
    "add_project_job_stages.sql",
    "add_voice_filename.sql",
    "add_project_books_blocks_json.sql",
]


def apply_one(filename: str) -> tuple[bool, str]:
    """Применяет одну миграцию. Возвращает (success, message)."""
    path = ROOT / "sql" / filename
    if not path.exists():
        return False, f"файл не найден: {path}"
    sql_text = path.read_text(encoding="utf-8")
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql_text)
        return True, "OK"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def main() -> int:
    print("=" * 60)
    print("Применение миграций кабинета")
    print("=" * 60)
    failures = 0
    for i, mig in enumerate(MIGRATIONS, 1):
        print(f"\n[{i}/{len(MIGRATIONS)}] {mig}")
        ok, msg = apply_one(mig)
        if ok:
            print(f"          [OK]")
        else:
            print(f"          [FAIL] {msg}")
            failures += 1

    print()
    print("=" * 60)
    if failures == 0:
        print(f"Все {len(MIGRATIONS)} миграций применены успешно ✅")
        print()
        print("Дальше:")
        print("  python -m cabinet.smoke_test")
        return 0
    print(f"{failures} из {len(MIGRATIONS)} миграций не применились ❌")
    print("Проверьте сообщения об ошибках выше.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
