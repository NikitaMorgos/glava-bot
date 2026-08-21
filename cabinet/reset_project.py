"""
Сброс проекта в начальное состояние — для тестирования обработки.

Что делает:
- Снимает materials_submitted_at (проект снова можно править)
- Удаляет все стадии обработки (project_job_stages)
- Удаляет все опубликованные книги (project_books) + файлы из S3
- Удаляет все доп. вопросы (project_questions)

Что НЕ трогает:
- Сам проект, рассказчиков, голосовые, фото — они остаются на месте

Использование:
  python -m cabinet.reset_project --project-id 8
  python -m cabinet.reset_project --project-id 8 --keep-s3   # не трогать S3
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("reset")


def reset(project_id: int, keep_s3: bool = False) -> int:
    # Соберём storage_keys книг, чтобы потом удалить из S3
    book_keys: list[str] = []
    if not keep_s3:
        for b in db.get_project_books(project_id):
            if b.get("storage_key"):
                book_keys.append(b["storage_key"])
            if b.get("html_storage_key"):
                book_keys.append(b["html_storage_key"])

    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE projects SET materials_submitted_at = NULL WHERE id = %s",
                (project_id,),
            )
            cur.execute("DELETE FROM project_job_stages WHERE project_id = %s", (project_id,))
            n_stages = cur.rowcount
            cur.execute("DELETE FROM project_books WHERE project_id = %s", (project_id,))
            n_books = cur.rowcount
            cur.execute("DELETE FROM project_questions WHERE project_id = %s", (project_id,))
            n_questions = cur.rowcount

    logger.info("✅ Проект %s сброшен:", project_id)
    logger.info("   - materials_submitted_at = NULL")
    logger.info("   - стадий удалено: %s", n_stages)
    logger.info("   - книг удалено: %s", n_books)
    logger.info("   - наборов вопросов удалено: %s", n_questions)

    if book_keys and not keep_s3:
        try:
            import storage
            for key in book_keys:
                try:
                    storage.delete_object(key)
                    logger.info("   S3: удалён %s", key)
                except Exception as e:
                    logger.warning("   S3: не удалось %s: %s", key, e)
        except Exception as e:
            logger.warning("Не удалось подключиться к S3 (книги не удалены): %s", e)

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Сброс проекта для повторной обработки")
    parser.add_argument("--project-id", type=int, required=True)
    parser.add_argument("--keep-s3", action="store_true",
                        help="Не удалять book.pdf/book.html из S3 (по умолчанию удаляет)")
    args = parser.parse_args()
    return reset(args.project_id, keep_s3=args.keep_s3)


if __name__ == "__main__":
    sys.exit(main())
