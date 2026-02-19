"""
Клиент Plaud API для транскрипции с диаризацией.

Поток:
1. Загрузка аудио (multipart upload)
2. Отправка workflow AUDIO_TRANSCRIBE (diarization=true)
3. Ожидание результата (polling)
4. Извлечение транскрипта
"""

import hashlib
import logging
import time
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

PLAUD_BASE_URL = "https://platform.plaud.ai/api"


def _get_headers(api_token: str) -> dict:
    return {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }


def upload_audio(
    audio_path: str,
    api_token: str,
    owner_id: str = "glava_default",
    name: str | None = None,
) -> str | None:
    """
    Загружает аудио в Plaud (multipart upload).
    Возвращает file_id или None при ошибке.
    """
    path = Path(audio_path)
    if not path.exists():
        logger.error("Файл не найден: %s", audio_path)
        return None

    file_size = path.stat().st_size
    ext = path.suffix.lower()
    file_type = "opus" if ext in (".ogg", ".opus", ".oga") else ("mp3" if ext == ".mp3" else "opus")

    # 1. Генерация presigned URLs
    resp = requests.post(
        f"{PLAUD_BASE_URL}/files/upload-s3/generate-presigned-urls",
        headers=_get_headers(api_token),
        json={"filesize": file_size, "filetype": file_type},
        timeout=30,
    )
    if not resp.ok:
        logger.warning("Plaud generate-presigned-urls: %s %s", resp.status_code, resp.text[:300])
        return None

    try:
        info = resp.json()
    except Exception as e:
        logger.warning("Plaud response JSON: %s", e)
        return None

    file_id = info.get("FileId") or info.get("file_id")
    upload_id = info.get("UploadId") or info.get("upload_id")
    parts = info.get("Parts") or info.get("parts") or []
    chunk_size = info.get("ChunkSize") or info.get("chunk_size") or 5 * 1024 * 1024

    if not file_id or not upload_id or not parts:
        logger.warning("Plaud: нет FileId/UploadId/Parts в ответе: %s", info)
        return None

    # 2. Загрузка чанков
    part_list = []
    with open(path, "rb") as f:
        for part in parts:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            presigned_url = part.get("PresignedUrl") or part.get("presigned_url")
            part_number = part.get("PartNumber") or part.get("part_number")
            if not presigned_url:
                continue
            up_resp = requests.put(
                presigned_url,
                data=chunk,
                headers={"Content-Type": "application/octet-stream"},
                timeout=60,
            )
            if not up_resp.ok:
                logger.warning("Plaud chunk upload: %s", up_resp.status_code)
                return None
            etag = up_resp.headers.get("ETag", "").strip('"')
            part_list.append({"PartNumber": part_number, "ETag": etag})

    # 3. Complete upload
    with open(path, "rb") as f:
        file_md5 = hashlib.md5(f.read()).hexdigest()

    complete_resp = requests.post(
        f"{PLAUD_BASE_URL}/files/upload-s3/complete-upload",
        headers=_get_headers(api_token),
        json={
            "owner_id": owner_id,
            "file_id": file_id,
            "upload_id": upload_id,
            "part_list": part_list,
            "filetype": file_type,
            "file_md5": file_md5,
            "name": name or path.name,
        },
        timeout=30,
    )
    if not complete_resp.ok:
        logger.warning("Plaud complete-upload: %s %s", complete_resp.status_code, complete_resp.text[:300])
        return None

    result = complete_resp.json()
    final_id = result.get("id") or result.get("Id") or file_id
    logger.info("Plaud upload OK, file_id=%s", final_id)
    return final_id


def submit_transcribe_workflow(
    file_id: str,
    api_token: str,
    language: str = "ru",
    diarization: bool = True,
    metadata: dict | None = None,
) -> str | None:
    """
    Отправляет workflow транскрипции.
    Возвращает workflow_id или None.
    """
    payload = {
        "workflows": [
            {
                "task_type": "AUDIO_TRANSCRIBE",
                "task_params": {
                    "file_id": file_id,
                    "language": language,
                    "diarization": diarization,
                },
            }
        ],
        "metadata": metadata or {},
        "version": "1.0",
    }
    # Некоторые версии API требуют file_id в metadata
    if metadata is None:
        payload["metadata"] = {"file_id": file_id}

    resp = requests.post(
        f"{PLAUD_BASE_URL}/workflows/submit",
        headers=_get_headers(api_token),
        json=payload,
        timeout=30,
    )
    if not resp.ok:
        logger.warning("Plaud submit workflow: %s %s", resp.status_code, resp.text[:300])
        return None

    try:
        data = resp.json()
    except Exception as e:
        logger.warning("Plaud workflow response: %s", e)
        return None

    wf_id = data.get("id") or data.get("Id")
    logger.info("Plaud workflow submitted: %s", wf_id)
    return wf_id


def get_workflow_status(workflow_id: str, api_token: str) -> dict | None:
    """Возвращает статус workflow."""
    resp = requests.get(
        f"{PLAUD_BASE_URL}/workflows/{workflow_id}/status",
        headers=_get_headers(api_token),
        timeout=30,
    )
    if not resp.ok:
        return None
    try:
        return resp.json()
    except Exception:
        return None


def get_workflow_result(workflow_id: str, api_token: str) -> dict | None:
    """Возвращает полный результат workflow."""
    resp = requests.get(
        f"{PLAUD_BASE_URL}/workflows/{workflow_id}/result",
        headers=_get_headers(api_token),
        timeout=30,
    )
    if not resp.ok:
        return None
    try:
        return resp.json()
    except Exception:
        return None


def wait_for_workflow(
    workflow_id: str,
    api_token: str,
    poll_interval: int = 5,
    max_wait_sec: int = 600,
) -> bool:
    """Ожидает завершения workflow. Возвращает True при SUCCESS, False при FAILURE/таймауте."""
    start = time.time()
    while time.time() - start < max_wait_sec:
        status_data = get_workflow_status(workflow_id, api_token)
        if not status_data:
            time.sleep(poll_interval)
            continue
        status = status_data.get("status", "")
        completed = status_data.get("completed_tasks", 0)
        total = status_data.get("total_tasks", 1)
        logger.info("Plaud workflow %s: %s (%s/%s)", workflow_id, status, completed, total)
        if status == "SUCCESS":
            return True
        if status == "FAILURE":
            logger.warning("Plaud workflow failed: %s", status_data)
            return False
        time.sleep(poll_interval)
    logger.warning("Plaud workflow timeout: %s", workflow_id)
    return False


def extract_transcript_from_result(result: dict) -> str:
    """
    Извлекает текст транскрипции из результата workflow.
    Поддерживает диаризованный формат: SPEAKER_00: текст
    """
    tasks = result.get("tasks") or []
    for task in tasks:
        if task.get("task_type") in ("audio_transcribe", "AUDIO_TRANSCRIBE"):
            res = task.get("result") or {}
            if isinstance(res, str):
                return res
            # Структура может быть: transcript, text, segments, dialogue
            text = res.get("transcript") or res.get("text") or ""
            if text:
                return text
            segments = res.get("segments") or res.get("dialogue") or []
            if segments:
                lines = []
                for seg in segments:
                    if isinstance(seg, dict):
                        spk = seg.get("speaker") or seg.get("Speaker") or "Спикер"
                        txt = seg.get("text") or seg.get("Text") or ""
                        if txt:
                            lines.append(f"{spk}: {txt}")
                    elif isinstance(seg, str):
                        lines.append(seg)
                return "\n".join(lines) if lines else ""
    return ""


def transcribe_via_plaud(
    audio_path: str,
    api_token: str,
    owner_id: str = "glava_default",
    language: str = "ru",
    diarization: bool = True,
) -> str:
    """
    Полный цикл: загрузка -> транскрипция -> ожидание -> извлечение текста.
    Возвращает транскрипт или пустую строку при ошибке.
    """
    file_id = upload_audio(audio_path, api_token, owner_id=owner_id)
    if not file_id:
        return ""

    workflow_id = submit_transcribe_workflow(
        file_id, api_token, language=language, diarization=diarization
    )
    if not workflow_id:
        return ""

    if not wait_for_workflow(workflow_id, api_token):
        return ""

    result = get_workflow_result(workflow_id, api_token)
    if not result:
        return ""

    return extract_transcript_from_result(result)
