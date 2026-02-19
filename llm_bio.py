"""
Обработка транскрипта через LLM (OpenAI) для создания биографического текста.
"""

import logging
from typing import Optional

from biographical_prompt import BIOGRAPHICAL_SYSTEM_PROMPT, get_user_message

logger = logging.getLogger(__name__)


def process_transcript_to_bio(
    transcript: str,
    api_key: str,
    model: str = "gpt-4o-mini",
) -> Optional[str]:
    """
    Преобразует транскрипт интервью в биографический текст.
    Возвращает текст или None при ошибке.
    """
    if not transcript or not transcript.strip():
        logger.warning("Пустой транскрипт")
        return None

    try:
        from openai import OpenAI
    except ImportError:
        logger.warning("openai не установлен: pip install openai")
        return None

    if not api_key:
        logger.warning("OPENAI_API_KEY не задан")
        return None

    client = OpenAI(api_key=api_key)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": BIOGRAPHICAL_SYSTEM_PROMPT},
                {"role": "user", "content": get_user_message(transcript)},
            ],
            temperature=0.3,
            max_tokens=4000,
        )
    except Exception as e:
        logger.exception("OpenAI API: %s", e)
        return None

    choice = response.choices[0] if response.choices else None
    if not choice or not choice.message:
        return None

    return (choice.message.content or "").strip()
