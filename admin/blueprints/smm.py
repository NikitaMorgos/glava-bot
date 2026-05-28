"""SMM редакция v2 — /smm/."""
import logging
import re
import threading
from pathlib import Path

from flask import (
    Blueprint, abort, flash, jsonify, redirect,
    render_template, request, send_file, session, url_for,
)

from admin import db_admin as dba
from admin.auth import role_required
from smm import db_smm

logger = logging.getLogger(__name__)

bp = Blueprint("smm", __name__, url_prefix="/smm")

# Служебные роли (без журналиста — он теперь отдельная сущность)
SMM_ROLES = [
    ("smm_strategy",     "Стратегия"),
    ("smm_scout",        "SMM Скаут"),
    ("smm_editor",       "Редактор"),
    ("smm_illustrator",  "Иллюстратор"),
]

_jobs: dict[str, str] = {}

STATUS_LABELS = {
    "draft":               "Черновик",
    "generating":          "Генерируется",
    "journalist_done":     "Текст готов (черновик)",
    "journalist_revised":  "Текст исправлен",
    "editor_rejected":     "Отклонён редактором",
    "ready":               "Готов к одобрению",
    "approved":            "Одобрен",
    "publishing":          "Публикуется",
    "published":           "Опубликован",
    "error":               "Ошибка",
    "deleted":             "Удалён",
}

STATUS_COLORS = {
    "draft":               "gray",
    "generating":          "yellow",
    "journalist_done":     "blue",
    "journalist_revised":  "sky",
    "editor_rejected":     "red",
    "ready":               "indigo",
    "approved":            "green",
    "publishing":          "yellow",
    "published":           "emerald",
    "error":               "red",
    "deleted":             "gray",
}


def _slug(text: str) -> str:
    t = text.lower().strip()
    t = re.sub(r"[^\w\s-]", "", t)
    t = re.sub(r"[\s_-]+", "_", t)
    return t[:40] or "item"


# ── Главная — доска постов ─────────────────────────────────────────────────────

@bp.route("/")
@role_required("dev", "lena", "dasha")
def index():
    pname_filter = request.args.get("platform") or None
    posts = db_smm.get_all_posts(100, platform_name_filter=pname_filter)
    plans = db_smm.get_latest_plans(10)
    platform_names = db_smm.get_unique_platform_names()
    platform_formats = db_smm.get_active_platform_formats()

    board: dict[str, list] = {
        "draft":           [],
        "generating":      [],
        "journalist_done": [],
        "editor_rejected": [],
        "ready":           [],
        "approved":        [],
        "publishing":      [],
        "published":       [],
        "error":           [],
    }
    for p in posts:
        bucket = board.get(p["status"], board["draft"])
        bucket.append(p)

    return render_template(
        "smm/index.html",
        board=board,
        plans=plans,
        platform_names=platform_names,
        platform_formats=platform_formats,
        active_platform=pname_filter,
        status_labels=STATUS_LABELS,
        status_colors=STATUS_COLORS,
    )


# ── Генерация контент-плана ────────────────────────────────────────────────────

@bp.route("/generate-plan", methods=["POST"])
@role_required("dev", "lena", "dasha")
def generate_plan():
    manual_ideas     = request.form.get("manual_ideas", "").strip()
    week_start       = request.form.get("week_start", "").strip() or None
    num_topics       = int(request.form.get("num_topics", 5))
    platform_name_f  = request.form.get("platform_name", "").strip() or None

    plan_id = db_smm.create_plan(week_start, manual_ideas)
    job_key = f"plan_{plan_id}"
    _jobs[job_key] = "running"

    def _run():
        try:
            from smm.scout import generate_content_plan
            generate_content_plan(
                plan_id,
                manual_ideas=manual_ideas,
                num_topics=num_topics,
                platform_name_filter=platform_name_f,
            )
            db_smm.update_plan_status(plan_id, "draft")
            _jobs[job_key] = "done"
        except Exception as e:
            logger.error("Scout ошибка план_ид=%d: %s", plan_id, e)
            db_smm.update_plan_status(plan_id, "error")
            _jobs[job_key] = f"error: {e}"

    threading.Thread(target=_run, daemon=True).start()
    label = platform_name_f or "все площадки"
    flash(f"Генерация контент-плана #{plan_id} для «{label}» запущена (~30 сек).", "success")
    return redirect(url_for("smm.index"))


# ── Пост — детальный вид ───────────────────────────────────────────────────────

@bp.route("/post/<int:post_id>")
@role_required("dev", "lena", "dasha")
def post_detail(post_id: int):
    post = db_smm.get_post(post_id)
    if not post:
        flash("Пост не найден", "error")
        return redirect(url_for("smm.index"))
    return render_template(
        "smm/post.html",
        post=post,
        job_status=_jobs.get(f"post_{post_id}", ""),
        pub_status=_jobs.get(f"publish_{post_id}", ""),
        status_labels=STATUS_LABELS,
        status_colors=STATUS_COLORS,
    )


@bp.route("/post/<int:post_id>/generate", methods=["POST"])
@role_required("dev", "lena", "dasha")
def generate_post(post_id: int):
    """Быстрая генерация: журналист → иллюстратор → редактор (без промежуточной правки)."""
    post = db_smm.get_post(post_id)
    if not post:
        flash("Пост не найден", "error")
        return redirect(url_for("smm.index"))

    db_smm.update_post(post_id, status="generating", last_error="")
    job_key = f"post_{post_id}"
    _jobs[job_key] = "running"

    def _run():
        try:
            from smm.journalist import write_article
            from smm.editor import review_and_generate_image
            write_article(post_id)
            review_and_generate_image(post_id)
            _jobs[job_key] = "done"
        except Exception as e:
            logger.error("Pipeline ошибка пост_ид=%d: %s", post_id, e)
            db_smm.update_post(post_id, status="error", last_error=str(e)[:2000])
            _jobs[job_key] = f"error: {e}"

    threading.Thread(target=_run, daemon=True).start()
    flash("Генерация статьи запущена (~60 сек).", "success")
    return redirect(url_for("smm.post_detail", post_id=post_id))


@bp.route("/post/<int:post_id>/generate-with-revision", methods=["POST"])
@role_required("dev", "lena", "dasha")
def generate_post_with_revision(post_id: int):
    """Полный pipeline: журналист → редактор 1 (фидбек) → правка → иллюстратор → редактор 2."""
    post = db_smm.get_post(post_id)
    if not post:
        flash("Пост не найден", "error")
        return redirect(url_for("smm.index"))

    db_smm.update_post(post_id, status="generating", last_error="", editor_1_feedback="")
    job_key = f"post_{post_id}"
    _jobs[job_key] = "running"

    def _run():
        try:
            from smm.journalist import write_article, revise_article
            from smm.editor import get_editorial_feedback, review_and_generate_image
            write_article(post_id)
            get_editorial_feedback(post_id)
            revise_article(post_id)
            review_and_generate_image(post_id)
            _jobs[job_key] = "done"
        except Exception as e:
            logger.error("Pipeline (с правкой) ошибка пост_ид=%d: %s", post_id, e)
            db_smm.update_post(post_id, status="error", last_error=str(e)[:2000])
            _jobs[job_key] = f"error: {e}"

    threading.Thread(target=_run, daemon=True).start()
    flash("Генерация с правкой журналиста запущена (~3 мин).", "success")
    return redirect(url_for("smm.post_detail", post_id=post_id))


@bp.route("/post/<int:post_id>/save", methods=["POST"])
@role_required("dev", "lena", "dasha")
def save_post(post_id: int):
    db_smm.update_post(
        post_id,
        topic=request.form.get("topic", "").strip(),
        article_title=request.form.get("article_title", "").strip(),
        article_body=request.form.get("article_body", "").strip(),
        image_prompt=request.form.get("image_prompt", "").strip(),
    )
    flash("Пост сохранён", "success")
    return redirect(url_for("smm.post_detail", post_id=post_id))


@bp.route("/post/<int:post_id>/approve", methods=["POST"])
@role_required("dev", "lena", "dasha")
def approve_post(post_id: int):
    db_smm.update_post(post_id, status="approved")
    flash("Пост одобрен к публикации", "success")
    return redirect(url_for("smm.post_detail", post_id=post_id))


@bp.route("/post/<int:post_id>/reject", methods=["POST"])
@role_required("dev", "lena", "dasha")
def reject_post(post_id: int):
    db_smm.update_post(post_id, status="draft")
    flash("Пост возвращён в черновик", "success")
    return redirect(url_for("smm.post_detail", post_id=post_id))


@bp.route("/post/<int:post_id>/delete", methods=["POST"])
@role_required("dev", "lena", "dasha")
def delete_post(post_id: int):
    db_smm.delete_post(post_id)
    flash("Пост удалён", "success")
    return redirect(url_for("smm.index"))


@bp.route("/post/<int:post_id>/publish-date", methods=["POST"])
@role_required("dev", "lena", "dasha")
def set_publish_date(post_id: int):
    date_str = request.form.get("publish_date", "").strip() or None
    db_smm.set_publish_date(post_id, date_str)
    flash("Дата публикации обновлена" if date_str else "Дата публикации снята", "success")
    return redirect(url_for("smm.post_detail", post_id=post_id))


@bp.route("/post/<int:post_id>/toggle-dialog", methods=["POST"])
@role_required("dev", "lena", "dasha")
def toggle_dialog(post_id: int):
    value = request.form.get("initiate_dialog") == "1"
    db_smm.set_initiate_dialog(post_id, value)
    flash("Диалог с читателем включён" if value else "Диалог с читателем выключен", "success")
    return redirect(url_for("smm.post_detail", post_id=post_id))


@bp.route("/post/<int:post_id>/regen-image", methods=["POST"])
@role_required("dev", "lena", "dasha")
def regen_image(post_id: int):
    image_prompt = request.form.get("image_prompt", "").strip()
    if image_prompt:
        db_smm.update_post(post_id, image_prompt=image_prompt)
    post = db_smm.get_post(post_id)
    final_prompt = image_prompt or (post or {}).get("image_prompt", "family memoir illustration")
    job_key = f"regen_{post_id}"
    _jobs[job_key] = "running"

    def _run():
        try:
            from smm.editor import _generate_image
            url = _generate_image(post_id, final_prompt)
            if url:
                db_smm.update_post(post_id, image_url=url)
            _jobs[job_key] = "done"
        except Exception as e:
            logger.error("Regen image ошибка пост_ид=%d: %s", post_id, e)
            db_smm.update_post(post_id, last_error=f"regen_image: {e}"[:2000])
            _jobs[job_key] = f"error: {e}"

    threading.Thread(target=_run, daemon=True).start()
    flash("Регенерация обложки запущена.", "success")
    return redirect(url_for("smm.post_detail", post_id=post_id))


@bp.route("/post/<int:post_id>/regen-image-2", methods=["POST"])
@role_required("dev", "lena", "dasha")
def regen_image_2(post_id: int):
    post = db_smm.get_post(post_id)
    if not post:
        flash("Пост не найден", "error")
        return redirect(url_for("smm.index"))
    job_key = f"regen2_{post_id}"
    _jobs[job_key] = "running"

    def _run():
        try:
            from smm.editor import _illustrator_prompts, _generate_image
            _, inline_prompt = _illustrator_prompts(post)
            if not inline_prompt:
                inline_prompt = (post.get("image_prompt") or "warm family memoir illustration, inline")
            url = _generate_image(post_id, inline_prompt, suffix="_2")
            if url:
                db_smm.update_post(post_id, image_url_2=url)
            _jobs[job_key] = "done"
        except Exception as e:
            logger.error("Regen image-2 ошибка пост_ид=%d: %s", post_id, e)
            db_smm.update_post(post_id, last_error=f"regen_image_2: {e}"[:2000])
            _jobs[job_key] = f"error: {e}"

    threading.Thread(target=_run, daemon=True).start()
    flash("Регенерация иллюстрации запущена.", "success")
    return redirect(url_for("smm.post_detail", post_id=post_id))


@bp.route("/post/<int:post_id>/publish", methods=["POST"])
@role_required("dev", "lena", "dasha")
def publish_post(post_id: int):
    post = db_smm.get_post(post_id)
    if not post:
        flash("Пост не найден", "error")
        return redirect(url_for("smm.index"))
    if post["status"] not in ("approved", "ready"):
        flash("Сначала одобрите пост", "error")
        return redirect(url_for("smm.post_detail", post_id=post_id))

    db_smm.update_post(post_id, status="publishing")
    job_key = f"publish_{post_id}"
    _jobs[job_key] = "running"

    def _run():
        try:
            from smm.publisher_dzen import publish_to_dzen
            published_url = publish_to_dzen(post)
            from datetime import datetime, timezone
            db_smm.update_post(
                post_id,
                status="published",
                published_url=published_url or "",
                published_at=datetime.now(timezone.utc),
            )
            _jobs[job_key] = "done"
        except Exception as e:
            logger.error("Publish ошибка пост_ид=%d: %s", post_id, e)
            db_smm.update_post(post_id, status="approved", last_error=f"publish: {e}"[:2000])
            _jobs[job_key] = f"error: {e}"

    threading.Thread(target=_run, daemon=True).start()
    flash("Публикация запущена (~2 мин).", "success")
    return redirect(url_for("smm.post_detail", post_id=post_id))


# ── Настройки SMM ──────────────────────────────────────────────────────────────

@bp.route("/settings")
@role_required("dev", "lena", "dasha")
def settings():
    tab = request.args.get("tab", "pformats")

    # Площадки/Форматы (v2)
    pformats = db_smm.get_all_platform_formats()

    # Рубрики
    rubrics = db_smm.get_all_rubrics()

    # Журналисты
    journalists = db_smm.get_all_journalists()

    # Собираем все нужные role-ключи и загружаем одним запросом
    pf_keys  = [f"smm_pf_{pf['slug']}"       for pf in pformats]
    rub_keys = [f"smm_rubric_{r['slug']}"     for r  in rubrics]
    j_keys   = [f"smm_journalist_{j['slug']}" for j  in journalists]
    role_keys = [r[0] for r in SMM_ROLES]

    all_keys = pf_keys + rub_keys + j_keys + role_keys
    prompts_map  = dba.get_prompts_batch(all_keys)
    # История нужна только для журналистов и служебных ролей
    histories_map = dba.get_prompt_histories_batch(j_keys + role_keys, limit=10)

    # Назначения для всех журналистов — один запрос
    j_ids = [j["id"] for j in journalists]
    all_assignments = db_smm.get_journalist_assignments_batch(j_ids) if j_ids else {}

    for pf in pformats:
        pf["prompt"] = prompts_map.get(f"smm_pf_{pf['slug']}")

    for r in rubrics:
        r["prompt"] = prompts_map.get(f"smm_rubric_{r['slug']}")

    for j in journalists:
        prompt_key = f"smm_journalist_{j['slug']}"
        j["prompt"]         = prompts_map.get(prompt_key)
        j["prompt_history"] = histories_map.get(prompt_key, [])
        j["assignments"]    = all_assignments.get(j["id"], {"rubric_ids": [], "pformat_ids": []})

    roles_data = []
    for role_key, role_name in SMM_ROLES:
        roles_data.append({
            "key":     role_key,
            "name":    role_name,
            "current": prompts_map.get(role_key),
            "history": histories_map.get(role_key, []),
        })

    return render_template(
        "smm/settings.html",
        pformats=pformats,
        rubrics=rubrics,
        journalists=journalists,
        roles_data=roles_data,
        active_tab=tab,
    )


# ── Площадки/Форматы (v2) ─────────────────────────────────────────────────────

@bp.route("/settings/pformat/save", methods=["POST"])
@role_required("dev", "lena", "dasha")
def save_pformat():
    slug          = request.form.get("slug", "").strip()
    platform_name = request.form.get("platform_name", "").strip()
    format_name   = request.form.get("format_name", "").strip()
    prompt_text   = request.form.get("prompt_text", "").strip()
    sort_order    = int(request.form.get("sort_order", 0) or 0)

    if not platform_name or not format_name:
        flash("Укажите площадку и формат", "error")
        return redirect(url_for("smm.settings", tab="pformats"))

    if not slug:
        slug = _slug(f"{platform_name}_{format_name}")

    db_smm.upsert_platform_format(slug, platform_name, format_name, sort_order)
    if prompt_text:
        dba.save_prompt(f"smm_pf_{slug}", prompt_text, session.get("username", "dev"))

    flash(f"«{platform_name} / {format_name}» сохранена", "success")
    return redirect(url_for("smm.settings", tab="pformats"))


@bp.route("/settings/pformat/<int:pf_id>/toggle", methods=["POST"])
@role_required("dev", "lena", "dasha")
def toggle_pformat(pf_id: int):
    is_active = request.form.get("is_active") == "1"
    db_smm.toggle_platform_format(pf_id, is_active)
    return redirect(url_for("smm.settings", tab="pformats"))


# ── Рубрики ────────────────────────────────────────────────────────────────────

@bp.route("/settings/rubric/save", methods=["POST"])
@role_required("dev", "lena", "dasha")
def save_rubric():
    slug        = request.form.get("slug", "").strip()
    name        = request.form.get("name", "").strip()
    prompt_text = request.form.get("prompt_text", "").strip()
    sort_order  = int(request.form.get("sort_order", 0) or 0)

    if not name:
        flash("Укажите название рубрики", "error")
        return redirect(url_for("smm.settings", tab="rubrics"))

    if not slug:
        slug = _slug(name)

    db_smm.upsert_rubric(slug, name, sort_order)
    if prompt_text:
        dba.save_prompt(f"smm_rubric_{slug}", prompt_text, session.get("username", "dev"))
    flash(f"Рубрика «{name}» сохранена", "success")
    return redirect(url_for("smm.settings", tab="rubrics"))


@bp.route("/settings/rubric/<int:rubric_id>/toggle", methods=["POST"])
@role_required("dev", "lena", "dasha")
def toggle_rubric(rubric_id: int):
    is_active = request.form.get("is_active") == "1"
    db_smm.toggle_rubric(rubric_id, is_active)
    return redirect(url_for("smm.settings", tab="rubrics"))


# ── Журналисты ─────────────────────────────────────────────────────────────────

@bp.route("/settings/journalist/save", methods=["POST"])
@role_required("dev", "lena", "dasha")
def save_journalist():
    slug        = request.form.get("slug", "").strip()
    name        = request.form.get("name", "").strip()
    prompt_text = request.form.get("prompt_text", "").strip()
    model_provider = request.form.get("model_provider", "openai").strip().lower()

    if not name:
        flash("Укажите имя журналиста", "error")
        return redirect(url_for("smm.settings", tab="journalists"))

    if not slug:
        slug = _slug(name)

    j_id = db_smm.upsert_journalist(slug, name, model_provider=model_provider)
    if prompt_text:
        dba.save_prompt(f"smm_journalist_{slug}", prompt_text, session.get("username", "dev"))

    # Назначения: рубрики
    rubric_ids = request.form.getlist("rubric_ids")
    db_smm.set_journalist_rubrics(j_id, [int(x) for x in rubric_ids if x.isdigit()])

    # Назначения: площадки/форматы
    pformat_ids = request.form.getlist("pformat_ids")
    db_smm.set_journalist_pformats(j_id, [int(x) for x in pformat_ids if x.isdigit()])

    flash(f"Журналист «{name}» сохранён", "success")
    return redirect(url_for("smm.settings", tab="journalists"))


@bp.route("/settings/journalist/<int:j_id>/toggle", methods=["POST"])
@role_required("dev", "lena", "dasha")
def toggle_journalist(j_id: int):
    is_active = request.form.get("is_active") == "1"
    db_smm.toggle_journalist(j_id, is_active)
    return redirect(url_for("smm.settings", tab="journalists"))


# ── Служебные роли — промпты ──────────────────────────────────────────────────

@bp.route("/settings/role/save", methods=["POST"])
@role_required("dev", "lena", "dasha")
def save_role_prompt():
    role = request.form.get("role", "").strip()
    text = request.form.get("prompt_text", "").strip()
    valid_roles = {r[0] for r in SMM_ROLES}
    if role not in valid_roles:
        flash("Неверная роль", "error")
        return redirect(url_for("smm.settings", tab="roles"))
    if not text:
        flash("Промпт не может быть пустым", "error")
        return redirect(url_for("smm.settings", tab="roles"))
    dba.save_prompt(role, text, session.get("username", "dev"))
    flash(f"Промпт «{dict(SMM_ROLES).get(role, role)}» сохранён", "success")
    return redirect(url_for("smm.settings", tab="roles"))


# ── Восстановление версии промта ──────────────────────────────────────────────

@bp.route("/settings/prompt/restore", methods=["POST"])
@role_required("dev", "lena", "dasha")
def restore_prompt():
    role    = request.form.get("role", "").strip()
    version = request.form.get("version", "").strip()
    tab     = request.form.get("tab", "roles")

    if not role or not version or not version.isdigit():
        flash("Неверные параметры восстановления", "error")
        return redirect(url_for("smm.settings", tab=tab))

    ok = dba.restore_prompt_version(role, int(version), session.get("username", "dev"))
    if ok:
        flash(f"Промпт «{role}» восстановлен до версии v{version}", "success")
    else:
        flash(f"Версия v{version} для «{role}» не найдена", "error")
    return redirect(url_for("smm.settings", tab=tab))


# ── Обратная совместимость ─────────────────────────────────────────────────────

@bp.route("/prompts")
@role_required("dev", "lena", "dasha")
def prompts():
    return redirect(url_for("smm.settings", tab="roles"))


@bp.route("/prompts/save", methods=["POST"])
@role_required("dev", "lena", "dasha")
def save_prompt():
    return save_role_prompt()


# ── Legacy: platform routes ───────────────────────────────────────────────────

@bp.route("/settings/platform/save", methods=["POST"])
@role_required("dev", "lena", "dasha")
def save_platform():
    slug        = request.form.get("slug", "").strip()
    name        = request.form.get("name", "").strip()
    prompt_text = request.form.get("prompt_text", "").strip()
    if not slug or not name:
        flash("Укажите slug и название", "error")
        return redirect(url_for("smm.settings", tab="pformats"))
    db_smm.upsert_platform(slug, name)
    if prompt_text:
        dba.save_prompt(f"smm_platform_{slug}", prompt_text, session.get("username", "dev"))
    flash(f"Площадка «{name}» сохранена (legacy)", "success")
    return redirect(url_for("smm.settings", tab="pformats"))


@bp.route("/settings/platform/<int:platform_id>/toggle", methods=["POST"])
@role_required("dev", "lena", "dasha")
def toggle_platform(platform_id: int):
    is_active = request.form.get("is_active") == "1"
    db_smm.toggle_platform(platform_id, is_active)
    return redirect(url_for("smm.settings", tab="pformats"))


# ── Утилиты ────────────────────────────────────────────────────────────────────

@bp.route("/image/<filename>")
@role_required("dev", "lena", "dasha")
def serve_image(filename: str):
    import os
    images_dir = Path(os.environ.get("SMM_IMAGES_DIR", "/tmp/smm_images"))
    filepath = images_dir / filename
    if not filepath.exists() or not filepath.is_file():
        abort(404)
    return send_file(str(filepath))


# ── Dzen auth UI ───────────────────────────────────────────────────────────────

@bp.route("/dzen-auth")
@role_required("dev", "lena", "dasha")
def dzen_auth():
    return render_template("smm/dzen_auth.html")


@bp.route("/dzen-auth/start", methods=["POST"])
@role_required("dev", "lena", "dasha")
def dzen_auth_start():
    from smm import dzen_auth_server
    dzen_auth_server.start()
    return jsonify({"ok": True})


@bp.route("/dzen-auth/state")
@role_required("dev", "lena", "dasha")
def dzen_auth_state():
    from smm import dzen_auth_server
    return jsonify(dzen_auth_server.get_state())


@bp.route("/dzen-auth/click", methods=["POST"])
@role_required("dev", "lena", "dasha")
def dzen_auth_click():
    data = request.json or {}
    from smm import dzen_auth_server
    dzen_auth_server.click(int(data.get("x", 0)), int(data.get("y", 0)))
    return jsonify({"ok": True})


@bp.route("/dzen-auth/type", methods=["POST"])
@role_required("dev", "lena", "dasha")
def dzen_auth_type():
    data = request.json or {}
    from smm import dzen_auth_server
    dzen_auth_server.type_text(data.get("text", ""))
    return jsonify({"ok": True})


@bp.route("/dzen-auth/key", methods=["POST"])
@role_required("dev", "lena", "dasha")
def dzen_auth_key():
    data = request.json or {}
    from smm import dzen_auth_server
    dzen_auth_server.press_key(data.get("key", "Enter"))
    return jsonify({"ok": True})


@bp.route("/dzen-auth/navigate", methods=["POST"])
@role_required("dev", "lena", "dasha")
def dzen_auth_navigate():
    data = request.json or {}
    from smm import dzen_auth_server
    dzen_auth_server.navigate(data.get("url", "https://dzen.ru"))
    return jsonify({"ok": True})


@bp.route("/dzen-auth/save", methods=["POST"])
@role_required("dev", "lena", "dasha")
def dzen_auth_save():
    from smm import dzen_auth_server
    ok = dzen_auth_server.save_session()
    state = dzen_auth_server.get_state()
    return jsonify({"ok": ok, "message": state["message"]})


# ── Контент-календарь ──────────────────────────────────────────────────────────

@bp.route("/calendar")
@role_required("dev", "lena", "dasha")
def calendar_view():
    import os
    from datetime import date, timedelta

    platform_id = request.args.get("platform_id", type=int)

    platforms = db_smm.get_all_platforms()
    rubrics   = db_smm.get_all_rubrics()

    # Показываем ±60 дней от сегодня (достаточно для редактирования)
    today    = date.today()
    date_from = today - timedelta(days=7)
    date_to   = today + timedelta(days=60)

    entries = db_smm.get_calendar_entries_with_post_status(
        date_from=date_from.isoformat(),
        date_to=date_to.isoformat(),
    )
    if platform_id:
        entries = [e for e in entries if e.get("platform_id") == platform_id]

    scout_job_key = "calendar_scout"
    import_report = session.pop("smm_calendar_import_report", None)
    return render_template(
        "smm/calendar.html",
        platforms=platforms,
        rubrics=rubrics,
        entries=entries,
        active_platform_id=platform_id,
        today=today,
        scout_status=_jobs.get(scout_job_key, ""),
        calendar_draft=_get_calendar_draft(),
        import_report=import_report,
    )


@bp.route("/calendar/entry/add", methods=["POST"])
@role_required("dev", "lena", "dasha")
def calendar_entry_add():
    platform_id   = request.form.get("platform_id", type=int)
    publish_date  = request.form.get("publish_date", "").strip()
    title         = request.form.get("title", "").strip()
    material_type = request.form.get("material_type", "").strip()
    rubric_id     = request.form.get("rubric_id", type=int) or None
    extra_info    = request.form.get("extra_info", "").strip()
    content_ready = bool(request.form.get("content_ready"))

    if not platform_id or not publish_date or not title:
        flash("Заполните площадку, дату и название", "error")
        return redirect(url_for("smm.calendar_view", platform_id=platform_id))

    db_smm.add_calendar_entry(
        platform_id=platform_id,
        publish_date=publish_date,
        title=title,
        material_type=material_type,
        rubric_id=rubric_id,
        extra_info=extra_info,
        content_ready=content_ready,
    )
    flash("Запись добавлена в календарь", "success")
    return redirect(url_for("smm.calendar_view", platform_id=platform_id))


@bp.route("/calendar/entry/<int:entry_id>/edit", methods=["POST"])
@role_required("dev", "lena", "dasha")
def calendar_entry_edit(entry_id: int):
    entry = db_smm.get_calendar_entry(entry_id)
    if not entry:
        flash("Запись не найдена", "error")
        return redirect(url_for("smm.calendar_view"))

    publish_date  = request.form.get("publish_date", "").strip()
    title         = request.form.get("title", "").strip()
    material_type = request.form.get("material_type", "").strip()
    rubric_id     = request.form.get("rubric_id", type=int) or None
    extra_info    = request.form.get("extra_info", "").strip()
    content_ready = bool(request.form.get("content_ready"))

    db_smm.update_calendar_entry(
        entry_id,
        publish_date=publish_date or None,
        title=title,
        material_type=material_type,
        rubric_id=rubric_id,
        extra_info=extra_info,
        content_ready=content_ready,
    )
    flash("Запись обновлена", "success")
    return redirect(url_for("smm.calendar_view", platform_id=entry.get("platform_id")))


@bp.route("/calendar/entry/<int:entry_id>/delete", methods=["POST"])
@role_required("dev", "lena", "dasha")
def calendar_entry_delete(entry_id: int):
    entry = db_smm.get_calendar_entry(entry_id)
    platform_id = entry.get("platform_id") if entry else None
    db_smm.delete_calendar_entry(entry_id)
    flash("Запись удалена", "success")
    return redirect(url_for("smm.calendar_view", platform_id=platform_id))


# ── Массовый импорт календаря ──────────────────────────────────────────────────

_CALENDAR_DRAFT_KEY = "smm_calendar_bulk_draft"


def _get_calendar_draft() -> str:
    row = dba.get_prompt(_CALENDAR_DRAFT_KEY)
    return row.get("prompt_text", "") if row else ""


def _save_calendar_draft(text: str) -> None:
    dba.save_prompt(_CALENDAR_DRAFT_KEY, text or "", session.get("username", "system"))


@bp.route("/calendar/draft", methods=["POST"])
@role_required("dev", "lena", "dasha")
def save_calendar_draft():
    _save_calendar_draft(request.form.get("calendar_text", ""))
    flash("Черновик сохранён", "success")
    return redirect(url_for("smm.calendar_view"))


@bp.route("/calendar/import", methods=["POST"])
@role_required("dev", "lena", "dasha")
def import_calendar():
    from smm import calendar_import as ci

    text = request.form.get("calendar_text", "")
    _save_calendar_draft(text)

    report = ci.run_import(
        text,
        get_platform_by_name=db_smm.get_platform_by_name,
        get_rubric_by_name=db_smm.get_rubric_by_name,
        get_existing_signatures=db_smm.get_existing_calendar_signatures,
        add_entry=db_smm.add_calendar_entry,
    )
    session["smm_calendar_import_report"] = report.to_dict()
    return redirect(url_for("smm.calendar_view"))


# ── Скаут по календарю ─────────────────────────────────────────────────────────

@bp.route("/scout/run", methods=["POST"])
@role_required("dev", "lena", "dasha")
def run_scout_calendar():
    """Ручной запуск ежедневного скаута по контент-календарю."""
    job_key = "calendar_scout"
    if _jobs.get(job_key) == "running":
        flash("Скаут уже запущен", "info")
        return redirect(url_for("smm.calendar_view"))

    _jobs[job_key] = "running"

    def _run():
        try:
            from smm.scout import run_calendar_scout
            result = run_calendar_scout(days_ahead=30)
            _jobs[job_key] = f"done: создано {result['created']}, пропущено {result['skipped']}"
        except Exception as e:
            logger.error("Calendar scout ошибка: %s", e)
            _jobs[job_key] = f"error: {e}"

    threading.Thread(target=_run, daemon=True).start()
    flash("Скаут запущен (30 дней)", "success")
    return redirect(url_for("smm.calendar_view"))


@bp.route("/scout/run-cron", methods=["POST"])
def run_scout_cron():
    """Endpoint для cron-задачи. Аутентификация по токену SCOUT_CRON_TOKEN."""
    import os
    token = os.environ.get("SCOUT_CRON_TOKEN", "")
    if not token or request.headers.get("X-Scout-Token") != token:
        abort(403)

    job_key = "calendar_scout"
    if _jobs.get(job_key) == "running":
        return jsonify({"status": "already_running"})

    _jobs[job_key] = "running"

    def _run():
        try:
            from smm.scout import run_calendar_scout
            result = run_calendar_scout(days_ahead=30)
            _jobs[job_key] = f"done: {result}"
        except Exception as e:
            logger.error("Cron scout ошибка: %s", e)
            _jobs[job_key] = f"error: {e}"

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"status": "started"})


@bp.route("/status/<job_key>")
@role_required("dev", "lena", "dasha")
def job_status(job_key: str):
    return jsonify({"status": _jobs.get(job_key, "unknown")})
