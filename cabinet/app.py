"""
Личный кабинет Glava — веб-интерфейс для пользователей бота.
Вход по логину (@username или telegram_id) и паролю.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Загрузка .env (config при импорте db)
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from flask import Flask, redirect, render_template, request, session, url_for

import db
import storage

app = Flask(__name__)
app.secret_key = os.environ.get("CABINET_SECRET_KEY", "glava-cabinet-dev-change-in-prod")
# Для работы за nginx (HTTPS)
app.config["PREFERRED_URL_SCHEME"] = "https"
if os.environ.get("TRUST_PROXY", "").lower() in ("1", "true", "yes"):
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)


def verify_password(user: dict, password: str) -> bool:
    """Проверяет пароль пользователя (bcrypt, совместимо с ботом)."""
    import bcrypt

    h = user.get("web_password_hash")
    if not h:
        return False
    try:
        return bcrypt.checkpw(
            password.encode("utf-8", errors="replace")[:72],
            h.encode("ascii") if isinstance(h, str) else h,
        )
    except Exception:
        return False


def get_user_by_login(login: str) -> dict | None:
    """Находит пользователя по @username (без @) или telegram_id."""
    login = (login or "").strip().lower().lstrip("@")
    if not login:
        return None
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, telegram_id, username, web_password_hash
                FROM users
                WHERE LOWER(REPLACE(COALESCE(username,''), '@', '')) = %s
                   OR CAST(telegram_id AS TEXT) = %s
                LIMIT 1
                """,
                (login, login),
            )
            row = cur.fetchone()
    if not row:
        return None
    return {
        "id": row[0],
        "telegram_id": row[1],
        "username": row[2] or "",
        "web_password_hash": row[3],
    }


@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    error = None
    if request.method == "POST":
        login_val = request.form.get("login", "").strip()
        password = request.form.get("password", "")
        if not login_val or not password:
            error = "Введите логин и пароль"
        else:
            user = get_user_by_login(login_val)
            if not user:
                error = "Пользователь не найден"
            elif not user.get("web_password_hash"):
                error = "Пароль не настроен. Напиши /cabinet в боте @glava_voice_bot"
            elif not verify_password(user, password):
                error = "Неверный пароль"
            else:
                session["user_id"] = user["id"]
                session["telegram_id"] = user["telegram_id"]
                return redirect(url_for("dashboard"))
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    telegram_id = session["telegram_id"]
    user, voices, photos = db.get_user_all_data(telegram_id)
    # Presigned URLs для скачивания (1 час)
    for v in voices:
        v["download_url"] = storage.get_presigned_download_url(v["storage_key"])
    for p in photos:
        p["download_url"] = storage.get_presigned_download_url(p["storage_key"])
    return render_template(
        "dashboard.html",
        user=user,
        voices=voices,
        photos=photos,
        pdf_docs=PDF_DOCUMENTS,
    )


# PDF-документы в cabinet/static/pdfs/ (добавь файлы при деплое)
PDF_DOCUMENTS = [
    {"title": "One-pager Glava", "filename": "pdfs/one-pager.pdf"},
]

INTERVIEW_QUESTIONS = [
    ("О семье и происхождении", [
        "Как звали твоих родителей полностью? Девичья фамилия мамы?",
        "Где и когда они родились? В какой семье?",
        "Были ли у них братья и сёстры? Кто старше?",
        "Чем занимались дедушка и бабушка?",
    ]),
    ("Детство", [
        "Где прошло детство? Какие самые яркие воспоминания?",
        "Как проводили время? Игры, друзья, школа.",
        "Что рассказывали родители о своей молодости?",
        "Были ли домашние животные, семейные традиции?",
    ]),
    ("Учёба и работа", [
        "Где учился? Любимые предметы, учителя?",
        "Почему выбрал именно эту профессию?",
        "Первый рабочий день — что запомнилось?",
        "Самые важные проекты или достижения?",
    ]),
    ("Любовь и семья", [
        "Как познакомились с супругой/супругом?",
        "Как делали предложение? Где и когда сыграли свадьбу?",
        "Расскажи о детях — как росли, чему радовались?",
        "Сложные моменты в семье и как их пережили?",
    ]),
    ("История страны", [
        "Что помнишь о войне (или о рассказах родителей)?",
        "Перестройка, 90-е — как жила семья?",
        "Были ли переезды, смена работы, трудные времена?",
    ]),
]


@app.route("/questions")
def questions():
    """Страница со списком вопросов для интервью."""
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("questions.html", blocks=INTERVIEW_QUESTIONS)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
