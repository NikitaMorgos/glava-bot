"""
Загрузка сообщений бота из Admin API с fallback на prepay.messages.

Бот вызывает get_message(key, **vars) — возвращает текст (с подстановкой плейсхолдеров).
Кеш 60 сек. При недоступности API — fallback на константы из prepay.messages.
"""
import logging
import os
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)

# Маппинг key → атрибут в prepay.messages (для fallback)
_FALLBACK_MAP = {
    # Pre-pay
    "intro_main": "INTRO_MAIN_MSG",
    "intro_example": "INTRO_EXAMPLE_MSG",
    "intro_price": "INTRO_PRICE_MSG",
    "config_characters": "CONFIG_CHARACTERS_MSG",
    "config_characters_list": "CONFIG_CHARACTERS_LIST_MSG",
    "email_input": "EMAIL_INPUT_MSG",
    "email_error": "EMAIL_ERROR_MSG",
    "order_summary": "ORDER_SUMMARY_MSG",
    "payment_init": "PAYMENT_INIT_MSG",
    "payment_wait": "PAYMENT_WAIT_MSG",
    "payment_still_pending": "PAYMENT_STILL_PENDING_MSG",
    "resume_draft": "RESUME_DRAFT_MSG",
    "resume_payment": "RESUME_PAYMENT_MSG",
    "blocked_media": "BLOCKED_MEDIA_MSG",
    "online_meeting_intro": "ONLINE_MEETING_INTRO_MSG",
    "online_meeting_link_sent": "ONLINE_MEETING_LINK_SENT_MSG",
    "online_meeting_telemost_sent": "ONLINE_MEETING_TELEMOST_SENT_MSG",
    "online_meeting_bad_link": "ONLINE_MEETING_BAD_LINK_MSG",
    "online_meeting_error": "ONLINE_MEETING_ERROR_MSG",
    # Scenario v2 — pre-pay
    "character_name": "CHARACTER_NAME_MSG",
    "character_relation": "CHARACTER_RELATION_MSG",
    # Scenario v2 — post-pay
    "narrators_setup": "NARRATORS_SETUP_MSG",
    "narrator_relation": "NARRATOR_RELATION_MSG",
    "narrators_list": "NARRATORS_LIST_MSG",
    "interview_guide": "INTERVIEW_GUIDE_MSG",
    "interview_questions": "INTERVIEW_QUESTIONS_MSG",
    "upload_who": "UPLOAD_WHO_MSG",
    "upload_audio": "UPLOAD_AUDIO_MSG",
    "upload_file_accepted": "UPLOAD_FILE_ACCEPTED_MSG",
    "upload_photo": "UPLOAD_PHOTO_MSG",
    "upload_photo_accepted": "UPLOAD_PHOTO_ACCEPTED_MSG",
    "upload_summary": "UPLOAD_SUMMARY_MSG",
    "upload_processing": "UPLOAD_PROCESSING_MSG",
    "interview_questions_ready": "INTERVIEW_QUESTIONS_READY_MSG",
    "interview2": "INTERVIEW_2_MSG",
    "interview2_confirm": "INTERVIEW_2_CONFIRM_MSG",
    "assembling": "ASSEMBLING_MSG",
    "book_ready": "BOOK_READY_MSG",
    "revision_prompt": "REVISION_PROMPT_MSG",
    "revision_processing": "REVISION_PROCESSING_MSG",
    "revision_ready": "REVISION_READY_MSG",
    "revision_debounce": "REVISION_DEBOUNCE_MSG",
    "revision_limit": "REVISION_LIMIT_MSG",
    "versions_empty": "VERSIONS_EMPTY_MSG",
    "versions_list": "VERSIONS_LIST_MSG",
    "versions_rollback_confirm": "VERSIONS_ROLLBACK_CONFIRM_MSG",
    "finalize_confirm": "FINALIZE_CONFIRM_MSG",
    "finalized": "FINALIZED_MSG",
    "print_soon": "PRINT_SOON_MSG",
    "refund_reason": "REFUND_REASON_MSG",
    "refund_submitted": "REFUND_SUBMITTED_MSG",
    "assembly_error": "ASSEMBLY_ERROR_MSG",
    "unsupported_file": "UNSUPPORTED_FILE_MSG",
    "file_too_large": "FILE_TOO_LARGE_MSG",
}

_CACHE: dict[str, tuple[str, float]] = {}
_CACHE_TTL = 60  # секунд
_API_BASE = os.environ.get("ADMIN_API_BASE_URL", "http://127.0.0.1:5001/api")


def get_message(key: str, **vars: Any) -> str:
    """
    Возвращает текст сообщения по ключу.
    Подставляет {placeholders} из vars.
    Fallback на prepay.messages при недоступности API.
    """
    now = time.time()
    cache_key = key
    if cache_key in _CACHE:
        text, ts = _CACHE[cache_key]
        if now - ts < _CACHE_TTL:
            try:
                return text.format(**vars) if vars else text
            except KeyError:
                pass

    url = f"{_API_BASE.rstrip('/')}/prompts/bot_{key}"
    try:
        r = requests.get(url, timeout=3)
        if r.status_code == 200:
            data = r.json()
            text = (data.get("text") or "").strip()
            if text:
                _CACHE[cache_key] = (text, now)
                return text.format(**vars) if vars else text
    except Exception as e:
        logger.debug("bot_messages API недоступен: %s", e)

    # Fallback
    from prepay import messages as m
    attr = _FALLBACK_MAP.get(key)
    if attr:
        text = getattr(m, attr, "")
        if text:
            return text.format(**vars) if vars else text
    return ""
