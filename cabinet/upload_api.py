# -*- coding: utf-8 -*-
"""
Upload API — загрузка больших файлов через браузер.

Обходит ограничение Telegram Bot API в 20 МБ.
Бот генерирует одноразовый токен → клиент открывает ссылку → загружает файл.

Эндпоинты:
  GET  /upload/<token>   — страница загрузки
  POST /upload/<token>   — приём файла (multipart)
"""

import logging
import os
import tempfile
import threading
import time
import uuid
from pathlib import Path

from flask import Blueprint, jsonify, render_template_string, request

logger = logging.getLogger(__name__)

upload_api = Blueprint("upload_api", __name__)

AUDIO_EXTENSIONS = {".ogg", ".mp3", ".m4a", ".wav", ".opus", ".oga"}
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500 МБ
TOKEN_TTL = 3600  # 1 час


def _ensure_table():
    """Создаёт таблицу upload_tokens если не существует."""
    import db
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS upload_tokens (
                    token VARCHAR(64) PRIMARY KEY,
                    telegram_id BIGINT NOT NULL,
                    user_id INTEGER NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)


_table_ensured = False


def _maybe_ensure_table():
    global _table_ensured
    if not _table_ensured:
        _ensure_table()
        _table_ensured = True


def create_upload_token(telegram_id: int, user_id: int) -> str:
    """Создаёт одноразовый токен для загрузки. Вызывается из бота."""
    import db
    _maybe_ensure_table()
    _cleanup_expired()
    token = uuid.uuid4().hex
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO upload_tokens (token, telegram_id, user_id) VALUES (%s, %s, %s)",
                (token, telegram_id, user_id),
            )
    return token


def _cleanup_expired():
    import db
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM upload_tokens WHERE created_at < NOW() - INTERVAL '%s seconds'",
                (TOKEN_TTL,),
            )


def _validate_token(token: str) -> dict | None:
    import db
    _maybe_ensure_table()
    _cleanup_expired()
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT telegram_id, user_id FROM upload_tokens WHERE token = %s",
                (token,),
            )
            row = cur.fetchone()
            if row:
                return {"telegram_id": row[0], "user_id": row[1]}
    return None


UPLOAD_HTML = """\
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Загрузка файла — Глава</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: 'Inter', system-ui, sans-serif;
    background: #f8f7f4;
    color: #1a1a1a;
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
}
.card {
    background: #fff;
    border-radius: 16px;
    box-shadow: 0 2px 24px rgba(0,0,0,0.06);
    padding: 40px;
    max-width: 480px;
    width: 100%;
}
.logo { font-size: 24px; font-weight: 600; margin-bottom: 8px; }
.subtitle { color: #666; font-size: 14px; margin-bottom: 32px; }
.drop-zone {
    border: 2px dashed #d0cec8;
    border-radius: 12px;
    padding: 48px 24px;
    text-align: center;
    cursor: pointer;
    transition: all 0.2s;
    position: relative;
}
.drop-zone:hover, .drop-zone.drag-over {
    border-color: #8b7355;
    background: #faf8f5;
}
.drop-zone__icon { font-size: 48px; margin-bottom: 12px; }
.drop-zone__text { font-size: 15px; color: #555; }
.drop-zone__hint { font-size: 12px; color: #999; margin-top: 8px; }
.drop-zone input[type="file"] {
    position: absolute;
    inset: 0;
    opacity: 0;
    cursor: pointer;
}
.progress-wrap {
    margin-top: 24px;
    display: none;
}
.progress-wrap.active { display: block; }
.progress-bar {
    height: 8px;
    background: #e8e6e1;
    border-radius: 4px;
    overflow: hidden;
}
.progress-bar__fill {
    height: 100%;
    background: #8b7355;
    border-radius: 4px;
    width: 0%;
    transition: width 0.3s;
}
.progress-text {
    font-size: 13px;
    color: #666;
    margin-top: 8px;
    text-align: center;
}
.file-info {
    margin-top: 16px;
    padding: 12px 16px;
    background: #faf8f5;
    border-radius: 8px;
    font-size: 13px;
    color: #555;
    display: none;
}
.file-info.active { display: block; }
.result {
    margin-top: 24px;
    padding: 16px;
    border-radius: 12px;
    text-align: center;
    font-size: 15px;
    display: none;
}
.result.success {
    display: block;
    background: #e8f5e9;
    color: #2e7d32;
}
.result.error {
    display: block;
    background: #fbe9e7;
    color: #c62828;
}
.formats { font-size: 12px; color: #999; margin-top: 16px; text-align: center; }
</style>
</head>
<body>
<div class="card">
    <div class="logo">Глава</div>
    <div class="subtitle">Загрузка аудиофайла для вашей книги</div>

    <div class="drop-zone" id="dropZone">
        <div class="drop-zone__icon">🎵</div>
        <div class="drop-zone__text">Перетащите файл сюда или нажмите для выбора</div>
        <div class="drop-zone__hint">Максимум 500 МБ</div>
        <input type="file" id="fileInput" accept=".mp3,.ogg,.m4a,.wav,.opus,.oga">
    </div>

    <div class="file-info" id="fileInfo"></div>

    <div class="progress-wrap" id="progressWrap">
        <div class="progress-bar"><div class="progress-bar__fill" id="progressFill"></div></div>
        <div class="progress-text" id="progressText">Загрузка...</div>
    </div>

    <div class="result" id="result"></div>

    <div class="formats">Форматы: mp3, ogg, m4a, wav, opus, oga</div>
</div>

<script>
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const fileInfo = document.getElementById('fileInfo');
const progressWrap = document.getElementById('progressWrap');
const progressFill = document.getElementById('progressFill');
const progressText = document.getElementById('progressText');
const result = document.getElementById('result');
const TOKEN = '{{ token }}';

['dragenter','dragover'].forEach(e => {
    dropZone.addEventListener(e, ev => { ev.preventDefault(); dropZone.classList.add('drag-over'); });
});
['dragleave','drop'].forEach(e => {
    dropZone.addEventListener(e, ev => { ev.preventDefault(); dropZone.classList.remove('drag-over'); });
});
dropZone.addEventListener('drop', ev => {
    const files = ev.dataTransfer.files;
    if (files.length) uploadFile(files[0]);
});
fileInput.addEventListener('change', () => {
    if (fileInput.files.length) uploadFile(fileInput.files[0]);
});

function formatSize(bytes) {
    if (bytes < 1024) return bytes + ' Б';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' КБ';
    return (bytes / 1048576).toFixed(1) + ' МБ';
}

function uploadFile(file) {
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    const allowed = ['.mp3','.ogg','.m4a','.wav','.opus','.oga'];
    if (!allowed.includes(ext)) {
        showResult('Неподдерживаемый формат. Принимаем: ' + allowed.join(', '), true);
        return;
    }
    if (file.size > 500 * 1024 * 1024) {
        showResult('Файл слишком большой (макс. 500 МБ)', true);
        return;
    }

    fileInfo.textContent = file.name + ' — ' + formatSize(file.size);
    fileInfo.classList.add('active');
    progressWrap.classList.add('active');
    dropZone.style.display = 'none';
    result.style.display = 'none';
    result.className = 'result';

    const form = new FormData();
    form.append('file', file);

    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/upload/' + TOKEN);

    xhr.upload.addEventListener('progress', ev => {
        if (ev.lengthComputable) {
            const pct = Math.round(ev.loaded / ev.total * 100);
            progressFill.style.width = pct + '%';
            progressText.textContent = pct + '% — ' + formatSize(ev.loaded) + ' из ' + formatSize(ev.total);
        }
    });

    xhr.onload = function() {
        progressWrap.classList.remove('active');
        try {
            const data = JSON.parse(xhr.responseText);
            if (xhr.status === 200 && data.ok) {
                showResult('Файл загружен! Можете закрыть эту страницу и вернуться в Telegram.', false);
            } else {
                showResult(data.error || 'Ошибка загрузки', true);
                dropZone.style.display = '';
            }
        } catch(e) {
            showResult('Ошибка сервера', true);
            dropZone.style.display = '';
        }
    };
    xhr.onerror = function() {
        progressWrap.classList.remove('active');
        showResult('Ошибка сети. Проверьте соединение и попробуйте снова.', true);
        dropZone.style.display = '';
    };
    xhr.send(form);
}

function showResult(msg, isError) {
    result.textContent = msg;
    result.className = 'result ' + (isError ? 'error' : 'success');
}
</script>
</body>
</html>
"""


@upload_api.route("/upload/<token>", methods=["GET"])
def upload_page(token: str):
    """Страница загрузки файла."""
    info = _validate_token(token)
    if not info:
        return render_template_string(
            "<html><body style='font-family:sans-serif;text-align:center;padding:80px'>"
            "<h2>Ссылка недействительна</h2>"
            "<p>Ссылка устарела или уже использована. Запросите новую в боте.</p>"
            "</body></html>"
        ), 410
    return render_template_string(UPLOAD_HTML, token=token)


@upload_api.route("/upload/<token>", methods=["POST"])
def upload_file(token: str):
    """Приём загруженного файла."""
    info = _validate_token(token)
    if not info:
        return jsonify({"ok": False, "error": "Ссылка недействительна или устарела"}), 410

    if "file" not in request.files:
        return jsonify({"ok": False, "error": "Файл не получен"}), 400

    f = request.files["file"]
    if not f.filename:
        return jsonify({"ok": False, "error": "Пустое имя файла"}), 400

    ext = Path(f.filename).suffix.lower()
    if ext not in AUDIO_EXTENSIONS:
        return jsonify({"ok": False, "error": f"Формат {ext} не поддерживается. Принимаем: mp3, ogg, m4a, wav, opus, oga"}), 400

    telegram_id = info["telegram_id"]
    user_id = info["user_id"]

    try:
        import storage
        import db

        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp_path = tmp.name
            f.save(tmp_path)

        try:
            file_size = os.path.getsize(tmp_path)
            if file_size > MAX_FILE_SIZE:
                return jsonify({"ok": False, "error": "Файл слишком большой (макс. 500 МБ)"}), 400

            storage_key = storage.upload_file(tmp_path, user_id)
            voice = db.save_voice_message(
                user_id=user_id,
                telegram_file_id=f"web_upload_{uuid.uuid4().hex[:8]}",
                storage_key=storage_key,
                duration=None,
            )
            logger.info(
                "Web upload: user_id=%s, telegram_id=%s, file=%s, size=%s",
                user_id, telegram_id, f.filename, file_size,
            )
        finally:
            Path(tmp_path).unlink(missing_ok=True)

        # Удаляем использованный токен
        import db as _db
        with _db.get_connection() as _conn:
            with _conn.cursor() as _cur:
                _cur.execute("DELETE FROM upload_tokens WHERE token = %s", (token,))

        # Уведомляем в Telegram + запускаем транскрипцию в фоне
        _notify_and_transcribe(telegram_id, user_id, storage_key, f.filename, voice)

        return jsonify({"ok": True})

    except Exception as e:
        logger.exception("Web upload error: %s", e)
        return jsonify({"ok": False, "error": "Внутренняя ошибка сервера"}), 500


def _notify_and_transcribe(
    telegram_id: int,
    user_id: int,
    storage_key: str,
    filename: str,
    voice: dict | None,
):
    """Уведомляет пользователя в Telegram и запускает транскрипцию."""
    def _run():
        logger.info("_notify_and_transcribe started: telegram_id=%s, file=%s", telegram_id, filename)
        try:
            import requests as _req
            bot_token = os.environ.get("BOT_TOKEN", "")
            if bot_token:
                resp = _req.post(
                    f"https://api.telegram.org/bot{bot_token}/sendMessage",
                    json={
                        "chat_id": telegram_id,
                        "text": f"Файл «{filename}» загружен через браузер. Обрабатываем...",
                    },
                    timeout=10,
                )
                logger.info("Telegram notify sent: status=%s", resp.status_code)
            else:
                logger.warning("BOT_TOKEN not set, skipping Telegram notify")
        except Exception as e:
            logger.warning("Telegram notify failed: %s", e)

        # Транскрипция
        if voice:
            try:
                from pipeline_transcribe_bio import run_pipeline_sync
                run_pipeline_sync(
                    voice_id=voice["id"],
                    storage_key=storage_key,
                    telegram_id=telegram_id,
                    username=None,
                )
            except ImportError:
                logger.info("pipeline_transcribe_bio not available, skipping transcription")
            except Exception as e:
                logger.warning("Transcription after web upload failed: %s", e)

    t = threading.Thread(target=_run, daemon=True)
    t.start()
