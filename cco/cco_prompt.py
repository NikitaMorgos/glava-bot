# -*- coding: utf-8 -*-
"""Системный промпт CCO-агента: промпт из БД + база знаний из файлов + метрики."""
import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_KB_PATH = _PROJECT_ROOT / "tasks" / "support-bot" / "docs" / "KNOWLEDGE_BASE.md"
_TOV_PATH = _PROJECT_ROOT / "tasks" / "support-bot" / "docs" / "TONE_OF_VOICE.md"

_cache: dict[str, tuple[str, float]] = {}
_CACHE_TTL = 300


def _read_file(path: Path) -> str:
    key = str(path)
    now = time.time()
    cached = _cache.get(key)
    if cached and (now - cached[1]) < _CACHE_TTL:
        return cached[0]
    try:
        text = path.read_text(encoding="utf-8")
        _cache[key] = (text, now)
        return text
    except Exception as e:
        logger.warning("Cannot read %s: %s", path, e)
        return ""


def _get_db_prompt() -> str:
    """Читает промпт CCO из таблицы prompts."""
    try:
        import sys
        sys.path.insert(0, str(_PROJECT_ROOT))
        from admin.db_admin import get_prompt
        p = get_prompt("cco_agent")
        if p:
            return p["prompt_text"]
    except Exception as e:
        logger.warning("Cannot read CCO prompt from DB: %s", e)
    return ""


def get_system_prompt(metrics_text: str = "") -> str:
    """Собирает полный системный промпт для CCO."""
    prompt = _get_db_prompt()
    if not prompt:
        prompt = "Ты — CCO (Chief Customer Officer) сервиса ГЛАВА. Отвечай на вопросы команды."

    kb = _read_file(_KB_PATH)
    tov = _read_file(_TOV_PATH)

    parts = [prompt]

    if kb:
        parts.append("\n\n--- БАЗА ЗНАНИЙ О СЕРВИСЕ ---\n\n" + kb)
    if tov:
        parts.append("\n\n--- ТОН ОБЩЕНИЯ ---\n\n" + tov)
    if metrics_text:
        parts.append("\n\n--- АКТУАЛЬНЫЕ ДАННЫЕ ---\n\n" + metrics_text)

    return "\n".join(parts)
