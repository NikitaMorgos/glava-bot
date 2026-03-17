"""
GLAVA Admin Panel — панели управления для Dev / Даши / Лены.
Порт: 5001. Домен: admin.glava.family.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from flask import Flask, redirect, render_template, request, session, url_for

app = Flask(__name__, template_folder="templates")
app.secret_key = os.environ.get("ADMIN_SECRET_KEY", "glava-admin-dev-change-in-prod")
app.config["JSON_AS_ASCII"] = False

if os.environ.get("TRUST_PROXY", "").lower() in ("1", "true", "yes"):
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

# ── Роли и пароли из env ──────────────────────────────────────────
USERS = {
    "dev":   {"password": os.environ.get("ADMIN_PASSWORD_DEV",   "dev123"),   "role": "dev"},
    "dasha": {"password": os.environ.get("ADMIN_PASSWORD_DASHA", "dasha123"), "role": "dasha"},
    "lena":  {"password": os.environ.get("ADMIN_PASSWORD_LENA",  "lena123"),  "role": "lena"},
}

ROLE_HOME = {
    "dev":   "/dev/",
    "dasha": "/dasha/",
    "lena":  "/lena/",
}

# ── Blueprints ────────────────────────────────────────────────────
from admin.blueprints.dev     import bp as dev_bp
from admin.blueprints.dasha   import bp as dasha_bp
from admin.blueprints.lena    import bp as lena_bp
from admin.blueprints.api     import bp as api_bp
from admin.blueprints.finance import bp as finance_bp

app.register_blueprint(dev_bp)
app.register_blueprint(dasha_bp)
app.register_blueprint(lena_bp)
app.register_blueprint(api_bp)
app.register_blueprint(finance_bp)

# ── Auth ──────────────────────────────────────────────────────────
@app.route("/")
def index():
    role = session.get("role")
    if role and role in ROLE_HOME:
        return redirect(ROLE_HOME[role])
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        user = USERS.get(username)
        if user and user["password"] == password:
            session["username"] = username
            session["role"] = user["role"]
            return redirect(ROLE_HOME[user["role"]])
        error = "Неверный логин или пароль"
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)
