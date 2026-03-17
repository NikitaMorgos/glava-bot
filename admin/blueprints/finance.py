"""
Blueprint «Финансы» — учёт расходов и P&L.
Доступен всем авторизованным ролям: dev, dasha, lena.
"""
from decimal import Decimal, InvalidOperation

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from admin import db_finance as dbf

bp = Blueprint("finance", __name__, url_prefix="/finance")

ALL_ROLES = {"dev", "dasha", "lena"}


def _require_auth():
    """Возвращает None если всё ок, иначе redirect."""
    if session.get("role") not in ALL_ROLES:
        return redirect(url_for("login"))
    return None


# ── Расходы ────────────────────────────────────────────────────────

@bp.route("/")
def index():
    guard = _require_auth()
    if guard:
        return guard
    return redirect(url_for("finance.expenses"))


@bp.route("/expenses")
def expenses():
    guard = _require_auth()
    if guard:
        return guard

    month = request.args.get("month", "")
    rows = dbf.get_expenses(month or None)
    categories = dbf.get_categories()
    initiators = dbf.get_initiators()
    total = sum(r["amount"] for r in rows)

    return render_template(
        "finance/expenses.html",
        rows=rows,
        categories=categories,
        initiators=initiators,
        total=total,
        selected_month=month,
    )


@bp.route("/expenses/add", methods=["POST"])
def expense_add():
    guard = _require_auth()
    if guard:
        return guard

    date = request.form.get("date", "").strip()
    amount_str = request.form.get("amount", "").strip().replace(",", ".")
    category_id = request.form.get("category_id", "")
    initiator_id = request.form.get("initiator_id", "")
    periodicity = request.form.get("periodicity", "разовая")
    behavior = request.form.get("behavior", "переменная")
    title = request.form.get("title", "").strip()
    comment = request.form.get("comment", "").strip()

    try:
        amount = Decimal(amount_str)
        if amount <= 0:
            raise ValueError
    except (InvalidOperation, ValueError):
        flash("Некорректная сумма", "error")
        return redirect(url_for("finance.expenses"))

    if not date or not category_id or not initiator_id:
        flash("Заполните все обязательные поля", "error")
        return redirect(url_for("finance.expenses"))

    dbf.add_expense(date, amount, int(category_id), int(initiator_id),
                    periodicity, behavior, title, comment, session.get("username", ""))
    flash("Расход добавлен", "success")
    month = date[:7]
    return redirect(url_for("finance.expenses", month=month))


@bp.route("/expenses/<int:expense_id>/edit", methods=["GET", "POST"])
def expense_edit(expense_id: int):
    guard = _require_auth()
    if guard:
        return guard

    expense = dbf.get_expense(expense_id)
    if not expense:
        flash("Расход не найден", "error")
        return redirect(url_for("finance.expenses"))

    if request.method == "POST":
        date = request.form.get("date", "").strip()
        amount_str = request.form.get("amount", "").strip().replace(",", ".")
        category_id = request.form.get("category_id", "")
        initiator_id = request.form.get("initiator_id", "")
        periodicity = request.form.get("periodicity", "разовая")
        behavior = request.form.get("behavior", "переменная")
        title = request.form.get("title", "").strip()
        comment = request.form.get("comment", "").strip()

        try:
            amount = Decimal(amount_str)
            if amount <= 0:
                raise ValueError
        except (InvalidOperation, ValueError):
            flash("Некорректная сумма", "error")
            return redirect(url_for("finance.expense_edit", expense_id=expense_id))

        dbf.update_expense(expense_id, date, amount,
                           int(category_id), int(initiator_id),
                           periodicity, behavior, title, comment)
        flash("Расход обновлён", "success")
        month = date[:7]
        return redirect(url_for("finance.expenses", month=month))

    return render_template(
        "finance/expense_edit.html",
        expense=expense,
        categories=dbf.get_categories(),
        initiators=dbf.get_initiators(),
    )


@bp.route("/expenses/<int:expense_id>/delete", methods=["POST"])
def expense_delete(expense_id: int):
    guard = _require_auth()
    if guard:
        return guard
    dbf.delete_expense(expense_id)
    flash("Расход удалён", "success")
    return redirect(url_for("finance.expenses"))


# ── Категории (AJAX-подобные POST) ────────────────────────────────

@bp.route("/categories/add", methods=["POST"])
def category_add():
    guard = _require_auth()
    if guard:
        return guard
    name = request.form.get("name", "").strip()
    if name:
        dbf.add_category(name)
        flash(f"Категория «{name}» добавлена", "success")
    return redirect(url_for("finance.expenses"))


@bp.route("/categories/<int:cat_id>/delete", methods=["POST"])
def category_delete(cat_id: int):
    guard = _require_auth()
    if guard:
        return guard
    ok = dbf.delete_category(cat_id)
    if ok:
        flash("Категория удалена", "success")
    else:
        flash("Нельзя удалить: есть расходы в этой категории", "error")
    return redirect(url_for("finance.expenses"))


# ── Инициаторы ─────────────────────────────────────────────────────

@bp.route("/initiators/add", methods=["POST"])
def initiator_add():
    guard = _require_auth()
    if guard:
        return guard
    name = request.form.get("name", "").strip()
    if name:
        dbf.add_initiator(name)
        flash(f"Инициатор «{name}» добавлен", "success")
    return redirect(url_for("finance.expenses"))


@bp.route("/initiators/<int:init_id>/delete", methods=["POST"])
def initiator_delete(init_id: int):
    guard = _require_auth()
    if guard:
        return guard
    ok = dbf.delete_initiator(init_id)
    if ok:
        flash("Инициатор удалён", "success")
    else:
        flash("Нельзя удалить: есть расходы от этого инициатора", "error")
    return redirect(url_for("finance.expenses"))


# ── P&L ────────────────────────────────────────────────────────────

@bp.route("/pnl")
def pnl():
    guard = _require_auth()
    if guard:
        return guard
    months = int(request.args.get("months", 6))
    data = dbf.get_pnl(months)
    return render_template("finance/pnl.html", data=data, months=months)
