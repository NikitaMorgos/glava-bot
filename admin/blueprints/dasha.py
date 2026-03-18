"""Панель Даши (Product Manager) — /dasha/."""
import os
from datetime import datetime

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for, session

from admin.auth import role_required
from admin import db_admin as dba

bp = Blueprint("dasha", __name__, url_prefix="/dasha")

# Сообщения бота (key → человекочитаемое имя)
BOT_MESSAGE_KEYS = [
    ("intro_main", "Приветствие (главное)"),
    ("intro_example", "Пример книги"),
    ("intro_price", "Стоимость"),
    ("config_characters", "Персонажи — ввод"),
    ("config_characters_list", "Персонажи — список"),
    ("email_input", "Ввод email"),
    ("email_error", "Ошибка email"),
    ("order_summary", "Итого заказа"),
    ("payment_init", "Оплата создана"),
    ("payment_wait", "Ожидание оплаты"),
    ("payment_still_pending", "Оплата ещё не поступила"),
    ("resume_draft", "Возобновление черновика"),
    ("resume_payment", "Оплата в процессе"),
    ("blocked_media", "Блокировка до оплаты"),
    ("online_meeting_intro", "Онлайн-встреча — ввод"),
    ("online_meeting_link_sent", "Онлайн — ссылка отправлена"),
    ("online_meeting_telemost_sent", "Онлайн — ссылка Телемост"),
    ("online_meeting_bad_link", "Онлайн — неверная ссылка"),
    ("online_meeting_error", "Онлайн — ошибка"),
]

AGENT_ROLES = [
    ("triage_agent",      "00 · Триаж-агент"),
    ("transcriber",       "01 · Транскрибатор"),
    ("fact_extractor",    "02 · Фактолог"),
    ("historian",         "02b · Историк"),
    ("ghostwriter",       "03 · Писатель"),
    ("fact_checker",      "04 · Фактчекер"),
    ("literary_editor",   "05 · Литредактор"),
    ("proofreader",       "06 · Корректор"),
    ("photo_editor",      "07 · Фоторедактор"),
    ("layout_designer",   "08 · Верстальщик"),
    ("layout_qa",         "09 · Контролёр вёрстки"),
    ("producer",          "10 · Продюсер"),
    ("interview_architect","11 · Интервьюер"),
    ("cover_designer",    "12 · Дизайнер обложки"),
]


# ── Промпты агентов ───────────────────────────────────────────────
@bp.route("/")
@role_required("dev", "dasha", "lena")
def index():
    return redirect(url_for("dasha.prompts"))


@bp.route("/prompts")
@role_required("dev", "dasha", "lena")
def prompts():
    rows = dba.get_all_prompts()
    role_map = dict(AGENT_ROLES)
    return render_template("dasha/prompts.html", prompts=rows,
                           agent_roles=AGENT_ROLES, role_map=role_map)


@bp.route("/prompts/<role>", methods=["GET", "POST"])
@role_required("dev", "dasha", "lena")
def prompt_edit(role: str):
    role_map = dict(AGENT_ROLES)
    if role not in role_map:
        flash("Неизвестная роль", "error")
        return redirect(url_for("dasha.prompts"))

    if request.method == "POST":
        text = request.form.get("prompt_text", "").strip()
        if text:
            author = request.headers.get("X-Session-User", "dasha")
            from flask import session
            author = session.get("username", "dasha")
            dba.save_prompt(role, text, author)
            flash(f"Промпт «{role_map[role]}» сохранён", "success")
        return redirect(url_for("dasha.prompts"))

    current = dba.get_prompt(role)
    history = dba.get_prompt_history(role)
    return render_template("dasha/prompt_edit.html",
                           role=role, role_name=role_map[role],
                           current=current, history=history)


# ── Dashboard проектов (State Machine) ────────────────────────────

@bp.route("/projects")
@role_required("dev", "dasha", "lena")
def projects():
    all_projects = dba.get_all_project_states()
    summary = dba.get_project_states_summary()
    return render_template(
        "dasha/projects.html",
        projects=all_projects,
        summary=summary,
        state_labels=dba.STATE_LABELS,
        state_colors=dba.STATE_COLORS,
        valid_states=dba.VALID_STATES,
    )


@bp.route("/projects/<int:telegram_id>/set_state", methods=["POST"])
@role_required("dev", "dasha")
def set_project_state(telegram_id: int):
    new_state = request.form.get("state", "")
    notes     = request.form.get("notes", "")
    if new_state in dba.VALID_STATES:
        dba.upsert_project_state(telegram_id, new_state, notes=notes)
        flash(f"Статус проекта обновлён: {dba.STATE_LABELS.get(new_state, new_state)}", "success")
    else:
        flash("Неверный статус", "danger")
    return redirect(url_for("dasha.projects"))


# ── Сообщения бота ───────────────────────────────────────────────
@bp.route("/bot_messages")
@role_required("dev", "dasha", "lena")
def bot_messages():
    rows = dba.get_bot_messages()
    prompt_map = {r["role"]: r for r in rows}
    return render_template(
        "dasha/bot_messages.html",
        bot_keys=BOT_MESSAGE_KEYS,
        prompt_map=prompt_map,
    )


@bp.route("/bot_flow")
@role_required("dev", "dasha", "lena")
def bot_flow():
    """Живая карта флоу бота."""
    return render_template("dasha/bot_flow.html")


@bp.route("/bot_messages_json")
@role_required("dev", "dasha", "lena")
def bot_messages_json():
    """JSON со всеми текстами бота для живой карты флоу."""
    from flask import jsonify
    rows = dba.get_bot_messages()
    data = {r["role"].replace("bot_", ""): r.get("prompt_text", "") for r in rows}
    return jsonify(data)


@bp.route("/bot_messages/<key>", methods=["GET", "POST"])
@role_required("dev", "dasha", "lena")
def bot_message_edit(key: str):
    key_map = dict(BOT_MESSAGE_KEYS)
    if key not in key_map:
        flash("Неизвестный ключ сообщения", "error")
        return redirect(url_for("dasha.bot_messages"))

    role = f"bot_{key}"
    if request.method == "POST":
        text = request.form.get("prompt_text", "").strip()
        if text:
            from flask import session
            author = session.get("username", "dasha")
            dba.save_prompt(role, text, author)
            flash(f"Сообщение «{key_map[key]}» сохранено", "success")
        return redirect(url_for("dasha.bot_messages"))

    current = dba.get_prompt(role)
    history = dba.get_prompt_history(role)
    return render_template(
        "dasha/bot_message_edit.html",
        key=key,
        key_name=key_map[key],
        current=current,
        history=history,
    )


# ── Заказы / пайплайн ────────────────────────────────────────────
@bp.route("/orders")
@role_required("dev", "dasha", "lena")
def orders():
    rows = dba.get_pipeline_jobs()
    return render_template("dasha/orders.html", orders=rows)


@bp.route("/orders/<int:telegram_id>")
@role_required("dev", "dasha", "lena")
def order_detail(telegram_id: int):
    job = dba.get_pipeline_job(telegram_id)
    return render_template("dasha/order_detail.html", job=job, telegram_id=telegram_id)


@bp.route("/orders/<int:telegram_id>/start", methods=["POST"])
@role_required("dev", "dasha", "lena")
def pipeline_start(telegram_id: int):
    """Запустить Phase A для клиента через n8n webhook."""
    import requests as req
    n8n_url = os.environ.get("N8N_WEBHOOK_PHASE_A", "http://localhost:5678/webhook/start-pipeline")
    try:
        r = req.post(n8n_url, json={"telegram_id": telegram_id}, timeout=10)
        flash(f"Пайплайн запущен (HTTP {r.status_code})", "success")
    except Exception as e:
        flash(f"Ошибка запуска: {e}", "error")
    return redirect(url_for("dasha.order_detail", telegram_id=telegram_id))


# ── Предложения по флоу ──────────────────────────────────────────
@bp.route("/suggest_change", methods=["POST"])
@role_required("dev", "dasha", "lena")
def suggest_change():
    data = request.get_json(silent=True) or {}
    screen_id = data.get("screen_id", "").strip()
    screen_title = data.get("screen_title", "").strip()
    suggestion = data.get("suggestion", "").strip()
    if not screen_id or not suggestion:
        return jsonify({"ok": False, "error": "Заполните все поля"}), 400
    author = session.get("username", "dasha")
    new_id = dba.add_flow_suggestion(screen_id, screen_title, suggestion, author)
    return jsonify({"ok": True, "id": new_id})


# ── Отчёты ───────────────────────────────────────────────────────
@bp.route("/reports")
@role_required("dev", "dasha", "lena")
def reports():
    stats = dba.get_pipeline_stats()
    return render_template("dasha/reports.html", stats=stats)
