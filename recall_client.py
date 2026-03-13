"""
Клиент Recall.ai API для транскрипции онлайн-встреч.

Поток:
1. Бот создаётся через POST /api/v1/bot (meeting_url)
2. Polling статуса — ждём "done"
3. Получение транскрипта — GET /api/v1/bot/{bot_id}/transcript/

Поддерживаются: Google Meet, Zoom, Microsoft Teams, Webex.
Транскрипция через AssemblyAI (поддерживает русский язык, диаризация).

Документация: https://docs.recall.ai/
"""

import logging
import time
from datetime import datetime, timezone

import requests

logger = logging.getLogger(__name__)

# Регион задаётся через RECALL_REGION в config / .env
# Доступные: us-east-1, eu-west-2, us-west-2
DEFAULT_REGION = "us-east-1"

BOT_TERMINAL_STATUSES = {"done", "fatal"}


def _base_url(region: str = DEFAULT_REGION) -> str:
    return f"https://{region}.recall.ai/api/v1"


def _headers(api_key: str) -> dict:
    return {
        "Authorization": f"Token {api_key}",
        "Content-Type": "application/json",
    }


def create_bot(
    meeting_url: str,
    api_key: str,
    bot_name: str = "GLAVA",
    region: str = DEFAULT_REGION,
    language_code: str = "ru",
    assemblyai_api_key: str = "",
) -> str | None:
    """
    Создаёт бота Recall.ai для записи встречи по ссылке.
    Возвращает bot_id или None при ошибке.

    ASR провайдер: AssemblyAI (поддерживает русский язык, диаризацию).
    """
    if not meeting_url or not meeting_url.strip():
        logger.error("recall create_bot: пустая ссылка на встречу")
        return None

    transcription_options: dict = {
        "provider": "assembly_ai",
        "assembly_ai": {
            "language_code": language_code,
        },
    }
    if assemblyai_api_key:
        transcription_options["assembly_ai"]["api_key"] = assemblyai_api_key

    payload = {
        "meeting_url": meeting_url.strip(),
        "bot_name": bot_name,
        "transcription_options": transcription_options,
        "recording_mode": "speaker_view",
    }

    try:
        resp = requests.post(
            f"{_base_url(region)}/bot",
            json=payload,
            headers=_headers(api_key),
            timeout=30,
        )
    except requests.RequestException as e:
        logger.warning("recall create_bot error: %s", e)
        return None

    if not resp.ok:
        logger.warning("recall create_bot: %s %s", resp.status_code, resp.text[:500])
        return None

    try:
        data = resp.json()
        bot_id = data.get("id")
        if bot_id:
            logger.info("recall bot created, bot_id=%s", bot_id)
            return bot_id
        logger.warning("recall create_bot: нет id в ответе: %s", data)
    except Exception as e:
        logger.warning("recall create_bot response parse: %s", e)
    return None


def get_bot_status(bot_id: str, api_key: str, region: str = DEFAULT_REGION) -> str | None:
    """
    Возвращает текущий статус бота.
    Жизненный цикл: ready → joining_call → in_call_not_recording →
                    in_call_recording → call_ended → done
    Ошибка: fatal
    """
    try:
        resp = requests.get(
            f"{_base_url(region)}/bot/{bot_id}",
            headers=_headers(api_key),
            timeout=30,
        )
        if resp.ok:
            data = resp.json()
            # Статус находится в status_changes[-1].code
            status_changes = data.get("status_changes") or []
            if status_changes:
                return status_changes[-1].get("code", "").lower()
            # Fallback — прямое поле status
            return (data.get("status") or "").lower() or None
    except requests.RequestException as e:
        logger.warning("recall get_bot_status: %s", e)
    return None


def wait_for_done(
    bot_id: str,
    api_key: str,
    region: str = DEFAULT_REGION,
    timeout_sec: int = 7200,
    poll_interval: int = 15,
) -> bool:
    """
    Ждёт статус 'done'. Возвращает True при успехе, False при fatal или таймауте.
    """
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        status = get_bot_status(bot_id, api_key, region)
        if status == "done":
            logger.info("recall bot %s: done", bot_id)
            return True
        if status == "fatal":
            logger.warning("recall bot %s: fatal", bot_id)
            return False
        logger.info("recall status: %s, ждём...", status)
        time.sleep(poll_interval)
    logger.warning("recall timeout: bot_id=%s", bot_id)
    return False


def get_transcript(
    bot_id: str,
    api_key: str,
    region: str = DEFAULT_REGION,
) -> str:
    """
    Получает транскрипт встречи.
    Возвращает текст с разбивкой по спикерам или пустую строку.
    """
    try:
        resp = requests.get(
            f"{_base_url(region)}/bot/{bot_id}/transcript",
            headers=_headers(api_key),
            timeout=60,
        )
        if not resp.ok:
            logger.warning("recall get_transcript: %s %s", resp.status_code, resp.text[:500])
            return ""
        segments = resp.json()
    except requests.RequestException as e:
        logger.warning("recall get_transcript request: %s", e)
        return ""
    except ValueError as e:
        logger.warning("recall get_transcript JSON: %s", e)
        return ""

    return _format_transcript(segments)


def _format_transcript(segments: list) -> str:
    """
    Форматирует список сегментов Recall.ai в читаемый текст с указанием спикеров.

    Формат сегмента:
    {
        "speaker": "Speaker 1",
        "words": [{"text": "Привет", ...}, ...],
        "is_final": true
    }
    """
    if not isinstance(segments, list):
        logger.warning("recall transcript: ожидался list, получен %s", type(segments))
        return ""

    parts = []
    for i, seg in enumerate(segments):
        if not isinstance(seg, dict):
            continue
        if not seg.get("is_final", True):
            continue

        speaker = seg.get("speaker") or f"Спикер {i + 1}"
        words = seg.get("words") or []

        if isinstance(words, list):
            text = " ".join(
                w.get("text", "") if isinstance(w, dict) else str(w)
                for w in words
            ).strip()
        elif isinstance(words, str):
            text = words.strip()
        else:
            text = ""

        if text:
            parts.append(f"{speaker}: {text}")

    result = "\n".join(parts)
    if result:
        logger.info("recall transcript: %d символов, %d сегментов", len(result), len(parts))
    else:
        logger.warning("recall transcript: пустой результат. Сегментов: %d", len(segments))
    return result


def record_meeting(
    link: str,
    api_key: str,
    bot_name: str = "GLAVA",
    region: str = DEFAULT_REGION,
    language_code: str = "ru",
    assemblyai_api_key: str = "",
) -> str | None:
    """
    Совместимая с mymeet_client.record_meeting точка входа.
    Подключает бота Recall.ai к встрече по ссылке.
    Возвращает bot_id (аналог meeting_id) или None.
    """
    return create_bot(
        meeting_url=link,
        api_key=api_key,
        bot_name=bot_name,
        region=region,
        language_code=language_code,
        assemblyai_api_key=assemblyai_api_key,
    )
