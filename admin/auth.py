"""Декораторы авторизации для admin-панели."""
from functools import wraps
from flask import redirect, session, url_for


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "role" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def role_required(*roles):
    """Разрешает доступ только пользователям с указанными ролями."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if "role" not in session:
                return redirect(url_for("login"))
            if session["role"] not in roles:
                return redirect(url_for("login"))
            return f(*args, **kwargs)
        return decorated
    return decorator
