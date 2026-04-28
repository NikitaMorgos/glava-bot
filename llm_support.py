# -*- coding: utf-8 -*-
"""
LLM-модуль клиентской поддержки ГЛАВА.

Хранит историю диалогов в памяти (per telegram_id) и вызывает OpenAI.
"""

import logging
import os
import time
from typing import Optional

from support_prompt import get_system_prompt

logger = logging.getLogger(__name__)

SUPPORT_MODEL = os.getenv("SUPPORT_MODEL", "gpt-4o")
MAX_HISTORY = 20  # последних сообщений в контексте
MAX_RESPONSE_TOKENS = 600
TEMPERATURE = 0.3
TIMEOUT = 30.0

_histories: dict[int, list[dict[str, str]]] = {}
_HISTORY_EXPIRY = 3600  # 1 час без активности → сброс
_last_activity: dict[int, float] = {}


def _get_history(chat_id: int) -> list[dict[str, str]]:
    now = time.time()
    last = _last_activity.get(chat_id, 0)
    if now - last > _HISTORY_EXPIRY:
        _histories.pop(chat_id, None)
    _last_activity[chat_id] = now
    if chat_id not in _histories:
        _histories[chat_id] = []
    return _histories[chat_id]


def _trim_history(history: list[dict[str, str]]) -> list[dict[str, str]]:
    if len(history) > MAX_HISTORY:
        return history[-MAX_HISTORY:]
    return history


def clear_history(chat_id: int) -> None:
    """Очистка истории диалога."""
    _histories.pop(chat_id, None)
    _last_activity.pop(chat_id, None)


def get_support_response(
    user_message: str,
    chat_id: int,
    user_name: str = "",
    api_key: Optional[str] = None,
) -> Optional[str]:
    """
    Генерирует ответ поддержки на сообщение пользователя.

    Args:
        user_message: текст от пользователя
        chat_id: ID чата (для истории)
        user_name: имя пользователя (для контекста)
        api_key: OpenAI API key (если не передан, берётся из env)

    Returns:
        Текст ответа или None при ошибке.
    """
    key = api_key or os.getenv("OPENAI_API_KEY", "")
    if not key:
        logger.error("OPENAI_API_KEY не задан")
        return None

    try:
        from openai import OpenAI
    except ImportError:
        logger.error("openai не установлен: pip install openai")
        return None

    history = _get_history(chat_id)

    user_msg = user_message.strip()
    if user_name:
        user_content = f"[{user_name}]: {user_msg}"
    else:
        user_content = user_msg

    history.append({"role": "user", "content": user_content})
    history = _trim_history(history)
    _histories[chat_id] = history

    system_prompt = get_system_prompt()
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)

    try:
        client = OpenAI(api_key=key, timeout=TIMEOUT)
        response = client.chat.completions.create(
            model=SUPPORT_MODEL,
            messages=messages,
            max_tokens=MAX_RESPONSE_TOKENS,
            temperature=TEMPERATURE,
        )
        answer = response.choices[0].message.content or ""
        answer = answer.strip()

        history.append({"role": "assistant", "content": answer})
        _histories[chat_id] = _trim_history(history)

        return answer

    except Exception as e:
        logger.exception("Ошибка OpenAI support: %s", e)
        history.pop()
        return None
