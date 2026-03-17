"""
Внутренний API для n8n — без UI-авторизации.
Доступен только с localhost ИЛИ с правильным X-Api-Key заголовком.
Маршруты: /api/prompts/<role>    GET
          /api/jobs/update       POST
          /api/send-book-pdf     POST  — генерация PDF и отправка в Telegram
"""
import logging
import os

import requests as _requests
from flask import Blueprint, abort, jsonify, request

from admin import db_admin as dba

bp = Blueprint("api", __name__, url_prefix="/api")
logger = logging.getLogger(__name__)


def _check_access() -> None:
    """Разрешаем запросы только с localhost или с правильным API-ключом."""
    remote = (request.remote_addr or "").split(",")[0].strip()
    token = request.headers.get("X-Api-Key", "")
    api_key = os.environ.get("ADMIN_API_KEY", "")

    if remote in ("127.0.0.1", "::1", "localhost"):
        return
    if api_key and token == api_key:
        return
    logger.warning("api: доступ запрещён с %s", remote)
    abort(403)


# ── GET /api/prompts/<role> ────────────────────────────────────────

@bp.get("/prompts/<role>")
def get_prompt(role: str):
    """Возвращает текущий промпт агента по роли.
    Если промпта нет — text будет пустой строкой (n8n использует fallback)."""
    _check_access()
    row = dba.get_prompt(role)
    if row is None:
        return jsonify({"role": role, "text": "", "version": 0, "found": False}), 200
    return jsonify({
        "role": role,
        "text": row.get("prompt_text", ""),
        "version": row.get("version", 0),
        "found": True,
    }), 200


# ── POST /api/jobs/update ─────────────────────────────────────────

@bp.post("/jobs/update")
def update_job():
    """n8n вызывает этот endpoint после каждого шага пайплайна.
    Body: {telegram_id, phase, step, status, error?}"""
    _check_access()
    data = request.get_json(silent=True) or {}
    telegram_id = data.get("telegram_id")
    phase = data.get("phase", "A")
    step = data.get("step", "")
    status = data.get("status", "running")   # running | done | error
    error = data.get("error")

    if not telegram_id:
        return jsonify({"error": "telegram_id required"}), 400

    try:
        dba.upsert_pipeline_job(int(telegram_id), phase, step, status, error)
    except Exception as e:
        logger.exception("update_job error: %s", e)
        return jsonify({"error": str(e)}), 500

    return jsonify({"ok": True}), 200


# ── POST /api/send-book-pdf ───────────────────────────────────────
# n8n вызывает этот endpoint вместо прямой отправки bio_text как текста.
# Генерирует PDF-книгу из bio_text и отправляет файл в Telegram.
# Body: {telegram_id, bio_text, character_name, draft_id?}

@bp.post("/send-book-pdf")
def send_book_pdf():
    _check_access()
    data = request.get_json(silent=True) or {}

    telegram_id = data.get("telegram_id")
    bio_text = data.get("bio_text", "")
    character_name = data.get("character_name", "Герой книги")
    draft_id = data.get("draft_id", 0)

    if not telegram_id:
        return jsonify({"error": "telegram_id required"}), 400
    if not bio_text:
        return jsonify({"error": "bio_text required"}), 400

    bot_token = os.environ.get("BOT_TOKEN", "")
    if not bot_token:
        return jsonify({"error": "BOT_TOKEN not configured"}), 500

    try:
        from pdf_book import generate_book_pdf
        pdf_bytes = generate_book_pdf(bio_text, character_name=character_name)
    except Exception as e:
        logger.exception("send_book_pdf: ошибка генерации PDF: %s", e)
        return jsonify({"error": f"pdf generation failed: {e}"}), 500

    # Имя файла
    safe_name = "".join(c for c in character_name if c.isalnum() or c in " _-")[:40].strip()
    filename = f"Glava_{safe_name or 'kniga'}.pdf"

    # Отправляем через Telegram Bot API sendDocument
    tg_url = f"https://api.telegram.org/bot{bot_token}/sendDocument"
    try:
        resp = _requests.post(
            tg_url,
            data={"chat_id": str(telegram_id)},
            files={"document": (filename, pdf_bytes, "application/pdf")},
            timeout=60,
        )
        resp.raise_for_status()
        tg_result = resp.json()
        if not tg_result.get("ok"):
            logger.error("send_book_pdf: Telegram вернул ошибку: %s", tg_result)
            return jsonify({"error": "telegram send failed", "detail": tg_result}), 502
    except Exception as e:
        logger.exception("send_book_pdf: ошибка отправки в Telegram: %s", e)
        return jsonify({"error": f"telegram send failed: {e}"}), 502

    logger.info(
        "send_book_pdf: PDF '%s' (%d байт) отправлен telegram_id=%s",
        filename, len(pdf_bytes), telegram_id,
    )
    return jsonify({"ok": True, "filename": filename, "size": len(pdf_bytes)}), 200


# ── GET /api/health ───────────────────────────────────────────────

@bp.get("/health")
def health():
    return jsonify({"status": "ok"}), 200
