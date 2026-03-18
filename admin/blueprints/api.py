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
    cover_spec = data.get("cover_spec") or {}

    if not telegram_id:
        return jsonify({"error": "telegram_id required"}), 400
    if not bio_text:
        return jsonify({"error": "bio_text required"}), 400

    bot_token = os.environ.get("BOT_TOKEN", "")
    if not bot_token:
        return jsonify({"error": "BOT_TOKEN not configured"}), 500

    try:
        from pdf_book import generate_book_pdf
        pdf_bytes = generate_book_pdf(
            bio_text,
            character_name=character_name,
            cover_spec=cover_spec if cover_spec else None,
        )
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


# ── POST /api/orchestrate/fact-check ─────────────────────────────
# Цикл: Fact Checker → Ghostwriter (до 3 итераций).
# Body: {book_draft, fact_map, transcripts, project_id?, max_iterations?}

@bp.post("/orchestrate/fact-check")
def orchestrate_fact_check():
    _check_access()
    data = request.get_json(silent=True) or {}

    book_draft = data.get("book_draft")
    fact_map = data.get("fact_map")
    transcripts = data.get("transcripts", [])
    project_id = str(data.get("project_id", "proj"))
    max_iterations = int(data.get("max_iterations", 3))

    if not book_draft or not fact_map:
        return jsonify({"error": "book_draft and fact_map are required"}), 400

    openai_key = os.environ.get("OPENAI_API_KEY", "")
    if not openai_key:
        return jsonify({"error": "OPENAI_API_KEY not configured"}), 500

    admin_url = "http://127.0.0.1:5001"

    try:
        from orchestrator import run_fact_check_loop
        result = run_fact_check_loop(
            book_draft=book_draft,
            fact_map=fact_map,
            transcripts=transcripts,
            openai_key=openai_key,
            admin_url=admin_url,
            project_id=project_id,
            max_iterations=max_iterations,
        )
        return jsonify({"ok": True, **result}), 200
    except Exception as e:
        logger.exception("orchestrate_fact_check error: %s", e)
        return jsonify({"error": str(e)}), 500


# ── POST /api/orchestrate/literary-edit ──────────────────────────
# Цикл: Literary Editor → Ghostwriter (до 2 итераций).
# Body: {book_draft, fact_checker_warnings, project_id?, max_iterations?}

@bp.post("/orchestrate/literary-edit")
def orchestrate_literary_edit():
    _check_access()
    data = request.get_json(silent=True) or {}

    book_draft = data.get("book_draft")
    warnings = data.get("fact_checker_warnings", [])
    project_id = str(data.get("project_id", "proj"))
    max_iterations = int(data.get("max_iterations", 2))

    if not book_draft:
        return jsonify({"error": "book_draft is required"}), 400

    openai_key = os.environ.get("OPENAI_API_KEY", "")
    if not openai_key:
        return jsonify({"error": "OPENAI_API_KEY not configured"}), 500

    admin_url = "http://127.0.0.1:5001"

    try:
        from orchestrator import run_literary_edit_loop
        result = run_literary_edit_loop(
            book_draft=book_draft,
            fact_checker_warnings=warnings,
            openai_key=openai_key,
            admin_url=admin_url,
            project_id=project_id,
            max_iterations=max_iterations,
        )
        return jsonify({"ok": True, **result}), 200
    except Exception as e:
        logger.exception("orchestrate_literary_edit error: %s", e)
        return jsonify({"error": str(e)}), 500


# ── POST /api/orchestrate/layout-qa ──────────────────────────────
# Цикл: Layout QA → Layout Designer (до 3 итераций).
# Body: {layout_spec, bio_text, photo_layout, project_id?, max_iterations?}

@bp.post("/orchestrate/layout-qa")
def orchestrate_layout_qa():
    _check_access()
    data = request.get_json(silent=True) or {}

    layout_spec = data.get("layout_spec")
    bio_text = data.get("bio_text", "")
    photo_layout = data.get("photo_layout", [])
    project_id = str(data.get("project_id", "proj"))
    max_iterations = int(data.get("max_iterations", 3))

    if not layout_spec:
        return jsonify({"error": "layout_spec is required"}), 400

    openai_key = os.environ.get("OPENAI_API_KEY", "")
    if not openai_key:
        return jsonify({"error": "OPENAI_API_KEY not configured"}), 500

    admin_url = "http://127.0.0.1:5001"

    try:
        from orchestrator import run_layout_qa_loop
        result = run_layout_qa_loop(
            layout_spec=layout_spec,
            bio_text=bio_text,
            photo_layout=photo_layout,
            openai_key=openai_key,
            admin_url=admin_url,
            project_id=project_id,
            max_iterations=max_iterations,
        )
        return jsonify({"ok": True, **result}), 200
    except Exception as e:
        logger.exception("orchestrate_layout_qa error: %s", e)
        return jsonify({"error": str(e)}), 500


# ── GET /api/health ───────────────────────────────────────────────

@bp.get("/health")
def health():
    return jsonify({"status": "ok"}), 200
