"""Раздел CCO (Chief Customer Officer) — /cco/."""
from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from admin.auth import role_required
from admin import db_admin as dba

bp = Blueprint("cco", __name__, url_prefix="/cco")

CCO_ROLE = "cco_agent"
CCO_ROLE_NAME = "CCO — Chief Customer Officer"


@bp.route("/")
@role_required("dev", "dasha", "lena")
def index():
    current = dba.get_prompt(CCO_ROLE)
    history = dba.get_prompt_history(CCO_ROLE)
    return render_template("cco/index.html",
                           role=CCO_ROLE,
                           role_name=CCO_ROLE_NAME,
                           current=current,
                           history=history)


@bp.route("/save", methods=["POST"])
@role_required("dev", "dasha", "lena")
def save():
    text = request.form.get("prompt_text", "").strip()
    if text:
        author = session.get("username", "dev")
        dba.save_prompt(CCO_ROLE, text, author)
        flash("Промпт CCO сохранён", "success")
    else:
        flash("Промпт не может быть пустым", "error")
    return redirect(url_for("cco.index"))
