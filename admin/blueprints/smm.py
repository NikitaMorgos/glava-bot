"""SMM редакция — /smm/."""
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

SMM_ROLES = [
    ("smm_strategy",     "Стратегия"),
    ("smm_scout",        "SMM Скаут"),
    ("smm_journalist",   "Журналист"),
    ("smm_editor",       "Редактор"),
    ("smm_illustrator",  "Иллюстратор"),
]

_jobs: dict[str, str] = {}

STATUS_LABELS = {
    "draft":            "Черновик",
    "generating":       "Генерируется",
    "journalist_done":  "Текст готов",
    "editor_rejected":  "Отклонён редактором",
    "ready":            "Готов к одобрению",
    "approved":         "Одобрен",
    "publishing":       "Публикуется",
    "published":        "Опубликован",
    "error":            "Ошибка",
}

STATUS_COLORS = {
    "draft":            "gray",
    "generating":       "yellow",
    "journalist_done":  "blue",
    "editor_rejected":  "red",
    "ready":            "indigo",
    "approved":         "green",
    "publishing":       "yellow",
    "published":        "emerald",
    "error":            "red",
}


def _slug(text: str) -> str:
    """Простая транслитерация / slug из произвольной строки."""
    t = text.lower().strip()
    t = re.sub(r"[^\w\s-]", "", t)
    t = re.sub(r"[\s_-]+", "_", t)
    return t[:40] or "item"


# ── Главная — доска постов ─────────────────────────────────────────────────────

@bp.route("/")
@role_required("dev", "lena", "dasha")
def index():
    platform_filter = request.args.get("platform") or None
    posts = db_smm.get_all_posts(100, platform_slug=platform_filter)
    plans = db_smm.get_latest_plans(10)
    platforms = db_smm.get_all_platforms()

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
        platforms=platforms,
        active_platform=platform_filter,
        status_labels=STATUS_LABELS,
        status_colors=STATUS_COLORS,
    )


# ── Генерация контент-плана ────────────────────────────────────────────────────

@bp.route("/generate-plan", methods=["POST"])
@role_required("dev", "lena", "dasha")
def generate_plan():
    manual_ideas  = request.form.get("manual_ideas", "").strip()
    week_start    = request.form.get("week_start", "").strip() or None
    num_topics    = int(request.form.get("num_topics", 5))
    platform_slug = request.form.get("platform_slug", "dzen").strip() or "dzen"

    plan_id = db_smm.create_plan(week_start, manual_ideas, platform_slug=platform_slug)
    job_key = f"plan_{plan_id}"
    _jobs[job_key] = "running"

    def _run():
        try:
            from smm.scout import generate_content_plan
            generate_content_plan(
                plan_id,
                manual_ideas=manual_ideas,
                num_topics=num_topics,
                platform_slug=platform_slug,
            )
            db_smm.update_plan_status(plan_id, "draft")
            _jobs[job_key] = "done"
        except Exception as e:
            logger.error("Scout ошибка план_ид=%d: %s", plan_id, e)
            db_smm.update_plan_status(plan_id, "error")
            _jobs[job_key] = f"error: {e}"

    threading.Thread(target=_run, daemon=True).start()
    flash(f"Генерация контент-плана #{plan_id} для «{platform_slug}» запущена (~30 сек).", "success")
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
    post = db_smm.get_post(post_id)
    if not post:
        flash("Пост не найден", "error")
        return redirect(url_for("smm.index"))

    db_smm.update_post(post_id, status="generating")
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
            db_smm.update_post(post_id, status="error")
            _jobs[job_key] = f"error: {e}"

    threading.Thread(target=_run, daemon=True).start()
    flash("Генерация статьи запущена (~60 сек).", "success")
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
            _jobs[job_key] = f"error: {e}"

    threading.Thread(target=_run, daemon=True).start()
    flash("Регенерация обложки запущена.", "success")
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
            db_smm.update_post(post_id, status="approved")
            _jobs[job_key] = f"error: {e}"

    threading.Thread(target=_run, daemon=True).start()
    flash("Публикация в Яндекс Дзен запущена (~2 мин).", "success")
    return redirect(url_for("smm.post_detail", post_id=post_id))


# ── Настройки SMM ──────────────────────────────────────────────────────────────

@bp.route("/settings")
@role_required("dev", "lena", "dasha")
def settings():
    tab = request.args.get("tab", "platforms")

    platforms = db_smm.get_all_platforms()
    for p in platforms:
        p["prompt"] = dba.get_prompt(f"smm_platform_{p['slug']}")

    rubrics = db_smm.get_all_rubrics()
    for r in rubrics:
        r["prompt"] = dba.get_prompt(f"smm_rubric_{r['slug']}")

    roles_data = []
    for role_key, role_name in SMM_ROLES:
        roles_data.append({
            "key":     role_key,
            "name":    role_name,
            "current": dba.get_prompt(role_key),
            "history": dba.get_prompt_history(role_key, 4),
        })

    return render_template(
        "smm/settings.html",
        platforms=platforms,
        rubrics=rubrics,
        roles_data=roles_data,
        active_tab=tab,
    )


# ── Площадки ──────────────────────────────────────────────────────────────────

@bp.route("/settings/platform/save", methods=["POST"])
@role_required("dev", "lena", "dasha")
def save_platform():
    """Создать или обновить площадку + её промпт."""
    slug        = request.form.get("slug", "").strip()
    name        = request.form.get("name", "").strip()
    prompt_text = request.form.get("prompt_text", "").strip()

    if not slug or not name:
        flash("Укажите slug и название площадки", "error")
        return redirect(url_for("smm.settings", tab="platforms"))

    db_smm.upsert_platform(slug, name)
    if prompt_text:
        dba.save_prompt(f"smm_platform_{slug}", prompt_text, session.get("username", "dev"))
    flash(f"Площадка «{name}» сохранена", "success")
    return redirect(url_for("smm.settings", tab="platforms"))


@bp.route("/settings/platform/<int:platform_id>/toggle", methods=["POST"])
@role_required("dev", "lena", "dasha")
def toggle_platform(platform_id: int):
    is_active = request.form.get("is_active") == "1"
    db_smm.toggle_platform(platform_id, is_active)
    return redirect(url_for("smm.settings", tab="platforms"))


# ── Рубрики ────────────────────────────────────────────────────────────────────

@bp.route("/settings/rubric/save", methods=["POST"])
@role_required("dev", "lena", "dasha")
def save_rubric():
    """Создать или обновить рубрику + её промпт."""
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


# ── Роли — промпты ────────────────────────────────────────────────────────────

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


# ── Обратная совместимость: старая страница /smm/prompts ──────────────────────

@bp.route("/prompts")
@role_required("dev", "lena", "dasha")
def prompts():
    return redirect(url_for("smm.settings", tab="roles"))


@bp.route("/prompts/save", methods=["POST"])
@role_required("dev", "lena", "dasha")
def save_prompt():
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
    flash(f"Промпт сохранён", "success")
    return redirect(url_for("smm.settings", tab="roles"))


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


@bp.route("/status/<job_key>")
@role_required("dev", "lena", "dasha")
def job_status(job_key: str):
    return jsonify({"status": _jobs.get(job_key, "unknown")})
