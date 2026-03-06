"""
Обработка транскрипта через LLM (OpenAI) для создания биографического текста
и генерации уточняющих вопросов по обработанному интервью.

Доступ к OpenAI API из РФ часто блокируется — при обрывах соединения (WinError 10054)
запускайте вызывающий код на сервере за рубежом или с VPN. См. docs/OPENAI_ACCESS.md.
"""

import logging
import time
from typing import Optional

from biographical_prompt import BIOGRAPHICAL_SYSTEM_PROMPT, get_user_message
from clarifying_questions_prompt import (
    CLARIFYING_QUESTIONS_SYSTEM_PROMPT,
    get_clarifying_user_message,
)

logger = logging.getLogger(__name__)

# Таймаут для длинных запросов (сек); повторные попытки при обрыве соединения
OPENAI_TIMEOUT = 180.0
OPENAI_MAX_RETRIES = 3
OPENAI_RETRY_DELAYS = (5, 15, 30)  # паузы между попытками (сек)


def process_transcript_to_bio(
    transcript: str,
    api_key: str,
    model: Optional[str] = None,
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

    try:
        from config import OPENAI_BIO_MODEL
    except ImportError:
        OPENAI_BIO_MODEL = "gpt-4o"
    model = model or OPENAI_BIO_MODEL

    client = OpenAI(api_key=api_key, timeout=OPENAI_TIMEOUT)
    last_error = None
    for attempt in range(OPENAI_MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": BIOGRAPHICAL_SYSTEM_PROMPT},
                    {"role": "user", "content": get_user_message(transcript)},
                ],
                temperature=0.2,
                max_tokens=8192,
                stream=False,
            )
            break
        except Exception as e:
            last_error = e
            if attempt < OPENAI_MAX_RETRIES - 1:
                delay = OPENAI_RETRY_DELAYS[attempt] if attempt < len(OPENAI_RETRY_DELAYS) else 30
                logger.warning("OpenAI API попытка %s/%s: %s. Повтор через %s сек.", attempt + 1, OPENAI_MAX_RETRIES, e, delay)
                time.sleep(delay)
            else:
                logger.exception("OpenAI API: %s", e)
                return None

    choice = response.choices[0] if response.choices else None
    if not choice or not choice.message:
        return None

    return (choice.message.content or "").strip()


def generate_clarifying_questions(
    bio_text: str,
    api_key: str,
    model: str = "gpt-4o-mini",
) -> Optional[str]:
    """
    По обработанному интервью (bio_story) генерирует пул уточняющих вопросов
    для пользователя (для следующего интервью).
    Возвращает текст с вопросами или None при ошибке.
    """
    if not bio_text or not bio_text.strip():
        logger.warning("Пустой текст биографии для уточняющих вопросов")
        return None

    try:
        from openai import OpenAI
    except ImportError:
        logger.warning("openai не установлен: pip install openai")
        return None

    if not api_key:
        logger.warning("OPENAI_API_KEY не задан")
        return None

    client = OpenAI(api_key=api_key, timeout=OPENAI_TIMEOUT)
    last_error = None
    for attempt in range(OPENAI_MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": CLARIFYING_QUESTIONS_SYSTEM_PROMPT},
                    {"role": "user", "content": get_clarifying_user_message(bio_text)},
                ],
                temperature=0.3,
                max_tokens=2000,
            )
            break
        except Exception as e:
            last_error = e
            if attempt < OPENAI_MAX_RETRIES - 1:
                delay = OPENAI_RETRY_DELAYS[attempt] if attempt < len(OPENAI_RETRY_DELAYS) else 30
                logger.warning("OpenAI API (уточняющие вопросы) попытка %s/%s: %s. Повтор через %s сек.", attempt + 1, OPENAI_MAX_RETRIES, e, delay)
                time.sleep(delay)
            else:
                logger.exception("OpenAI API (уточняющие вопросы): %s", e)
                return None

    choice = response.choices[0] if response.choices else None
    if not choice or not choice.message:
        return None

    return (choice.message.content or "").strip()
