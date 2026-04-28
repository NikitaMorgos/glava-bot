#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
checkpoint_save.py — CLI для управления чекпоинтами пайплайна Glava.

Использование:

  # Одобрить чекпоинт (зафиксировать как источник истины)
  python scripts/checkpoint_save.py approve karakulina proofreader

  # Сохранить файл как чекпоинт и сразу одобрить
  python scripts/checkpoint_save.py save karakulina proofreader exports/karakulina_proofreader_report_20260329.json --approve

  # Сохранить текстовый файл как чекпоинт (оборачивается в {"text": "..."})
  python scripts/checkpoint_save.py save karakulina proofreader exports/karakulina_FINAL_stage3_20260329.txt --approve

  # Снять одобрение
  python scripts/checkpoint_save.py revoke karakulina proofreader

  # Показать все чекпоинты
  python scripts/checkpoint_save.py list
  python scripts/checkpoint_save.py list karakulina

  # Показать статус конкретного чекпоинта
  python scripts/checkpoint_save.py status karakulina proofreader

Соглашения:
  Этапы пайплайна (в порядке выполнения):
    cleaner       → очищенный транскрипт (Cleaner)
    fact_map      → карта фактов (Fact Extractor)
    ghostwriter   → черновик книги (Ghostwriter + Historian, 1-й проход)
    liteditor     → текст после литредактора
    proofreader   → финальный текст после корректора  ← ГЛАВНЫЙ
    layout        → план вёрстки (Layout Designer)
    pdf           → финальный PDF
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from checkpoint_utils import (
    approve_checkpoint,
    is_approved,
    list_checkpoints,
    load_checkpoint,
    revoke_checkpoint,
    save_checkpoint,
)

STAGE_ORDER = [
    "cleaner",
    "fact_map",
    "ghostwriter",
    "liteditor",
    "proofreader",
    "layout",
    "pdf",
]


def cmd_save(args):
    src = Path(args.file)
    if not src.exists():
        print(f"[ERROR] Файл не найден: {src}")
        sys.exit(1)

    raw = src.read_text(encoding="utf-8")
    # Определяем тип контента
    try:
        content = json.loads(raw)
    except json.JSONDecodeError:
        # Текстовый файл — оборачиваем
        content = {"text": raw, "_format": "plain_text"}

    path = save_checkpoint(
        args.project,
        args.stage,
        content,
        source_file=str(src),
        auto_approve=args.approve,
    )
    print(f"  Файл: {src.name}  ({len(raw)} символов)")
    if not args.approve:
        print(f"\n  Для одобрения: python scripts/checkpoint_save.py approve {args.project} {args.stage}")


def cmd_approve(args):
    regression_passed = None
    regression_report_path = None

    if not getattr(args, "skip_regression", False):
        suite_script = ROOT / "scripts" / "run_regression_suite.py"
        if suite_script.exists():
            out_dir = Path(getattr(args, "regression_output_dir", ROOT / "exports"))
            print(f"[REGRESSION] Запускаю обязательный regression suite перед approve...")
            run = subprocess.run(
                [
                    sys.executable,
                    str(suite_script),
                    "--project",
                    args.project,
                    "--stage",
                    args.stage,
                    "--output-dir",
                    str(out_dir),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=str(ROOT),
            )
            if run.stdout:
                print(run.stdout.strip())

            regression_passed = (run.returncode == 0)

            # Найдём путь к отчёту из вывода
            for line in (run.stdout or "").splitlines():
                if "regression_suite" in line and line.strip().startswith("[SAVED]"):
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        regression_report_path = parts[1].strip()

            if not regression_passed:
                if run.stderr:
                    print(run.stderr.strip())
                print("[REGRESSION] ❌ approve заблокирован: regression suite не пройден.")
                sys.exit(2)
            print("[REGRESSION] ✅ regression suite пройден.")
        else:
            print(f"[REGRESSION] ⚠️ Скрипт не найден: {suite_script} (пропуск)")
    else:
        print("[REGRESSION] ⚠️ --skip-regression: regression suite пропущен (аварийный режим)")

    try:
        approve_checkpoint(
            args.project, args.stage,
            regression_passed=regression_passed,
            regression_report_path=regression_report_path,
        )
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)


def cmd_revoke(args):
    try:
        revoke_checkpoint(args.project, args.stage)
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)


def cmd_status(args):
    try:
        data = load_checkpoint(args.project, args.stage)
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

    approved = "[OK] ODOBREN" if data.get("approved_at") else "[ ] ne odobren"
    print(f"\n{'='*55}")
    print(f"  Проект:      {data['project']}")
    print(f"  Этап:        {data['stage']}")
    print(f"  Версия:      {data['version']}")
    print(f"  Сохранён:    {data.get('saved_at', '—')}")
    print(f"  Статус:      {approved}")
    if data.get("approved_at"):
        print(f"  Одобрен:     {data['approved_at']}")
    if data.get("transcript_len"):
        print(f"  Транскрипт:  {data['transcript_len']} символов")
    if data.get("source_file"):
        print(f"  Источник:    {data['source_file']}")
    print(f"{'='*55}\n")


def cmd_list(args):
    project = getattr(args, "project", None)
    items = list_checkpoints(project)

    if not items:
        print("[INFO] Чекпоинтов нет.")
        return

    # Группируем по проекту
    by_project: dict = {}
    for item in items:
        by_project.setdefault(item["project"], []).append(item)

    for proj, stages in sorted(by_project.items()):
        print(f"\n  [dir] {proj}")
        # Сортируем по порядку этапов
        def stage_key(x):
            try:
                return STAGE_ORDER.index(x["stage"])
            except ValueError:
                return 99

        for item in sorted(stages, key=stage_key):
            approved = "[OK]" if item["approved_at"] else "    "
            tlen = f" [{item['transcript_len']} symv]" if item.get("transcript_len") else ""
            print(f"    {approved} {item['stage']:<15} v{item['version']}  {item['saved_at']}{tlen}")

    print()


def main():
    parser = argparse.ArgumentParser(
        description="Управление чекпоинтами пайплайна Glava"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # save
    p_save = sub.add_parser("save", help="Сохранить файл как чекпоинт")
    p_save.add_argument("project", help="Название проекта (karakulina, dmitriev, ...)")
    p_save.add_argument("stage", help="Этап пайплайна (proofreader, fact_map, ...)")
    p_save.add_argument("file", help="Путь к JSON или TXT файлу")
    p_save.add_argument("--approve", action="store_true", help="Сразу одобрить после сохранения")

    # approve
    p_approve = sub.add_parser("approve", help="Одобрить существующий чекпоинт")
    p_approve.add_argument("project")
    p_approve.add_argument("stage")
    p_approve.add_argument("--skip-regression", action="store_true",
                           help="Пропустить regression suite (аварийный режим)")
    p_approve.add_argument("--regression-output-dir", default=str(ROOT / "exports"),
                           help="Куда сохранять отчёт regression suite")

    # revoke
    p_revoke = sub.add_parser("revoke", help="Снять одобрение с чекпоинта")
    p_revoke.add_argument("project")
    p_revoke.add_argument("stage")

    # status
    p_status = sub.add_parser("status", help="Показать статус чекпоинта")
    p_status.add_argument("project")
    p_status.add_argument("stage")

    # list
    p_list = sub.add_parser("list", help="Показать все чекпоинты")
    p_list.add_argument("project", nargs="?", help="Фильтр по проекту (опционально)")

    args = parser.parse_args()

    dispatch = {
        "save":    cmd_save,
        "approve": cmd_approve,
        "revoke":  cmd_revoke,
        "status":  cmd_status,
        "list":    cmd_list,
    }
    dispatch[args.cmd](args)


if __name__ == "__main__":
    main()
