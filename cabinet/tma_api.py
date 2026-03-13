"""
Telegram Mini App API — Blueprint для Flask.

Верификация: Telegram передаёт initData с HMAC-SHA256 подписью.
Алгоритм проверки: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app

Эндпоинты:
  POST /api/tma/auth          — верификация initData → JWT-токен
  GET  /api/tma/dashboard     — голосовые, фото, bio (требует токен)
  GET  /api/tma/questions     — вопросы для интервью (требует токен)
"""

import hashlib
import hmac
import json
import os
import time
from functools import wraps
from urllib.parse import parse_qsl, unquote

from flask import Blueprint, jsonify, request

import db
import storage

tma_api = Blueprint("tma_api", __name__, url_prefix="/api/tma")

# ─────────────────────────────────────────────
# Верификация Telegram initData
# ─────────────────────────────────────────────

def _verify_init_data(init_data_raw: str, bot_token: str) -> dict | None:
    """
    Проверяет подпись initData от Telegram.
    Возвращает словарь данных пользователя или None если подпись неверна.
    Документация: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    """
    try:
        params = dict(parse_qsl(init_data_raw, keep_blank_values=True))
        received_hash = params.pop("hash", None)
        if not received_hash:
            return None

        # Формируем data_check_string: отсортированные пары key=value через \n
        data_check_string = "\n".join(
            f"{k}={v}" for k, v in sorted(params.items())
        )

        # secret_key = HMAC-SHA256("WebAppData", bot_token)
        secret_key = hmac.new(
            b"WebAppData", bot_token.encode(), hashlib.sha256
        ).digest()

        # Ожидаемая подпись
        expected_hash = hmac.new(
            secret_key, data_check_string.encode(), hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(expected_hash, received_hash):
            return None

        # Проверка свежести (не старше 24 часов)
        auth_date = int(params.get("auth_date", 0))
        if time.time() - auth_date > 86400:
            return None

        user_json = params.get("user", "{}")
        return json.loads(user_json)
    except Exception:
        return None


# ─────────────────────────────────────────────
# Простой stateless токен (подписанный HMAC)
# ─────────────────────────────────────────────

def _make_token(telegram_id: int) -> str:
    """Создаёт подписанный токен: telegram_id:timestamp:hmac."""
    secret = os.environ.get("CABINET_SECRET_KEY", "glava-cabinet-dev")
    ts = int(time.time())
    msg = f"{telegram_id}:{ts}"
    sig = hmac.new(secret.encode(), msg.encode(), hashlib.sha256).hexdigest()
    return f"{msg}:{sig}"


def _verify_token(token: str) -> int | None:
    """Проверяет токен, возвращает telegram_id или None."""
    try:
        secret = os.environ.get("CABINET_SECRET_KEY", "glava-cabinet-dev")
        parts = token.split(":")
        if len(parts) != 3:
            return None
        telegram_id_str, ts_str, sig = parts
        ts = int(ts_str)
        if time.time() - ts > 86400 * 7:  # токен живёт 7 дней
            return None
        msg = f"{telegram_id_str}:{ts_str}"
        expected = hmac.new(secret.encode(), msg.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, sig):
            return None
        return int(telegram_id_str)
    except Exception:
        return None


def _require_tma_auth(f):
    """Декоратор: проверяет токен из заголовка Authorization: Bearer <token>."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"error": "unauthorized"}), 401
        token = auth.removeprefix("Bearer ").strip()
        telegram_id = _verify_token(token)
        if not telegram_id:
            return jsonify({"error": "invalid or expired token"}), 401
        request.tma_telegram_id = telegram_id
        return f(*args, **kwargs)
    return decorated


# ─────────────────────────────────────────────
# Эндпоинты
# ─────────────────────────────────────────────

@tma_api.route("/auth", methods=["POST"])
def auth():
    """
    Верифицирует initData от Telegram и возвращает токен.
    Body: { "init_data": "<строка initData из Telegram.WebApp.initData>" }
    """
    body = request.get_json(silent=True) or {}
    init_data_raw = body.get("init_data", "")

    bot_token = os.environ.get("BOT_TOKEN", "")
    if not bot_token:
        return jsonify({"error": "server misconfigured"}), 500

    tg_user = _verify_init_data(init_data_raw, bot_token)
    if not tg_user:
        return jsonify({"error": "invalid init_data"}), 403

    telegram_id = tg_user.get("id")
    if not telegram_id:
        return jsonify({"error": "no user id"}), 403

    # Убеждаемся что пользователь существует в БД
    username = tg_user.get("username", "")
    db.get_or_create_user(telegram_id, username)

    token = _make_token(telegram_id)
    return jsonify({
        "token": token,
        "user": {
            "id": telegram_id,
            "first_name": tg_user.get("first_name", ""),
            "username": username,
        },
    })


@tma_api.route("/dashboard")
@_require_tma_auth
def dashboard():
    """Возвращает данные дашборда: голосовые, фото, наличие биографии."""
    telegram_id = request.tma_telegram_id
    try:
        user, voices, photos = db.get_user_all_data(telegram_id)
    except Exception:
        return jsonify({"error": "db error"}), 500

    # Presigned URL для каждого файла
    for v in voices:
        try:
            v["download_url"] = storage.get_presigned_download_url(v["storage_key"])
        except Exception:
            v["download_url"] = None
        # Убираем непримитивные типы
        if hasattr(v.get("created_at"), "isoformat"):
            v["created_at"] = v["created_at"].isoformat()

    for p in photos:
        try:
            p["download_url"] = storage.get_presigned_download_url(p["storage_key"])
        except Exception:
            p["download_url"] = None
        if hasattr(p.get("created_at"), "isoformat"):
            p["created_at"] = p["created_at"].isoformat()

    # Биография из файловой системы (если есть)
    bio_text = _read_client_file(telegram_id, user.get("username", ""), "bio_story.txt")
    transcript_exists = _read_client_file(
        telegram_id, user.get("username", ""), "transcript.txt"
    ) is not None

    return jsonify({
        "user": {
            "username": user.get("username", ""),
            "telegram_id": telegram_id,
        },
        "voices": voices,
        "photos": photos,
        "bio": bio_text,
        "has_transcript": transcript_exists,
        "voices_count": len(voices),
        "photos_count": len(photos),
    })


@tma_api.route("/questions")
@_require_tma_auth
def questions():
    """Возвращает список вопросов для интервью."""
    from cabinet.app import INTERVIEW_QUESTIONS  # импорт из основного модуля
    blocks = [
        {"title": title, "questions": qs}
        for title, qs in INTERVIEW_QUESTIONS
    ]
    return jsonify({"blocks": blocks})


# ─────────────────────────────────────────────
# Вспомогательные
# ─────────────────────────────────────────────

def _read_client_file(
    telegram_id: int, username: str, filename: str
) -> str | None:
    """Читает файл из exports/client_{telegram_id}_{username}/."""
    from pathlib import Path
    username = (username or "unknown").replace("/", "_")
    exports = Path(__file__).resolve().parent.parent / "exports"
    path = exports / f"client_{telegram_id}_{username}" / filename
    if path.exists():
        try:
            return path.read_text(encoding="utf-8")
        except Exception:
            return None
    return None
