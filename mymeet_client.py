"""
Клиент mymeet.ai API для транскрипции с диаризацией.

Поток:
1. Загрузка аудио (chunked upload)
2. Ожидание обработки (polling status)
3. Получение отчёта JSON и извлечение транскрипта

API: https://backend.mymeet.ai/docs/
API key: https://mymeet.ai/contact (B2B)
"""

import logging
import math
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

MYMEET_BASE_URL = "https://backend.mymeet.ai"
CHUNK_SIZE = 20 * 1024 * 1024  # 20 MB

# Шаблоны: research-interview подходит для биографических интервью
TEMPLATE_RESEARCH = "research-interview"
TEMPLATE_ARTICLE = "article"
TEMPLATE_DEFAULT = "default-meeting"


def upload_audio(
    audio_path: str,
    api_key: str,
    template_name: str = TEMPLATE_RESEARCH,
    title: str | None = None,
) -> str | None:
    """
    Загружает аудио в mymeet.ai (chunked upload).
    Возвращает meeting_id или None при ошибке.
    """
    path = Path(audio_path)
    if not path.exists():
        logger.error("Файл не найден: %s", audio_path)
        return None

    file_size = path.stat().st_size
    file_id = str(uuid.uuid4())
    total_chunks = max(1, math.ceil(file_size / CHUNK_SIZE))
    local_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")

    with open(path, "rb") as f:
        for chunk_idx in range(total_chunks):
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break

            chunk_number = chunk_idx + 1  # 1-based

            data = {
                "api_key": api_key,
                "id": file_id,
                "chunk_number": chunk_number,
                "chunk_total": total_chunks,
                "filename": path.name,
                "localTime": local_time,
                "template_name": template_name,
                "title": title or f"GLAVA voice {path.stem}",
            }

            files = {"file": (path.name, chunk, "application/octet-stream")}

            try:
                resp = requests.post(
                    f"{MYMEET_BASE_URL}/api/video",
                    data=data,
                    files=files,
                    timeout=120,
                )
            except requests.RequestException as e:
                logger.warning("mymeet upload error: %s", e)
                return None

            if not resp.ok:
                logger.warning("mymeet upload: %s %s", resp.status_code, resp.text[:500])
                return None

            logger.debug("mymeet chunk %s/%s OK", chunk_number, total_chunks)

            if chunk_number == total_chunks:
                try:
                    j = resp.json()
                    meeting_id = j.get("meeting_id") or j.get("meetingId")
                    if meeting_id:
                        logger.info("mymeet upload OK, meeting_id=%s", meeting_id)
                        return meeting_id
                    logger.warning("mymeet: нет meeting_id в ответе: %s", j)
                except Exception as e:
                    logger.warning("mymeet response parse: %s", e)
                return None

    return None


def get_meeting_status(meeting_id: str, api_key: str) -> str | None:
    """Возвращает статус: processing, processed, failed, queued, new."""
    try:
        resp = requests.get(
            f"{MYMEET_BASE_URL}/api/meeting/status",
            params={"api_key": api_key, "meeting_id": meeting_id},
            timeout=30,
        )
        if resp.ok:
            return resp.text.strip().strip('"').lower()
    except requests.RequestException as e:
        logger.warning("mymeet status: %s", e)
    return None


def wait_for_processed(
    meeting_id: str,
    api_key: str,
    timeout_sec: int = 600,
    poll_interval: int = 10,
) -> bool:
    """Ждёт статус processed. Возвращает True при успехе."""
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        status = get_meeting_status(meeting_id, api_key)
        if status == "processed":
            return True
        if status == "failed":
            logger.warning("mymeet meeting %s failed", meeting_id)
            return False
        logger.info("mymeet status: %s, ждём...", status)
        time.sleep(poll_interval)
    logger.warning("mymeet timeout: %s", meeting_id)
    return False


def _extract_transcript_from_report(report: dict) -> str:
    """
    Извлекает текст транскрипта из JSON-отчёта mymeet.
    Структура может отличаться — пробуем типичные пути.
    """
    # Прямые ключи
    for key in ("transcript", "full_transcript", "text", "meeting_text", "raw_transcript"):
        val = report.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()

    # Вложенные структуры
    segments = report.get("segments") or report.get("transcript_segments") or []
    if isinstance(segments, list):
        parts = []
        for s in segments:
            if isinstance(s, dict):
                text = s.get("text") or s.get("content") or s.get("phrase") or ""
            elif isinstance(s, str):
                text = s
            else:
                text = str(s) if s else ""
            if text:
                parts.append(text.strip())
        if parts:
            return "\n".join(parts)

    # speakers / turns
    speakers = report.get("speakers") or report.get("turns") or []
    if isinstance(speakers, list):
        parts = []
        for sp in speakers:
            if isinstance(sp, dict):
                text = sp.get("text") or sp.get("content") or sp.get("phrase") or ""
            elif isinstance(sp, str):
                text = sp
            else:
                text = str(sp) if sp else ""
            if text:
                parts.append(text.strip())
        if parts:
            return "\n".join(parts)

    # followup / summary (часто содержит весь текст)
    followup = report.get("followup") or report.get("followUp")
    if isinstance(followup, dict):
        return _extract_transcript_from_report(followup)
    if isinstance(followup, str) and followup.strip():
        return followup.strip()

    return ""


def get_meeting_report(meeting_id: str, api_key: str) -> dict | None:
    """Получает JSON-отчёт о встрече."""
    try:
        resp = requests.get(
            f"{MYMEET_BASE_URL}/api/video/report",
            params={"api_key": api_key, "meeting_id": meeting_id},
            timeout=60,
        )
        if resp.ok:
            return resp.json()
    except requests.RequestException as e:
        logger.warning("mymeet report: %s", e)
    except ValueError as e:
        logger.warning("mymeet report JSON: %s", e)
    return None


def transcribe_via_mymeet(
    audio_path: str,
    api_key: str,
    template_name: str = TEMPLATE_RESEARCH,
    timeout_sec: int = 600,
) -> str:
    """
    Полный цикл: загрузка -> ожидание -> транскрипт.
    Возвращает текст транскрипта или пустую строку.
    """
    meeting_id = upload_audio(audio_path, api_key, template_name=template_name)
    if not meeting_id:
        return ""

    if not wait_for_processed(meeting_id, api_key, timeout_sec=timeout_sec):
        return ""

    report = get_meeting_report(meeting_id, api_key)
    if not report:
        return ""

    transcript = _extract_transcript_from_report(report)
    if not transcript:
        logger.warning("mymeet: не удалось извлечь транскрипт из отчёта. Ключи: %s", list(report.keys())[:20])
    return transcript
