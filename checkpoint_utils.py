#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
checkpoint_utils.py — Система чекпоинтов пайплайна Glava.

Проблема, которую решает:
  Два пайплайна (бот/БД и локальные скрипты) писали в разные места,
  нет маркера «это финал», build-скрипты читали по glob и могли
  взять любой файл.

Решение:
  Каждый этап пайплайна сохраняет свой вывод как чекпоинт:
    checkpoints/{project}/{stage}.json       — последний результат
    checkpoints/{project}/{stage}.approved   — флаг одобрения (пустой файл)

  «Одобрить» = зафиксировать этот результат как источник истины для
  следующих этапов. Только одобренный чекпоинт используется в build-скриптах.

Структура чекпоинта (JSON):
  {
    "project":    "karakulina",
    "stage":      "proofreader",           # cleaner | fact_map | ghostwriter |
                                            # liteditor | proofreader | layout
    "version":    3,                        # инкрементируется при каждом save
    "saved_at":   "2026-03-29T06:53:32",
    "approved_at": "2026-03-29T10:00:00",  # null если не одобрен
    "transcript_hash": "sha256:...",        # хэш входного транскрипта
    "transcript_len":  11539,
    "source_file": "exports/karakulina_proofreader_report_20260329_065332.json",
    "content":    { ... }                   # фактический JSON-вывод агента
  }

Использование:
  from checkpoint_utils import save_checkpoint, load_approved, approve_checkpoint

  # В конце каждого этапа пайплайна:
  save_checkpoint("karakulina", "proofreader", result_dict,
                  transcript_len=11539, source_file=str(out_path))

  # В build-скриптах вместо glob:
  data = load_approved("karakulina", "proofreader")

  # Одобрить вручную:
  approve_checkpoint("karakulina", "proofreader")

  # Или через CLI:
  python scripts/checkpoint_save.py approve karakulina proofreader
  python scripts/checkpoint_save.py list karakulina
"""

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parent
CHECKPOINTS_DIR = ROOT / "checkpoints"


# ─────────────────────────────────────────────────────────────────
# Вспомогательные функции
# ─────────────────────────────────────────────────────────────────

def _project_dir(project: str) -> Path:
    d = CHECKPOINTS_DIR / project
    d.mkdir(parents=True, exist_ok=True)
    return d


def _checkpoint_path(project: str, stage: str) -> Path:
    return _project_dir(project) / f"{stage}.json"


def _approved_flag(project: str, stage: str) -> Path:
    return _project_dir(project) / f"{stage}.approved"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _hash_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode()).hexdigest()[:16]


# ─────────────────────────────────────────────────────────────────
# Основные функции
# ─────────────────────────────────────────────────────────────────

def save_checkpoint(
    project: str,
    stage: str,
    content: Any,
    *,
    transcript_text: Optional[str] = None,
    transcript_len: Optional[int] = None,
    source_file: Optional[str] = None,
    auto_approve: bool = False,
) -> Path:
    """
    Сохраняет результат этапа как чекпоинт.

    Если чекпоинт уже существует — увеличивает version.
    Флаг одобрения при save НЕ сбрасывается (одобренный остаётся одобренным
    до явного revoke или нового approve).

    Возвращает путь к файлу чекпоинта.
    """
    path = _checkpoint_path(project, stage)

    # Читаем предыдущую версию для инкремента
    version = 1
    prev_approved_at = None
    if path.exists():
        try:
            prev = json.loads(path.read_text(encoding="utf-8"))
            version = prev.get("version", 0) + 1
            prev_approved_at = prev.get("approved_at")
        except Exception:
            pass

    checkpoint = {
        "project": project,
        "stage": stage,
        "version": version,
        "saved_at": _now(),
        "approved_at": prev_approved_at,  # сохраняем если был одобрен
        "transcript_hash": _hash_text(transcript_text) if transcript_text else None,
        "transcript_len": transcript_len or (len(transcript_text) if transcript_text else None),
        "source_file": source_file,
        "content": content,
    }

    path.write_text(json.dumps(checkpoint, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[CHECKPOINT] Sokhranyon: {project}/{stage} v{version} -> {path}")

    if auto_approve:
        approve_checkpoint(project, stage)

    return path


def approve_checkpoint(
    project: str,
    stage: str,
    *,
    regression_passed: bool | None = None,
    regression_report_path: str | None = None,
) -> Path:
    """
    Помечает чекпоинт как одобренный.

    Одобренный чекпоинт — единственный источник истины для build-скриптов
    и следующих этапов пайплайна. Не одобрять автоматически — только вручную.

    regression_passed: True/False если regression suite прогонялся, None — не прогонялся.
    regression_report_path: путь к JSON-отчёту regression suite.
    """
    path = _checkpoint_path(project, stage)
    if not path.exists():
        raise FileNotFoundError(f"Чекпоинт не найден: {project}/{stage}")

    data = json.loads(path.read_text(encoding="utf-8"))
    data["approved_at"] = _now()
    data["regression_passed"] = regression_passed
    data["regression_report_path"] = regression_report_path

    if regression_passed is None:
        print(f"[CHECKPOINT] ⚠️  regression suite не прогонялся при approve {project}/{stage}")
    elif not regression_passed:
        print(f"[CHECKPOINT] ❌ regression suite FAILED при approve {project}/{stage}")

    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # Флаг-файл для быстрой проверки без парсинга JSON
    flag = _approved_flag(project, stage)
    flag.write_text(data["approved_at"], encoding="utf-8")

    print(f"[CHECKPOINT] OK Odobren: {project}/{stage} v{data['version']} @ {data['approved_at']}"
          + (f" | regression={'PASS' if regression_passed else 'SKIP' if regression_passed is None else 'FAIL'}"
             if regression_passed is not None or regression_passed is None else ""))
    return path


def revoke_checkpoint(project: str, stage: str) -> None:
    """Снимает одобрение с чекпоинта."""
    path = _checkpoint_path(project, stage)
    if not path.exists():
        raise FileNotFoundError(f"Чекпоинт не найден: {project}/{stage}")

    data = json.loads(path.read_text(encoding="utf-8"))
    data["approved_at"] = None
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    flag = _approved_flag(project, stage)
    if flag.exists():
        flag.unlink()

    print(f"[CHECKPOINT] WARN Odobreniye snyato: {project}/{stage}")


def load_checkpoint(project: str, stage: str, require_approved: bool = False) -> dict:
    """
    Загружает чекпоинт.

    require_approved=True — упадёт если чекпоинт не одобрен.
    Это защита от случайного использования черновых данных в build-скриптах.
    """
    path = _checkpoint_path(project, stage)
    if not path.exists():
        raise FileNotFoundError(
            f"Чекпоинт {project}/{stage} не найден.\n"
            f"Запустите соответствующий этап пайплайна или:\n"
            f"  python scripts/checkpoint_save.py save {project} {stage} <file>"
        )

    data = json.loads(path.read_text(encoding="utf-8"))

    if require_approved and not data.get("approved_at"):
        raise RuntimeError(
            f"Чекпоинт {project}/{stage} v{data['version']} не одобрен!\n"
            f"Для одобрения: python scripts/checkpoint_save.py approve {project} {stage}\n"
            f"Сохранён: {data.get('saved_at')}"
        )

    return data


def load_approved(project: str, stage: str) -> Any:
    """
    Загружает content одобренного чекпоинта.
    Удобная обёртка для build-скриптов.
    """
    return load_checkpoint(project, stage, require_approved=True)["content"]


def is_approved(project: str, stage: str) -> bool:
    """Быстрая проверка: одобрен ли чекпоинт."""
    flag = _approved_flag(project, stage)
    return flag.exists()


def list_checkpoints(project: Optional[str] = None) -> list[dict]:
    """Возвращает список всех чекпоинтов (или только указанного проекта)."""
    results = []
    search_root = CHECKPOINTS_DIR / project if project else CHECKPOINTS_DIR

    if not search_root.exists():
        return results

    for cp_file in sorted(search_root.rglob("*.json")):
        try:
            data = json.loads(cp_file.read_text(encoding="utf-8"))
            results.append({
                "project":     data.get("project", cp_file.parent.name),
                "stage":       data.get("stage", cp_file.stem),
                "version":     data.get("version"),
                "saved_at":    data.get("saved_at"),
                "approved_at": data.get("approved_at"),
                "transcript_len": data.get("transcript_len"),
                "source_file": data.get("source_file"),
            })
        except Exception:
            pass

    return results
