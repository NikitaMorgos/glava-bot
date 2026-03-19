"""Панель Даши (Product Manager) — /dasha/."""
import json
import os
import subprocess
import sys
import time
from datetime import datetime

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for, session

from admin.auth import role_required
from admin import db_admin as dba

bp = Blueprint("dasha", __name__, url_prefix="/dasha")

# Сообщения бота (key → человекочитаемое имя)
BOT_MESSAGE_KEYS = [
    # ── Pre-pay ──────────────────────────────────────────────────────────────
    ("intro_main",              "1.1 · Приветствие (главное)"),
    ("intro_example",           "1.2 · Пример книги"),
    ("intro_price",             "1.3 · Стоимость"),
    ("character_name",          "2.1 · О ком книга — ввод имени"),
    ("character_relation",      "2.1 · О ком книга — ввод родства"),
    ("config_characters",       "2.x · Персонажи — ввод (старый)"),
    ("config_characters_list",  "2.x · Персонажи — список (старый)"),
    ("email_input",             "3.1 · Ввод email"),
    ("email_error",             "E.1 · Ошибка email"),
    ("order_summary",           "4.1 · Итого заказа"),
    ("payment_init",            "4.2 · Оплата создана"),
    ("payment_wait",            "4.3 · Ожидание оплаты"),
    ("payment_still_pending",   "4.3 · Оплата ещё не поступила"),
    ("resume_draft",            "0.x · Возобновление черновика"),
    ("resume_payment",          "0.x · Оплата в процессе"),
    ("blocked_media",           "Блокировка до оплаты"),
    # ── Post-pay: нарраторы ──────────────────────────────────────────────────
    ("narrators_setup",         "6.1 · Кто расскажет?"),
    ("narrator_relation",       "6.1 · Родство нарратора"),
    ("narrators_list",          "6.1 · Список нарраторов"),
    # ── Post-pay: гид по интервью ────────────────────────────────────────────
    ("interview_guide",         "7.1 · Как провести интервью"),
    ("interview_questions",     "7.2 · Вопросы-подсказки"),
    # ── Post-pay: загрузка ───────────────────────────────────────────────────
    ("upload_who",              "8.1 · Кто говорит?"),
    ("upload_audio",            "8.2 · Загрузка материалов"),
    ("upload_file_accepted",    "8.2 · Файл принят"),
    ("upload_photo",            "8.3 · Загрузка фото"),
    ("upload_photo_accepted",   "8.3 · Фото добавлено"),
    ("upload_summary",          "8.4 · Итог загрузки"),
    ("upload_processing",       "8.5 · Обработка материалов"),
    # ── Post-pay: AI результат ───────────────────────────────────────────────
    ("interview_questions_ready","8.6 · Уточняющие вопросы готовы"),
    ("interview2",              "9.1 · Второе интервью"),
    ("interview2_confirm",      "9.2 · Подтверждение второго"),
    # ── Сборка книги ─────────────────────────────────────────────────────────
    ("assembling",              "10.1 · Сборка книги — ожидание"),
    ("book_ready",              "10.2 · Книга готова!"),
    # ── Правки ───────────────────────────────────────────────────────────────
    ("revision_prompt",         "11.1 · Комментарий к правке"),
    ("revision_processing",     "11.2 · Обработка правок"),
    ("revision_ready",          "11.3 · Обновлённая книга"),
    ("revision_debounce",       "11.1 · Debounce — принято"),
    ("revision_limit",          "11.x · Лимит правок исчерпан"),
    # ── Версии ───────────────────────────────────────────────────────────────
    ("versions_empty",          "12.1 · Нет версий"),
    ("versions_list",           "12.1 · Список версий"),
    ("versions_rollback_confirm","12.2 · Подтверждение отката"),
    # ── Завершение ───────────────────────────────────────────────────────────
    ("finalize_confirm",        "13.1 · Подтверждение завершения"),
    ("finalized",               "14.1 · Книга завершена"),
    ("print_soon",              "14.2 · Печать — скоро"),
    # ── Возврат ──────────────────────────────────────────────────────────────
    ("refund_reason",           "15.1 · Причина возврата"),
    ("refund_submitted",        "15.2 · Заявка принята"),
    # ── Ошибки ───────────────────────────────────────────────────────────────
    ("assembly_error",          "E.3 · Ошибка сборки"),
    ("unsupported_file",        "E.4 · Неподдерживаемый файл"),
    # ── Онлайн-встречи ───────────────────────────────────────────────────────
    ("online_meeting_intro",    "Онлайн-встреча — ввод"),
    ("online_meeting_link_sent","Онлайн — ссылка отправлена"),
    ("online_meeting_telemost_sent","Онлайн — ссылка Телемост"),
    ("online_meeting_bad_link", "Онлайн — неверная ссылка"),
    ("online_meeting_error",    "Онлайн — ошибка"),
]

AGENT_ROLES = [
    ("triage_agent",      "00 · Триаж Phase A"),
    ("triage_b",          "00b · Триаж Phase B"),
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
    summary      = dba.get_project_states_summary()

    # Последние версии книг по каждому telegram_id
    book_versions = {}
    for p in all_projects:
        try:
            row = dba.get_last_book_version(p["telegram_id"])
            if row:
                book_versions[p["telegram_id"]] = row
        except Exception:
            pass

    # Статусы пайплайна
    pipeline_jobs = {}
    try:
        for job in dba.get_pipeline_jobs():
            tid = job.get("telegram_id")
            if tid and tid not in pipeline_jobs:
                pipeline_jobs[tid] = job
    except Exception:
        pass

    return render_template(
        "dasha/projects.html",
        projects=all_projects,
        summary=summary,
        state_labels=dba.STATE_LABELS,
        state_colors=dba.STATE_COLORS,
        valid_states=dba.VALID_STATES,
        book_versions=book_versions,
        pipeline_jobs=pipeline_jobs,
    )


@bp.route("/projects/<int:telegram_id>/book-versions")
@role_required("dev", "dasha", "lena")
def project_book_versions(telegram_id: int):
    try:
        versions = dba.get_book_versions(telegram_id)
        return jsonify({"versions": [
            {
                "version": v["version"],
                "pdf_filename": v.get("pdf_filename", ""),
                "created_at": v["created_at"].strftime("%d.%m.%Y %H:%M") if v.get("created_at") else "",
            }
            for v in versions
        ]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


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


# ── Авто-тесты бота ──────────────────────────────────────────────

def _parse_json_report(report: dict, raw: str, duration_s: float) -> dict:
    """Разбирает pytest-json-report в структурированный результат."""
    results = []
    for test in report.get("tests", []):
        test_id = test.get("nodeid", "")
        short = test_id.split("::")[-1] if "::" in test_id else test_id
        outcome = test.get("outcome", "")
        status = "passed" if outcome == "passed" else "failed"
        # Traceback из longrepr
        tb = ""
        if outcome != "passed":
            for phase in ("setup", "call", "teardown"):
                ph = test.get(phase) or {}
                longrepr = ph.get("longrepr") or ""
                if longrepr:
                    tb = longrepr
                    break
        results.append({"id": test_id, "name": short, "status": status, "traceback": tb})

    passed = sum(1 for r in results if r["status"] == "passed")
    failed = sum(1 for r in results if r["status"] == "failed")
    dur = report.get("duration") or duration_s
    summary = report.get("summary") or {}
    summary_str = (
        f"{summary.get('passed', passed)} passed"
        + (f", {summary.get('failed', failed)} failed" if failed else "")
        + f" in {round(dur, 2)}s"
    )
    return {
        "results": results,
        "passed": passed,
        "failed": failed,
        "total": len(results),
        "duration_s": round(dur, 2),
        "summary": summary_str,
        "raw": raw,
    }


@bp.route("/bot_tests")
@role_required("dev", "dasha")
def bot_tests():
    """Панель авто-тестов бота."""
    history = dba.get_test_runs(limit=10)
    return render_template("dasha/bot_tests.html", history=history)


@bp.route("/bot_tests/run", methods=["POST"])
@role_required("dev", "dasha")
def bot_tests_run():
    """Запуск pytest, сохранение результата в БД, возврат JSON."""
    project_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..")
    )
    only_v2 = request.json.get("only_v2", False) if request.is_json else False
    test_path = "tests/test_bot_flows_v2.py" if only_v2 else "tests/"

    # Всегда используем явный путь к python из venv
    python_exe = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        ".venv", "bin", "python"
    )
    if not os.path.exists(python_exe):
        python_exe = sys.executable  # fallback

    import logging as _log
    _log.getLogger(__name__).info("bot_tests_run: python=%s cwd=%s path=%s", python_exe, project_root, test_path)

    # Временный JSON-файл для отчёта
    import tempfile as _tmp
    json_report_file = _tmp.mktemp(suffix=".json")

    t_start = time.time()
    raw = ""
    report_data = {}
    try:
        proc = subprocess.run(
            [python_exe, "-m", "pytest", test_path,
             "--json-report", f"--json-report-file={json_report_file}",
             "--tb=short", "--no-header", "--color=no", "-q"],
            capture_output=True,
            text=True,
            cwd=project_root,
            timeout=120,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "NO_COLOR": "1", "TERM": "dumb"},
        )
        raw = proc.stdout + proc.stderr
        _log.getLogger(__name__).info("bot_tests_run: rc=%d stdout_len=%d", proc.returncode, len(raw))
        if os.path.exists(json_report_file):
            with open(json_report_file, encoding="utf-8") as fj:
                report_data = json.load(fj)
            os.unlink(json_report_file)
    except subprocess.TimeoutExpired:
        raw = "TIMEOUT: тесты не завершились за 120 секунд"
    except Exception as e:
        raw = f"ERROR: {e}"
        _log.getLogger(__name__).error("bot_tests_run exception: %s", e)

    duration_s = time.time() - t_start

    if report_data:
        parsed = _parse_json_report(report_data, raw, duration_s)
    else:
        # Fallback: возвращаем raw как есть с понятной ошибкой
        parsed = {
            "results": [],
            "passed": 0,
            "failed": 0,
            "total": 0,
            "duration_s": round(duration_s, 2),
            "summary": "Ошибка запуска тестов — смотрите Raw лог",
            "raw": raw or "Нет вывода от pytest",
        }

    # Сохраняем в БД
    try:
        run_id = dba.save_test_run(
            results=parsed["results"],
            passed=parsed["passed"],
            failed=parsed["failed"],
            duration_s=parsed["duration_s"],
            summary=parsed["summary"],
        )
        parsed["run_id"] = run_id
    except Exception as e:
        parsed["run_id"] = None
        parsed["db_error"] = str(e)

    return jsonify(parsed)


@bp.route("/bot_tests/debug")
@role_required("dev", "dasha")
def bot_tests_debug():
    """Отладка: запускает pytest и возвращает сырой вывод + детали окружения."""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    python_venv = os.path.join(project_root, ".venv", "bin", "python")
    python_exe = python_venv if os.path.exists(python_venv) else sys.executable
    try:
        proc = subprocess.run(
            [python_exe, "-m", "pytest", "tests/test_bot_flows_v2.py", "-v", "--tb=short", "--no-header"],
            capture_output=True, text=True, cwd=project_root, timeout=60,
        )
        return jsonify({
            "python_exe": python_exe,
            "project_root": project_root,
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "stdout_lines": len(proc.stdout.splitlines()),
        })
    except Exception as e:
        return jsonify({"error": str(e), "python_exe": python_exe})


@bp.route("/bot_tests/run/<int:run_id>")
@role_required("dev", "dasha")
def bot_tests_run_detail(run_id: int):
    """Детали конкретного запуска (JSON)."""
    run = dba.get_test_run(run_id)
    if not run:
        return jsonify({"error": "not found"}), 404
    results = run.get("results") or []
    if isinstance(results, str):
        results = json.loads(results)
    return jsonify({**dict(run), "results": results})
