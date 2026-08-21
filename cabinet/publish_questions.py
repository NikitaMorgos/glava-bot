"""
CLI для публикации списка доп. вопросов проекта.

Использование:
  python -m cabinet.publish_questions --project-id 5 --from output/questions.md
  python -m cabinet.publish_questions --project-id 5 --from output/questions.md --notes "после 1-го раунда"

Парсит markdown-файл вида:

  # Дополнительные вопросы
  ## О детстве
  - Как выглядел дом в Русино?
  - Какие игры были в детстве?

  ## О работе
  - Какой был типичный день?

  # Блиц
  - Любимое блюдо?
  - Любимая песня?

Кладёт в таблицу project_questions новую версию.
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("publish_questions")


def _strip_md(s: str) -> str:
    """Убирает markdown-разметку: **bold**, *italic*, _und_, `code`."""
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
    s = re.sub(r"__(.+?)__", r"\1", s)
    s = re.sub(r"(?<!\*)\*([^*\n]+?)\*(?!\*)", r"\1", s)
    s = re.sub(r"(?<!_)_([^_\n]+?)_(?!_)", r"\1", s)
    s = re.sub(r"`([^`\n]+?)`", r"\1", s)
    return s.strip()


def parse_questions_md(text: str) -> tuple[list[dict], list[str]]:
    """
    Парсит markdown. Возвращает (blocks, blitz).
    - `## Тема` начинает новый блок
    - `# Блиц` (или содержащий "блиц"/"быстрые") переключает в режим blitz
    - `- вопрос` или `1. вопрос` — добавляется в текущий блок/блиц
    """
    blocks: list[dict] = []
    blitz: list[str] = []
    current: dict | None = None
    mode = "blocks"  # blocks | blitz

    def _is_blitz_title(t: str) -> bool:
        low = t.lower()
        return "блиц" in low or "быстр" in low

    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        # Заголовок H1: чаще всего «# Вопросы для ...» — игнорируем
        if line.startswith("# "):
            title = line[2:].strip()
            if _is_blitz_title(title):
                mode = "blitz"
                current = None
            continue
        # H2: новый блок верхнего уровня ИЛИ переключение в blitz mode
        if line.startswith("## "):
            title = _strip_md(line[3:].strip())
            if _is_blitz_title(title):
                mode = "blitz"
                current = None
                continue
            mode = "blocks"
            current = {"title": title, "questions": []}
            blocks.append(current)
            continue
        # H3: подкатегория — игнорируем заголовок, продолжаем собирать вопросы
        # в текущем блоке (или в blitz, если mode=blitz). Создаём пустой блок
        # только если на верхнем уровне ещё ничего нет.
        if line.startswith("### "):
            title = _strip_md(line[4:].strip())
            if mode == "blocks" and current is None:
                current = {"title": title, "questions": []}
                blocks.append(current)
            continue
        # вопрос - bullet или нумерованный
        m = re.match(r"^\s*(?:[-*•]|\d+[\.\)])\s+(.+)", line)
        if m:
            q = _strip_md(m.group(1).strip())
            if mode == "blitz":
                blitz.append(q)
            elif current is not None:
                current["questions"].append(q)
            else:
                # вопрос без темы — складываем в специальный блок «Общее»
                if not blocks or blocks[-1]["title"] != "Общее":
                    blocks.append({"title": "Общее", "questions": []})
                blocks[-1]["questions"].append(q)
            continue
    return blocks, blitz


def publish(md_path: Path, project_id: int, notes: str | None, reset_submission: bool = True) -> dict:
    if not md_path.exists():
        raise SystemExit(f"Файл вопросов не найден: {md_path}")

    text = md_path.read_text(encoding="utf-8")
    blocks, blitz = parse_questions_md(text)
    if not blocks and not blitz:
        raise SystemExit("Не удалось распарсить ни одного вопроса — проверь формат")

    # owner check
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM projects WHERE id = %s", (project_id,))
            if not cur.fetchone():
                raise SystemExit(f"Проект {project_id} не существует")

    rec = db.save_project_questions(
        project_id=project_id,
        blocks=blocks,
        blitz=blitz,
        notes=notes,
    )
    # Новый раунд: сбрасываем submission, клиент должен снова нажать «готово»
    # после того как догрузит ответы на доп. вопросы.
    # В round 2+ внутри worker'a НЕ сбрасываем (передаём reset_submission=False):
    # processing не должен прерваться, build-all продолжает работать.
    if reset_submission:
        db.reset_project_submission(project_id)
    logger.info("✅ Опубликовано: project=%s, version=v%s", project_id, rec["version"])
    logger.info("   Блоков: %s, всего вопросов: %s, блиц: %s",
                len(blocks), sum(len(b["questions"]) for b in blocks), len(blitz))
    for b in blocks:
        logger.info("   • %s (%s)", b["title"], len(b["questions"]))
    return rec


def main() -> None:
    parser = argparse.ArgumentParser(description="Публикация доп. вопросов в кабинет")
    parser.add_argument("--project-id", type=int, required=True)
    parser.add_argument("--from", dest="md_path", type=Path, required=True,
                        help="Путь к questions.md")
    parser.add_argument("--notes", type=str, default=None)
    args = parser.parse_args()
    publish(args.md_path, args.project_id, args.notes)


if __name__ == "__main__":
    main()
