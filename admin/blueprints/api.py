"""
Внутренний API для n8n — без UI-авторизации.
Доступен только с localhost ИЛИ с правильным X-Api-Key заголовком.
Маршруты: /api/prompts/<role>           GET
          /api/prompts/<role>/upload     POST  — загрузка .md промпта
          /api/jobs/update               POST
          /api/send-book-pdf             POST  — генерация PDF и отправка в Telegram
"""
import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path

import requests as _requests
from flask import Blueprint, abort, jsonify, request

from admin import db_admin as dba

_ROOT_DIR = Path(__file__).resolve().parent.parent.parent
_PROMPTS_DIR = _ROOT_DIR / "prompts"
_PROMPTS_BACKUP_DIR = _PROMPTS_DIR / "backups"
_PIPELINE_CONFIG_PATH = _PROMPTS_DIR / "pipeline_config.json"

_VALID_AGENT_KEYS = {
    "cleaner", "fact_extractor", "historian", "ghostwriter", "fact_checker",
    "literary_editor", "proofreader", "photo_editor", "layout_designer",
    "qa_layout", "cover_designer", "layout_art_director", "interview_architect",
}

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


# ── POST /api/prompts/<role>/upload ───────────────────────────────

@bp.post("/prompts/<role>/upload")
def upload_prompt(role: str):
    """Загрузка .md-файла промпта через API.

    Multipart form-data:
      file      — .md файл с содержимым промпта (обязательно)
      filename  — имя для сохранения, например 11_interview_architect_v4.2.md
                  (опционально; если не указано — перезаписывает текущий активный файл)

    Авторизация: X-Api-Key header.

    Возвращает:
      {"ok": true, "saved_as": "...", "size_kb": "..."}
    """
    _check_access()

    if role not in _VALID_AGENT_KEYS:
        return jsonify({"ok": False, "error": f"Unknown agent: {role}"}), 400

    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"ok": False, "error": "file required"}), 400
    if not f.filename.lower().endswith(".md"):
        return jsonify({"ok": False, "error": "only .md files accepted"}), 400

    # Загружаем конфиг
    if not _PIPELINE_CONFIG_PATH.exists():
        return jsonify({"ok": False, "error": "pipeline_config.json not found"}), 500
    with open(_PIPELINE_CONFIG_PATH, encoding="utf-8") as fp:
        cfg = json.load(fp)

    # Имя целевого файла: из параметра или из конфига
    custom_filename = (request.form.get("filename") or "").strip()
    if custom_filename:
        if not custom_filename.endswith(".md"):
            return jsonify({"ok": False, "error": "filename must end with .md"}), 400
        target_name = custom_filename
        # Обновляем prompt_file в конфиге на новое имя
        if role not in cfg:
            cfg[role] = {}
        cfg[role]["prompt_file"] = target_name
    else:
        target_name = cfg.get(role, {}).get("prompt_file") or f"{role}_v1.md"

    target_path = _PROMPTS_DIR / target_name

    # Бэкап старого файла
    if target_path.exists():
        _PROMPTS_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{target_path.stem}_{ts}{target_path.suffix}"
        shutil.copy2(target_path, _PROMPTS_BACKUP_DIR / backup_name)

    # Сохраняем новый файл
    _PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
    f.save(str(target_path))
    size_kb = f"{target_path.stat().st_size / 1024:.1f}"

    # Обновляем метаданные в конфиге
    if role not in cfg:
        cfg[role] = {}
    cfg[role]["_last_uploaded"] = datetime.now().strftime("%d.%m.%Y %H:%M")
    cfg[role]["_uploaded_filename"] = f.filename
    with open(_PIPELINE_CONFIG_PATH, "w", encoding="utf-8") as fp:
        json.dump(cfg, fp, ensure_ascii=False, indent=2)

    logger.info("api: prompt uploaded role=%s file=%s size=%s KB", role, target_name, size_kb)
    return jsonify({"ok": True, "saved_as": target_name, "size_kb": size_kb}), 200


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
# Body: {telegram_id, bio_text, character_name, draft_id?, cover_spec?, photo_layout?}

@bp.post("/send-book-pdf")
def send_book_pdf():
    _check_access()
    data = request.get_json(silent=True) or {}

    telegram_id = data.get("telegram_id")
    bio_text = data.get("bio_text", "")
    character_name = data.get("character_name", "Герой книги")
    draft_id = data.get("draft_id", 0)
    cover_spec = data.get("cover_spec") or {}
    photo_layout = data.get("photo_layout") or []  # от Photo Editor агента

    if not telegram_id:
        return jsonify({"error": "telegram_id required"}), 400
    if not bio_text:
        return jsonify({"error": "bio_text required"}), 400

    bot_token = os.environ.get("BOT_TOKEN", "")
    if not bot_token:
        return jsonify({"error": "BOT_TOKEN not configured"}), 500

    # ── AI-обложка через Replicate ──────────────────────────────────
    cover_image_bytes: bytes | None = None
    replicate_token = os.environ.get("REPLICATE_API_TOKEN", "")
    visual_style = cover_spec.get("visual_style", "") if cover_spec else ""

    if replicate_token and visual_style:
        try:
            from replicate_client import generate_cover_image
            logger.info("send_book_pdf: генерируем AI-обложку для '%s'", character_name)
            cover_image_bytes = generate_cover_image(
                visual_style=visual_style,
                character_name=character_name,
                api_token=replicate_token,
            )
            if cover_image_bytes:
                logger.info(
                    "send_book_pdf: AI-обложка сгенерирована, %d байт", len(cover_image_bytes)
                )
            else:
                logger.warning("send_book_pdf: Replicate вернул None, используем текстовую обложку")
        except Exception as e:
            logger.warning("send_book_pdf: ошибка Replicate, fallback на текстовую обложку: %s", e)
    elif not visual_style:
        logger.info("send_book_pdf: visual_style не задан, используем текстовую обложку")
    elif not replicate_token:
        logger.info("send_book_pdf: REPLICATE_API_TOKEN не задан, используем текстовую обложку")

    # ── Загрузка фотографий из S3 ──────────────────────────────────────
    photo_items: list[dict] = []
    try:
        import db as _db
        import storage as _storage
        import db_draft as _db_draft
        # Берём только фото, загруженные после создания драфта (фильтрует фото из других сессий)
        since_dt = None
        if draft_id:
            try:
                dr = _db_draft.get_draft_by_id(int(draft_id))
                if dr and dr.get("created_at"):
                    since_dt = dr["created_at"]
            except Exception:
                pass
        user_photos = _db.get_user_photos(int(telegram_id), limit=50, since=since_dt)
        # photo_layout: подписи от Photo Editor (id вида photo_001 или порядковый индекс)
        if user_photos:
            caption_map: dict[str, str] = {}
            for item in (photo_layout or []):
                pid = str(item.get("id", "") or item.get("photo_id", "") or "")
                cap = (item.get("caption") or item.get("caption_text") or
                       (item.get("analysis") or {}).get("description", ""))
                if pid:
                    caption_map[pid] = cap

            for idx, ph in enumerate(user_photos):
                photo_key = f"photo_{idx + 1:03d}"
                # подпись: по id, по порядку в массиве layout, или пусто
                caption = caption_map.get(photo_key, "")
                if not caption and idx < len(photo_layout or []):
                    alt = photo_layout[idx]
                    caption = (alt.get("caption") or alt.get("caption_text") or
                               (alt.get("analysis") or {}).get("description", ""))
                # Сохраняем подпись обратно в БД, если её ещё нет
                if caption and not ph.get("caption"):
                    try:
                        with _db.get_connection() as _conn:
                            with _conn.cursor() as _cur:
                                _cur.execute(
                                    "UPDATE photos SET caption=%s WHERE id=%s",
                                    (caption, ph["id"])
                                )
                    except Exception:
                        pass
                try:
                    import tempfile, os as _os
                    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tf:
                        tmp_path = tf.name
                    _storage.download_file(ph["storage_key"], tmp_path)
                    with open(tmp_path, "rb") as f:
                        img_bytes = f.read()
                    _os.unlink(tmp_path)
                    photo_items.append({"caption": caption, "image_bytes": img_bytes})
                except Exception as pe:
                    logger.warning("send_book_pdf: не удалось загрузить фото %s: %s",
                                   ph.get("storage_key"), pe)
        logger.info("send_book_pdf: загружено %d фото для вставки", len(photo_items))
    except Exception as e:
        logger.warning("send_book_pdf: ошибка загрузки фото, продолжаем без фото: %s", e)

    try:
        from pdf_book import generate_book_pdf
        pdf_bytes = generate_book_pdf(
            bio_text,
            character_name=character_name,
            cover_spec=cover_spec if cover_spec else None,
            cover_image_bytes=cover_image_bytes,
            photo_items=photo_items if photo_items else None,
        )
    except Exception as e:
        logger.exception("send_book_pdf: ошибка генерации PDF: %s", e)
        return jsonify({"error": f"pdf generation failed: {e}"}), 500

    # Имя файла
    safe_name = "".join(c for c in character_name if c.isalnum() or c in " _-")[:40].strip()
    filename = f"Glava_{safe_name or 'kniga'}.pdf"

    # Сохраняем версию книги ДО отправки в Telegram (не зависит от успеха доставки)
    saved_version = None
    try:
        saved_version = dba.save_book_version(
            int(telegram_id),
            bio_text=bio_text,
            character_name=character_name,
            pdf_filename=filename,
        )
        logger.info("send_book_pdf: book_version сохранена для telegram_id=%s", telegram_id)
    except Exception as e:
        logger.warning("send_book_pdf: не удалось сохранить book_version: %s", e)

    # Отправляем через Telegram Bot API sendDocument
    tg_url = f"https://api.telegram.org/bot{bot_token}/sendDocument"
    tg_error = None
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
            tg_error = tg_result
        else:
            logger.info(
                "send_book_pdf: PDF '%s' (%d байт) отправлен telegram_id=%s",
                filename, len(pdf_bytes), telegram_id,
            )
    except Exception as e:
        logger.warning("send_book_pdf: ошибка отправки в Telegram (книга сохранена в БД): %s", e)
        tg_error = str(e)

    return jsonify({
        "ok": True,
        "filename": filename,
        "size": len(pdf_bytes),
        "telegram_sent": tg_error is None,
        "telegram_error": tg_error,
        "version": saved_version,
    }), 200


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


# ── POST /api/state/transition ───────────────────────────────────
# n8n и бот вызывают при каждом переходе состояния проекта.
# Body: {telegram_id, state, draft_id?, character_name?, phase?, metadata?, notes?}

@bp.post("/state/transition")
def state_transition():
    _check_access()
    data = request.get_json(silent=True) or {}

    telegram_id = data.get("telegram_id")
    new_state   = data.get("state", "")

    if not telegram_id:
        return jsonify({"error": "telegram_id required"}), 400

    if new_state not in dba.VALID_STATES:
        return jsonify({
            "error": f"invalid state: {new_state}",
            "valid": list(dba.VALID_STATES),
        }), 400

    try:
        result = dba.upsert_project_state(
            telegram_id    = int(telegram_id),
            new_state      = new_state,
            draft_id       = data.get("draft_id"),
            character_name = data.get("character_name"),
            phase          = data.get("phase", "A"),
            metadata       = data.get("metadata"),
            notes          = data.get("notes", ""),
        )
        logger.info(
            "state_transition: telegram_id=%s %s → %s",
            telegram_id, result.get("previous_state"), new_state,
        )
        return jsonify({"ok": True, **result}), 200
    except Exception as e:
        logger.exception("state_transition error: %s", e)
        return jsonify({"error": str(e)}), 500


# ── GET /api/state/<telegram_id> ─────────────────────────────────

@bp.get("/state/<int:telegram_id>")
def get_state(telegram_id: int):
    _check_access()
    try:
        result = dba.get_project_state(telegram_id)
        if result is None:
            return jsonify({"telegram_id": telegram_id, "state": "created", "found": False}), 200
        return jsonify({"found": True, **result}), 200
    except Exception as e:
        logger.exception("get_state error: %s", e)
        return jsonify({"error": str(e)}), 500


# ── GET /api/book-context/<telegram_id> ──────────────────────────
# n8n Phase B запрашивает текст последней версии книги.

@bp.get("/book-context/<int:telegram_id>")
def book_context(telegram_id: int):
    _check_access()
    try:
        row = dba.get_last_book_version(telegram_id)
        if row is None:
            return jsonify({"found": False, "bio_text": "", "version": 0}), 200
        return jsonify({
            "found": True,
            "bio_text": row.get("bio_text", ""),
            "version": row.get("version", 1),
            "character_name": row.get("character_name", ""),
        }), 200
    except Exception as e:
        logger.exception("book_context error: %s", e)
        return jsonify({"error": str(e)}), 500


# ── POST /api/orchestrate/phase-b-revision ────────────────────────
# Phase B: применяет правку к тексту книги через нужных агентов.
# Body: {book_text, correction_type, correction_content, character_name, project_id?}

@bp.post("/orchestrate/phase-b-revision")
def orchestrate_phase_b():
    _check_access()
    data = request.get_json(silent=True) or {}

    book_text          = data.get("book_text", "")
    correction_type    = data.get("correction_type", "structural")
    correction_content = data.get("correction_content", "")
    character_name     = data.get("character_name", "Герой книги")
    project_id         = str(data.get("project_id", "proj"))

    if not correction_content:
        return jsonify({"error": "correction_content is required"}), 400
    # book_text может быть пустым (первый запуск Phase B до сохранения версии)
    # в этом случае используем correction_content как основу

    openai_key = os.environ.get("OPENAI_API_KEY", "")
    if not openai_key:
        return jsonify({"error": "OPENAI_API_KEY not configured"}), 500

    try:
        from orchestrator import run_phase_b_revision
        result = run_phase_b_revision(
            book_text=book_text,
            correction_type=correction_type,
            correction_content=correction_content,
            character_name=character_name,
            openai_key=openai_key,
            admin_url="http://127.0.0.1:5001",
            project_id=project_id,
        )
        return jsonify({"ok": True, **result}), 200
    except Exception as e:
        logger.exception("orchestrate_phase_b error: %s", e)
        return jsonify({"error": str(e)}), 500


# ── GET /api/health ───────────────────────────────────────────────

@bp.get("/health")
def health():
    return jsonify({"status": "ok"}), 200


# ── POST /api/agents/historian ────────────────────────────────────────
# Вызывает историка через OpenAI и возвращает historical_context.
# Body: {fact_map, triage_result, character_name, project_id}

@bp.post("/agents/historian")
def agent_historian():
    _check_access()
    import json as _json

    data = request.get_json(silent=True) or {}
    fact_map      = data.get("fact_map", {})
    triage_result = data.get("triage_result", {})
    character_name = data.get("character_name", "Герой книги")
    project_id    = str(data.get("project_id", "proj"))

    openai_key = os.environ.get("OPENAI_API_KEY", "")
    if not openai_key:
        return jsonify({"error": "OPENAI_API_KEY not set"}), 500

    admin_url = "http://127.0.0.1:5001"

    prompt_resp = _requests.get(f"{admin_url}/api/prompts/historian", timeout=10)
    system_prompt = ""
    if prompt_resp.ok:
        system_prompt = prompt_resp.json().get("text", "")
    if not system_prompt:
        system_prompt = (
            "Ты Историк. На основе фактов о герое опиши исторический контекст его эпохи. "
            "Верни только валидный JSON с полями: period_overview, key_historical_events "
            "(массив {year, event, relevance}), cultural_context, political_context, "
            "everyday_life_notes, historical_backdrop."
        )

    user_msg = _json.dumps({
        "phase": "A",
        "project_id": project_id,
        "character_name": character_name,
        "pipeline_variant": triage_result.get("pipeline_variant", "standard"),
        "subject_period": triage_result.get("subject_period", "советский"),
        "timeline": (fact_map.get("timeline") or [])[:20],
        "subject": fact_map.get("subject") or {},
        "locations": [l.get("name", "") for l in (fact_map.get("locations") or [])],
    }, ensure_ascii=False)

    try:
        resp = _requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {openai_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_msg},
                ],
                "temperature": 0.3,
                "max_tokens": 3000,
            },
            timeout=120,
        )
        resp.raise_for_status()
        raw = resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.exception("historian: openai error: %s", e)
        return jsonify({"error": str(e)}), 500

    historical_context = {}
    t = raw.strip()
    s, e2 = t.find("{"), t.rfind("}")
    if s != -1 and e2 > s:
        try:
            historical_context = _json.loads(t[s:e2 + 1])
        except Exception:
            historical_context = {"period_overview": raw[:500]}

    return jsonify({"historical_context": historical_context}), 200
