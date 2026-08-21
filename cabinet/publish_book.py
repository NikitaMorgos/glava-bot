"""
CLI для публикации готового PDF книги в кабинет.

Использование:
  python -m cabinet.publish_book --project-id 5 --pdf output/book_karakulina_v_polish.pdf
  python -m cabinet.publish_book --project-id 5 --pdf path/to/book.pdf --notes "v2 после правок по обложке"

Что делает:
1. Загружает PDF в S3 по ключу books/<project_id>/v<n>.pdf
2. Создаёт запись в project_books (version инкрементируется автоматически)
3. Выводит summary с presigned URL для проверки

Не запускает pipeline и ничего не пересобирает — это операция «опубликовать
уже готовый файл из локального output/ в кабинет, чтобы клиент мог скачать».
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

# Подгружаем .env как обычное Flask-приложение кабинета
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

import db
import storage

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("publish_book")


def _project_owner(project_id: int) -> int | None:
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT owner_user_id FROM projects WHERE id = %s", (project_id,))
            row = cur.fetchone()
            return row[0] if row else None


def publish(
    pdf_path: Path,
    project_id: int,
    notes: str | None,
    html_path: Path | None = None,
    book_json_path: Path | None = None,
) -> dict:
    if not pdf_path.exists():
        raise SystemExit(f"PDF не найден: {pdf_path}")
    if pdf_path.suffix.lower() != ".pdf":
        raise SystemExit(f"Ожидался .pdf, получен: {pdf_path.suffix}")
    if html_path is not None:
        if not html_path.exists():
            raise SystemExit(f"HTML не найден: {html_path}")
        if html_path.suffix.lower() not in {".html", ".htm"}:
            raise SystemExit(f"Ожидался .html, получен: {html_path.suffix}")
    if book_json_path is not None and not book_json_path.exists():
        logger.warning("book.json не найден по пути %s — сохраним без структуры", book_json_path)
        book_json_path = None

    owner = _project_owner(project_id)
    if owner is None:
        raise SystemExit(f"Проект {project_id} не существует")

    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COALESCE(MAX(version), 0) + 1 FROM project_books WHERE project_id = %s",
                (project_id,),
            )
            next_version = cur.fetchone()[0]

    pdf_key = f"books/{project_id}/v{next_version}.pdf"
    logger.info("Заливаю PDF %s → s3://%s", pdf_path.name, pdf_key)
    storage.upload_file_to_key(str(pdf_path), pdf_key)

    html_key = None
    if html_path is not None:
        html_key = f"books/{project_id}/v{next_version}.html"
        logger.info("Заливаю HTML %s → s3://%s", html_path.name, html_key)
        storage.upload_file_to_key(str(html_path), html_key)

    blocks_json = None
    if book_json_path is not None:
        import json as _json
        try:
            blocks_json = _json.loads(book_json_path.read_text(encoding="utf-8"))
            logger.info("Структура книги: %s глав",
                        len(blocks_json.get("chapters", [])) if isinstance(blocks_json, dict) else "?")
        except Exception as e:
            logger.warning("Не удалось прочитать book.json: %s", e)

    size_bytes = pdf_path.stat().st_size
    page_count = _try_count_pages(pdf_path)
    record = db.save_project_book(
        project_id=project_id,
        storage_key=pdf_key,
        html_storage_key=html_key,
        size_bytes=size_bytes,
        page_count=page_count,
        notes=notes,
        blocks_json=blocks_json,
    )

    url = storage.get_presigned_download_url(pdf_key, expires_in=3600)
    logger.info("Опубликовано: project=%s, version=v%s, size=%.1f МБ",
                project_id, record["version"], size_bytes / 1_048_576)
    if page_count:
        logger.info("   Страниц: %s", page_count)
    if html_key:
        logger.info("   HTML-источник: %s", html_key)
    if blocks_json:
        logger.info("   Структура книги сохранена (для редактора)")
    logger.info("   Preview URL PDF (1ч): %s", url)
    return record


def _try_count_pages(pdf_path: Path) -> int | None:
    """Опционально пытаемся посчитать страницы PDF — если pypdf доступен."""
    try:
        from pypdf import PdfReader  # type: ignore
        return len(PdfReader(str(pdf_path)).pages)
    except Exception:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Публикация PDF книги в кабинет")
    parser.add_argument("--project-id", type=int, required=True, help="ID проекта в БД")
    parser.add_argument("--pdf", type=Path, required=True, help="Путь к PDF файлу")
    parser.add_argument("--html", type=Path, default=None,
                        help="Путь к HTML-источнику (для inline-редактора)")
    parser.add_argument("--book-json", type=Path, default=None,
                        help="Путь к output/book.json из pipeline (структура для редактора)")
    parser.add_argument("--notes", type=str, default=None,
                        help="Заметка о версии (что нового), необязательно")
    args = parser.parse_args()
    publish(args.pdf, args.project_id, args.notes,
            html_path=args.html, book_json_path=args.book_json)


if __name__ == "__main__":
    main()
