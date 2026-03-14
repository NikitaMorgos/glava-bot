"""Панель Лены (Marketer) — /lena/."""
import os
from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from admin.auth import role_required
from admin import db_admin as dba

bp = Blueprint("lena", __name__, url_prefix="/lena")

SEGMENTS = [
    ("all",         "Все пользователи"),
    ("paid",        "Оплатили заказ"),
    ("book_ready",  "Книга готова"),
    ("inactive_7",  "Неактивны 7+ дней"),
    ("inactive_30", "Неактивны 30+ дней"),
    ("no_payment",  "Не оплатили"),
]


@bp.route("/")
@role_required("dev", "lena")
def index():
    return redirect(url_for("lena.users"))


# ── Пользователи ─────────────────────────────────────────────────
@bp.route("/users")
@role_required("dev", "lena")
def users():
    segment = request.args.get("segment", "all")
    rows = dba.get_users_by_segment(segment)
    return render_template("lena/users.html", users=rows,
                           segments=SEGMENTS, current_segment=segment)


# ── Рассылки ─────────────────────────────────────────────────────
@bp.route("/mailings")
@role_required("dev", "lena")
def mailings():
    rows = dba.get_mailings()
    return render_template("lena/mailings.html", mailings=rows)


@bp.route("/mailings/new", methods=["GET", "POST"])
@role_required("dev", "lena")
def mailing_new():
    if request.method == "POST":
        name    = request.form.get("name", "").strip()
        text    = request.form.get("template_text", "").strip()
        segment = request.form.get("segment", "all")
        author  = session.get("username", "lena")

        if not text:
            flash("Текст рассылки не может быть пустым", "error")
            return render_template("lena/mailing_new.html", segments=SEGMENTS)

        mailing_id = dba.create_mailing(name, text, segment, author)

        if request.form.get("send_now"):
            _send_mailing(mailing_id, text, segment)
            flash(f"Рассылка «{name}» запущена", "success")
        else:
            flash(f"Рассылка «{name}» сохранена (черновик)", "success")

        return redirect(url_for("lena.mailings"))

    return render_template("lena/mailing_new.html", segments=SEGMENTS)


def _send_mailing(mailing_id: int, text: str, segment: str):
    """Отправляет сообщения пользователям через Telegram Bot API в фоне."""
    import threading
    import requests as req

    bot_token = os.environ.get("BOT_TOKEN", "")
    recipients = dba.get_users_by_segment(segment)

    def send():
        sent, errors = 0, 0
        for user in recipients:
            tid = user.get("telegram_id")
            if not tid:
                continue
            try:
                r = req.post(
                    f"https://api.telegram.org/bot{bot_token}/sendMessage",
                    json={"chat_id": tid, "text": text, "parse_mode": "HTML"},
                    timeout=10,
                )
                if r.status_code == 200:
                    dba.mark_recipient_sent(mailing_id, tid)
                    sent += 1
                else:
                    dba.mark_recipient_error(mailing_id, tid, r.text[:200])
                    errors += 1
            except Exception as e:
                dba.mark_recipient_error(mailing_id, tid, str(e))
                errors += 1
        dba.finish_mailing(mailing_id, sent)

    threading.Thread(target=send, daemon=True).start()


# ── Триггеры ─────────────────────────────────────────────────────
@bp.route("/triggers")
@role_required("dev", "lena")
def triggers():
    rows = dba.get_triggers()
    return render_template("lena/triggers.html", triggers=rows)


@bp.route("/triggers/<int:trigger_id>/toggle", methods=["POST"])
@role_required("dev", "lena")
def trigger_toggle(trigger_id: int):
    dba.toggle_trigger(trigger_id)
    flash("Триггер обновлён", "success")
    return redirect(url_for("lena.triggers"))
