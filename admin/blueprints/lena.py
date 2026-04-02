"""Панель Лены (Marketer) — /lena/."""
import io
import os
from datetime import datetime
from flask import Blueprint, flash, make_response, redirect, render_template, request, session, url_for

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
@role_required("dev", "dasha", "lena")
def index():
    return redirect(url_for("lena.users"))


# ── Пользователи ─────────────────────────────────────────────────
@bp.route("/users")
@role_required("dev", "dasha", "lena")
def users():
    segment = request.args.get("segment", "all")
    rows = dba.get_users_by_segment(segment)
    return render_template("lena/users.html", users=rows,
                           segments=SEGMENTS, current_segment=segment)


# ── Рассылки ─────────────────────────────────────────────────────
@bp.route("/mailings")
@role_required("dev", "dasha", "lena")
def mailings():
    rows = dba.get_mailings()
    return render_template("lena/mailings.html", mailings=rows)


@bp.route("/mailings/new", methods=["GET", "POST"])
@role_required("dev", "dasha", "lena")
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
@role_required("dev", "dasha", "lena")
def triggers():
    rows = dba.get_triggers()
    return render_template("lena/triggers.html", triggers=rows)


@bp.route("/triggers/<int:trigger_id>/toggle", methods=["POST"])
@role_required("dev", "dasha", "lena")
def trigger_toggle(trigger_id: int):
    dba.toggle_trigger(trigger_id)
    flash("Триггер обновлён", "success")
    return redirect(url_for("lena.triggers"))


# ── Промо-коды ────────────────────────────────────────────────────────────────

@bp.route("/promo")
@role_required("dev", "dasha", "lena")
def promos():
    codes = dba.get_promo_codes()
    stats = dba.get_promo_stats()
    return render_template("lena/promos.html", codes=codes, stats=stats)


@bp.route("/promo/new", methods=["GET", "POST"])
@role_required("dev", "dasha", "lena")
def promo_new():
    if request.method == "POST":
        code = request.form.get("code", "").strip().upper()
        discount_type = request.form.get("discount_type", "percent")
        discount_value = request.form.get("discount_value", "0")
        promo_type = request.form.get("promo_type", "general")
        max_uses_raw = request.form.get("max_uses", "").strip()
        expires_at_raw = request.form.get("expires_at", "").strip()
        author = session.get("username", "lena")

        # Валидация
        errors = []
        if not code:
            errors.append("Код не может быть пустым.")
        try:
            discount_value = float(discount_value)
            if discount_value <= 0:
                errors.append("Скидка должна быть больше нуля.")
        except ValueError:
            errors.append("Неверное значение скидки.")

        max_uses = None
        if max_uses_raw:
            try:
                max_uses = int(max_uses_raw)
                if max_uses < 1:
                    errors.append("Лимит использований должен быть >= 1.")
            except ValueError:
                errors.append("Лимит использований должен быть числом.")

        expires_at = None
        if expires_at_raw:
            try:
                expires_at = datetime.strptime(expires_at_raw, "%Y-%m-%dT%H:%M")
            except ValueError:
                errors.append("Неверный формат даты.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("lena/promo_new.html")

        try:
            dba.create_promo_code(
                code=code,
                discount_type=discount_type,
                discount_value=discount_value,
                promo_type=promo_type,
                max_uses=max_uses,
                expires_at=expires_at,
                created_by=author,
            )
            flash(f"Промо-код «{code}» создан", "success")
            return redirect(url_for("lena.promos"))
        except Exception as e:
            if "unique" in str(e).lower():
                flash(f"Код «{code}» уже существует. Придумайте другой.", "error")
            else:
                flash(f"Ошибка: {e}", "error")
            return render_template("lena/promo_new.html")

    return render_template("lena/promo_new.html")


@bp.route("/promo/<int:promo_id>/deactivate", methods=["POST"])
@role_required("dev", "dasha", "lena")
def promo_deactivate(promo_id: int):
    dba.deactivate_promo_code(promo_id)
    flash("Промо-код деактивирован", "success")
    return redirect(url_for("lena.promos"))


@bp.route("/promo/<int:promo_id>/activate", methods=["POST"])
@role_required("dev", "dasha", "lena")
def promo_activate(promo_id: int):
    dba.activate_promo_code(promo_id)
    flash("Промо-код активирован", "success")
    return redirect(url_for("lena.promos"))


@bp.route("/promo/<int:promo_id>/usages")
@role_required("dev", "dasha", "lena")
def promo_usages(promo_id: int):
    code = dba.get_promo_code(promo_id)
    if not code:
        flash("Промо-код не найден", "error")
        return redirect(url_for("lena.promos"))
    usages = dba.get_promo_usages(promo_id)
    return render_template("lena/promo_usages.html", code=code, usages=usages)


@bp.route("/promo/export.csv")
@role_required("dev", "dasha", "lena")
def promo_export():
    csv_data = dba.export_promo_codes_csv()
    response = make_response(csv_data)
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = "attachment; filename=promo_codes.csv"
    return response
