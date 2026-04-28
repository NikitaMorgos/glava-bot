# -*- coding: utf-8 -*-
"""
System prompt для AI-бота клиентской поддержки ГЛАВА.

Промпт строится динамически из двух markdown-файлов:
- tasks/support-bot/docs/KNOWLEDGE_BASE.md — база знаний о продукте
- tasks/support-bot/docs/TONE_OF_VOICE.md  — правила тона общения

Это позволяет команде редактировать контент без правок кода.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent
_KB_PATH = _PROJECT_ROOT / "tasks" / "support-bot" / "docs" / "KNOWLEDGE_BASE.md"
_TOV_PATH = _PROJECT_ROOT / "tasks" / "support-bot" / "docs" / "TONE_OF_VOICE.md"

_PREAMBLE = """\
Ты — бот клиентской поддержки сервиса ГЛАВА (glava.family).

Твоя задача — помогать клиентам: отвечать на вопросы о продукте, \
объяснять как пользоваться сервисом, решать проблемы.

СТРОГИЕ ПРАВИЛА:
1. Отвечай ТОЛЬКО на основе информации из базы знаний ниже. \
Если информации нет — честно скажи и предложи написать на hello@glava.family.
2. НИКОГДА не придумывай цены, сроки, функции, которых нет в базе знаний.
3. Не обсуждай внутреннее устройство системы (AI, нейросети, серверы, архитектура).
4. Не давай юридических консультаций.
5. Не обсуждай конкурентов.
6. Если клиент расстроен — прояви эмпатию, предложи конкретное решение.
7. Отвечай кратко (2–5 предложений), развёрнуто — только по просьбе.
8. Обращайся на «вы».
9. Язык — русский.

Ниже — база знаний и правила тона общения.\
"""


def _read_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.warning("Файл не найден: %s", path)
        return ""
    except Exception as e:
        logger.error("Ошибка чтения %s: %s", path, e)
        return ""


_cache: dict[str, tuple[str, float]] = {}
_CACHE_TTL = 300  # 5 минут


def get_system_prompt() -> str:
    """Собирает system prompt из файлов KB и ToV с кешированием."""
    import time
    now = time.time()

    cache_key = "system_prompt"
    if cache_key in _cache:
        text, ts = _cache[cache_key]
        if now - ts < _CACHE_TTL:
            return text

    kb = _read_file(_KB_PATH)
    tov = _read_file(_TOV_PATH)

    parts = [_PREAMBLE]
    if kb:
        parts.append("\n\n--- БАЗА ЗНАНИЙ ---\n\n" + kb)
    if tov:
        parts.append("\n\n--- ТОН ОБЩЕНИЯ ---\n\n" + tov)

    prompt = "\n".join(parts)
    _cache[cache_key] = (prompt, now)
    return prompt
