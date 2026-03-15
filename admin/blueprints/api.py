"""
Внутренний API для n8n — без UI-авторизации.
Доступен только с localhost ИЛИ с правильным X-Api-Key заголовком.
Маршруты: /api/prompts/<role>  GET
          /api/jobs/update     POST
"""
import logging
import os

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


# ── GET /api/health ───────────────────────────────────────────────

@bp.get("/health")
def health():
    return jsonify({"status": "ok"}), 200
