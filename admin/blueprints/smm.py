"""SMM редакция — /smm/."""
import logging
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
    ("smm_strategy", "Стратегия"),
    ("smm_scout",    "SMM Скаут"),
    ("smm_journalist", "Журналист"),
    ("smm_editor",   "Редактор"),
]

# Лёгкий in-memory трекер фоновых задач {job_key: "running"|"done"|"error: ..."}
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


# ── Главная — доска постов ─────────────────────────────────────────────────────

@bp.route("/")
@role_required("dev", "lena", "dasha")
def index():
    posts = db_smm.get_all_posts(100)
    plans = db_smm.get_latest_plans(10)

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
        status_labels=STATUS_LABELS,
        status_colors=STATUS_COLORS,
    )


# ── Генерация контент-плана ────────────────────────────────────────────────────

@bp.route("/generate-plan", methods=["POST"])
@role_required("dev", "lena", "dasha")
def generate_plan():
    manual_ideas = request.form.get("manual_ideas", "").strip()
    week_start = request.form.get("week_start", "").strip() or None
    num_topics = int(request.form.get("num_topics", 5))

    plan_id = db_smm.create_plan(week_start, manual_ideas)
    job_key = f"plan_{plan_id}"
    _jobs[job_key] = "running"

    def _run():
        try:
            from smm.scout import generate_content_plan
            generate_content_plan(plan_id, manual_ideas, num_topics)
            db_smm.update_plan_status(plan_id, "draft")
            _jobs[job_key] = "done"
        except Exception as e:
            logger.error("Scout ошибка план_ид=%d: %s", plan_id, e)
            db_smm.update_plan_status(plan_id, "error")
            _jobs[job_key] = f"error: {e}"

    threading.Thread(target=_run, daemon=True).start()
    flash(f"Генерация контент-плана #{plan_id} запущена. Обновите страницу через ~30 секунд.", "success")
    return redirect(url_for("smm.index"))


# ── Пост — детальный вид ───────────────────────────────────────────────────────

@bp.route("/post/<int:post_id>")
@role_required("dev", "lena", "dasha")
def post_detail(post_id: int):
    post = db_smm.get_post(post_id)
    if not post:
        flash("Пост не найден", "error")
        return redirect(url_for("smm.index"))
    job_status = _jobs.get(f"post_{post_id}", "")
    pub_status = _jobs.get(f"publish_{post_id}", "")
    return render_template(
        "smm/post.html",
        post=post,
        job_status=job_status,
        pub_status=pub_status,
        status_labels=STATUS_LABELS,
        status_colors=STATUS_COLORS,
    )


@bp.route("/post/<int:post_id>/generate", methods=["POST"])
@role_required("dev", "lena", "dasha")
def generate_post(post_id: int):
    """Запустить полный пайплайн: Journalist → Editor → Replicate."""
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
    flash("Генерация статьи запущена. Обновите страницу через ~60 секунд.", "success")
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
    flash("Публикация в Яндекс Дзен запущена. Обновите страницу через ~2 минуты.", "success")
    return redirect(url_for("smm.post_detail", post_id=post_id))


# ── Промпты ролей ──────────────────────────────────────────────────────────────

@bp.route("/prompts")
@role_required("dev", "lena", "dasha")
def prompts():
    roles_data = []
    for role_key, role_name in SMM_ROLES:
        current = dba.get_prompt(role_key)
        history = dba.get_prompt_history(role_key, 5)
        roles_data.append({
            "key": role_key,
            "name": role_name,
            "current": current,
            "history": history,
        })
    return render_template("smm/prompts.html", roles_data=roles_data)


@bp.route("/prompts/save", methods=["POST"])
@role_required("dev", "lena", "dasha")
def save_prompt():
    role = request.form.get("role", "").strip()
    text = request.form.get("prompt_text", "").strip()
    valid_roles = {r[0] for r in SMM_ROLES}
    if role not in valid_roles:
        flash("Неверная роль", "error")
        return redirect(url_for("smm.prompts"))
    if not text:
        flash("Промпт не может быть пустым", "error")
        return redirect(url_for("smm.prompts"))
    author = session.get("username", "dev")
    dba.save_prompt(role, text, author)
    flash(f"Промпт «{dict(SMM_ROLES).get(role, role)}» сохранён", "success")
    return redirect(url_for("smm.prompts"))


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
