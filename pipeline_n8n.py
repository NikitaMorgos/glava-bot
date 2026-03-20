"""
Триггер n8n пайплайна Phase A.

После успешной транскрипции Python отправляет данные в n8n webhook.
n8n запускает полную цепочку агентов и отправляет результат напрямую в Telegram.

Если N8N_WEBHOOK_PHASE_A не задан — модуль ничего не делает (graceful fallback).
"""
import logging
import os
import threading

import requests as _requests

logger = logging.getLogger(__name__)


def trigger_phase_a(
    telegram_id: int,
    transcript: str,
    character_name: str = "",
    draft_id: int = 0,
    username: str = "",
) -> bool:
    """
    Отправляет транскрипт в n8n webhook для обработки цепочкой агентов Phase A.
    Возвращает True если запрос принят (2xx), False при любой ошибке.
    Вызов синхронный — используй trigger_phase_a_background для неблокирующего запуска.
    """
    webhook_url = os.environ.get("N8N_WEBHOOK_PHASE_A", "").strip()
    if not webhook_url:
        logger.info("N8N_WEBHOOK_PHASE_A не задан — n8n пайплайн пропущен")
        return False

    bot_token = os.environ.get("BOT_TOKEN", "")
    admin_api_url = os.environ.get(
        "ADMIN_API_BASE_URL", "http://127.0.0.1:5001/api"
    )

    # Добавляем количество фото — нужно Photo Editor для генерации подписей
    try:
        import db as _db
        photo_count = len(_db.get_user_photos(telegram_id, limit=100))
    except Exception:
        photo_count = 0

    payload = {
        "telegram_id": telegram_id,
        "transcript": transcript,
        "character_name": character_name,
        "draft_id": draft_id,
        "username": username,
        "photo_count": photo_count,
        "bot_token": bot_token,
        "admin_api_url": admin_api_url,
    }

    try:
        r = _requests.post(webhook_url, json=payload, timeout=30)
        if r.status_code < 400:
            logger.info(
                "n8n Phase A запущен: HTTP %s, telegram_id=%s",
                r.status_code,
                telegram_id,
            )
            return True
        else:
            logger.error(
                "n8n webhook вернул ошибку: HTTP %s, body=%s",
                r.status_code,
                r.text[:200],
            )
            return False
    except Exception as e:
        logger.error("n8n trigger_phase_a ошибка: %s", e)
        return False


def trigger_phase_b(
    telegram_id: int,
    input_type: str,
    content: str,
    character_name: str = "",
    draft_id: int = 0,
    username: str = "",
) -> bool:
    """
    Отправляет клиентскую правку в n8n webhook Phase B.
    input_type: text | voice_transcript | photo_caption
    Возвращает True если запрос принят.
    """
    webhook_url = os.environ.get("N8N_WEBHOOK_PHASE_B", "").strip()
    if not webhook_url:
        logger.info("N8N_WEBHOOK_PHASE_B не задан — Phase B пропущен")
        return False

    bot_token = os.environ.get("BOT_TOKEN", "")
    admin_api_url = os.environ.get("ADMIN_API_BASE_URL", "http://127.0.0.1:5001/api")

    payload = {
        "telegram_id": telegram_id,
        "input_type": input_type,
        "content": content,
        "character_name": character_name,
        "draft_id": draft_id,
        "username": username,
        "bot_token": bot_token,
        "admin_api_url": admin_api_url,
    }

    try:
        r = _requests.post(webhook_url, json=payload, timeout=30)
        if r.status_code < 400:
            logger.info("n8n Phase B запущен: HTTP %s, telegram_id=%s", r.status_code, telegram_id)
            return True
        logger.error("n8n Phase B webhook ошибка: HTTP %s, body=%s", r.status_code, r.text[:200])
        return False
    except Exception as e:
        logger.error("n8n trigger_phase_b ошибка: %s", e)
        return False


def trigger_phase_b_background(
    telegram_id: int,
    input_type: str,
    content: str,
    character_name: str = "",
    draft_id: int = 0,
    username: str = "",
) -> None:
    """Запускает trigger_phase_b в фоновом потоке."""
    def _run():
        trigger_phase_b(
            telegram_id=telegram_id,
            input_type=input_type,
            content=content,
            character_name=character_name,
            draft_id=draft_id,
            username=username,
        )
    t = threading.Thread(target=_run, daemon=True)
    t.start()
    logger.info("n8n Phase B триггер отправлен в фон для telegram_id=%s", telegram_id)


def trigger_phase_a_background(
    telegram_id: int,
    transcript: str,
    character_name: str = "",
    draft_id: int = 0,
    username: str = "",
) -> None:
    """Запускает trigger_phase_a в фоновом потоке (не блокирует бота).

    Если transcript пустой, ждёт до 10 минут пока фоновая транскрипция
    не сохранит результаты в БД, затем собирает итоговый транскрипт.
    """
    import time

    def _run():
        import db as _db
        current_transcript = transcript.strip() if transcript else ""

        if not current_transcript:
            # Ждём завершения фоновой транскрипции (polling, макс 10 мин)
            logger.info(
                "n8n Phase A: транскрипт пустой, ждём БД (telegram_id=%s)...", telegram_id
            )
            for attempt in range(60):  # 60 × 10с = 10 мин
                time.sleep(10)
                current_transcript = _db.get_user_transcripts(telegram_id)
                if current_transcript and current_transcript.strip():
                    logger.info(
                        "n8n Phase A: транскрипт получен (попытка %d, %d chars)",
                        attempt + 1, len(current_transcript),
                    )
                    break
            else:
                logger.warning(
                    "n8n Phase A: транскрипт по-прежнему пустой после 10 мин "
                    "(telegram_id=%s) — запускаем без транскрипта",
                    telegram_id,
                )

        trigger_phase_a(
            telegram_id=telegram_id,
            transcript=current_transcript,
            character_name=character_name,
            draft_id=draft_id,
            username=username,
        )

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    logger.info("n8n Phase A триггер отправлен в фон для telegram_id=%s", telegram_id)
