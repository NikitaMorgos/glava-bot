"""
Личный кабинет Glava — веб-интерфейс для пользователей бота.
Вход по логину (@username или telegram_id) и паролю.
"""
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Загрузка .env (config при импорте db)
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from flask import Flask, jsonify, redirect, render_template, request, session, url_for

import db
import storage

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.jinja_env.auto_reload = True
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
        return redirect(url_for("projects_list"))
    return redirect(url_for("auth"))


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

# Каждый блок: (title, subtitle, [questions])
INTERVIEW_QUESTIONS = [
    ("🏠 Бытовой портрет",
     "Как выглядел этот человек, как жил каждый день, что было вокруг него.",
     [
         "Какие ежедневные ритуалы и привычки были у этого человека? Может, всегда пил чай в определённое время, или читал перед сном, или обходил огород с утра? Что повторялось изо дня в день?",
         "Что в доме было отражением этого человека? Не просто вещи — а то, что про него. Коллекция, порядок на полках, вечный бардак в мастерской, иконка в углу, магнитики на холодильнике?",
         "Любил ли готовить? Если да — какие блюда получались лучше всего? Если нет — что больше всего любил из еды, напитков? Было ли что-то, от чего никогда не отказывался?",
         "Как выглядел? Как одевался — аккуратно, небрежно, всегда одинаково? Была ли фирменная деталь — шляпа, часы, фартук, причёска? Как выглядели руки?",
         "Были ли привычки или странности, которые все замечали? Может, всегда проверял замок дважды, или стучал по столу, или разговаривал сам с собой, или насвистывал?",
     ]),
    ("📖 Биография — нить жизни",
     "Не даты, а путь: откуда пришёл, через что прошёл, куда привела жизнь.",
     [
         "Расскажите, откуда родом. Какая была семья? Как жили — бедно, средне, хорошо?",
         "Каким было детство? Какие воспоминания рассказывал? Было счастливым — или пришлось рано повзрослеть?",
         "Чем занимался по жизни? Как оказался на этой работе — случайно или шёл к ней? Нравилось ли?",
         "Рассматривал ли другие профессии? Мечтал ли о чём-то другом? Жалел ли, что не попробовал?",
         "Был ли рабочий момент, которым особенно гордился? Проект, достижение, случай на работе, который запомнился?",
         "Как учился? Любил ли школу? Какие предметы нравились? Как выбирал, куда поступать? Подрабатывал ли во время учёбы? Чем занимался помимо уроков?",
         "Как встретил свою половину? Как рассказывали эту историю в семье?",
         "Были ли дети? Как менялся с их появлением? Каким был родителем — строгим, мягким, отстранённым, вовлечённым?",
         "Менялось ли место жизни? Переезжал? Скучал ли по тому, что оставил?",
         "Был ли момент, после которого жизнь стала другой? Что произошло и как справился?",
     ]),
    ("💪 Характер, убеждения, увлечения",
     "Что за человек он был — изнутри. Как думал, во что верил, чем горел.",
     [
         "Как проявлялся характер в обычной жизни? Был терпеливым или вспыльчивым? Мягким или жёстким? Как это видели окружающие?",
         "Было ли чувство юмора? Шутил ли? Какие шутки любил? Умел ли смеяться над собой?",
         "Какие были жизненные принципы? Было ли что-то, чего никогда бы не сделал? Или наоборот — что считал обязательным?",
         "Как относился к вере, религии? Верил ли — в Бога, в судьбу, в человека? Менялось ли это с годами?",
         "Были ли политические убеждения? Интересовался ли тем, что происходит в стране? Спорил ли на эти темы?",
         "Что умел делать лучше всех? Мастерил, чинил, рисовал, пел, считал в уме? Был ли талант, который не все знали?",
         "Чем занимался в свободное время? Было ли увлечение для души — рыбалка, сад, книги, музыка, спорт?",
         "Как относился к деньгам? Экономил, тратил легко, откладывал на чёрный день?",
     ]),
    ("❤️ Отношения с людьми",
     "Как строил связи — с самыми близкими и с окружающими.",
     [
         "Как ладил со своими родителями? Были ли близкие отношения или дистанция? Менялось ли это с годами?",
         "Какие были отношения с супругом? Как распределялись роли? Кто был главным? Как решали конфликты?",
         "Каким был с друзьями? Много ли их было? Или один-два, но на всю жизнь? Как поддерживал дружбу?",
         "Как вёл себя с незнакомыми? Открыто, настороженно, с юмором? Легко сходился с людьми?",
         "Кто был самым близким человеком? С кем мог поговорить о чём угодно? А с кем отношения были сложными?",
     ]),
    ("📖 Семейные истории",
     "То, что передаётся из поколения в поколение.",
     [
         "Расскажите историю, которую в семье пересказывают снова и снова — смешную, странную или трогательную.",
         "Был ли случай, когда все удивились? Сделал то, чего никто не ожидал?",
         "Есть ли семейные реликвии или памятные вещи? Фотография, письмо, награда, посуда, инструмент — что-то, что хранят и передают?",
     ]),
    ("🌍 Жизнь и перемены",
     "Как большие события — в стране или в семье — прошли через этого человека.",
     [
         "Какое время в жизни было самым трудным? Как справлялся? Рассказывал об этом — или молчал?",
         "А какое время было самым счастливым? Когда жизнь складывалась так, как хотелось?",
     ]),
    ("🪞 Ваш взгляд",
     "Не только про героя — про вас и ваши отношения.",
     [
         "Чему вас научил этот человек — не словами, а своим примером?",
         "Какие привычки или установки вы переняли от него? Может, фразу, подход к делу, отношение к чему-то?",
         "Что бы вы хотели сказать ему, если бы была возможность — одну фразу?",
     ]),
]

# Советы рассказчику — показываются в конце списка вопросов
INTERVIEW_TIPS = [
    "Не обязательно отвечать на все вопросы — выберите 5–7, которые «зацепили»",
    "Рассказывайте как хочется, а не по порядку. Перескакивайте, возвращайтесь — это нормально",
    "Мелочи — самое ценное. «Он всегда чистил яблоко ножом по спирали» важнее, чем «он родился в 1935 году»",
    "Если расплачетесь — ничего страшного, это значит что история живая",
    "Можно рассказывать о себе — как ВЫ помните этого человека, что ВЫ чувствуете",
]


@app.route("/questions")
def questions():
    """Страница со списком вопросов для интервью."""
    if "user_id" not in session:
        return redirect(url_for("auth"))
    return render_template("questions.html", blocks=INTERVIEW_QUESTIONS, tips=INTERVIEW_TIPS)


@app.route("/questions/download")
def questions_download():
    """Скачать типовые подсказки для интервью как .txt"""
    if "user_id" not in session:
        return redirect(url_for("auth"))
    lines = ["Вопросы-подсказки для биографического интервью", "=" * 50, ""]
    for title, subtitle, qs in INTERVIEW_QUESTIONS:
        lines.append(title)
        if subtitle:
            lines.append(subtitle)
        lines.append("-" * 50)
        for q in qs:
            lines.append(f"  • {q}")
        lines.append("")
    if INTERVIEW_TIPS:
        lines.append("Подсказки для рассказчика")
        lines.append("-" * 50)
        for tip in INTERVIEW_TIPS:
            lines.append(f"  • {tip}")
        lines.append("")
    body = "\n".join(lines).encode("utf-8")
    from flask import Response
    return Response(
        body,
        mimetype="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="glava_interview_tips.txt"',
        },
    )


# ── Проекты ──────────────────────────────────────────────────────────────────

@app.route("/projects")
def projects_list():
    """Список книг (проектов) пользователя — главная страница нового кабинета."""
    if "user_id" not in session:
        return redirect(url_for("login"))
    projects = db.get_user_projects(session["user_id"])
    return render_template("projects.html", projects=projects)


@app.route("/projects/new", methods=["GET", "POST"])
def project_new():
    """Создание нового проекта: имя героя + отношение (бабушка/дедушка/...)."""
    if "user_id" not in session:
        return redirect(url_for("login"))
    error = None
    if request.method == "POST":
        hero_name = (request.form.get("hero_name") or "").strip()
        hero_relation = (request.form.get("hero_relation") or "").strip()
        if not hero_name:
            error = "Введите имя персонажа"
        else:
            project = db.create_project(
                owner_user_id=session["user_id"],
                project_type="one_person",
            )
            db.create_hero(
                project_id=project["id"],
                name=hero_name,
                relation=hero_relation or None,
                role="subject",
            )
            return redirect(url_for("project_detail", project_id=project["id"]))
    return render_template("project_new.html", error=error)


@app.route("/projects/<int:project_id>")
def project_detail(project_id: int):
    """Детали проекта: subject (о ком книга) + narrators (рассказчики) + материалы."""
    if "user_id" not in session:
        return redirect(url_for("auth"))
    project = db.get_project(project_id, session["user_id"])
    if not project:
        return redirect(url_for("projects_list"))
    heroes = db.get_project_heroes(project_id)
    subject = next((h for h in heroes if h.get("role") == "subject"), None)
    narrators = [h for h in heroes if h.get("role") != "subject"]
    voices = db.get_project_voices(project_id)
    photos = db.get_project_photos(project_id)
    for v in voices:
        v["download_url"] = storage.get_presigned_download_url(v["storage_key"])
    for p in photos:
        p["download_url"] = storage.get_presigned_download_url(p["storage_key"])
    by_hero: dict = {}
    for h in heroes:
        by_hero[h["id"]] = {"hero": h, "voices": [], "photos": []}
    by_hero[None] = {"hero": None, "voices": [], "photos": []}
    for v in voices:
        by_hero.setdefault(v["hero_id"], {"hero": None, "voices": [], "photos": []})["voices"].append(v)
    for p in photos:
        by_hero.setdefault(p["hero_id"], {"hero": None, "voices": [], "photos": []})["photos"].append(p)
    # Определяем «текущий шаг» — какая кнопка должна быть главной (CTA)
    latest_questions = db.get_latest_project_questions(project_id)
    has_questions = latest_questions is not None
    has_book = db.get_latest_project_book(project_id) is not None
    submitted = project.get("materials_submitted_at") is not None
    # Приоритет: submitted (идёт обработка) > book > questions > upload/submit
    # Это позволяет запустить Round 3+ поверх уже готовой книги:
    # publish_questions и publish_book сбрасывают submitted → клиент
    # опять видит step "questions"/"book" с возможностью догрузить материалы
    # и нажать «Пересобрать книгу» → submit → снова идём в processing.
    if submitted:
        current_step = "processing"
    elif has_book:
        current_step = "book"
    elif has_questions:
        current_step = "questions"
    elif len(voices) == 0:
        current_step = "upload"
    else:
        # Материалы есть, но клиент ещё не нажал «начать обработку»
        current_step = "ready_to_submit"
    # Read-only:
    #  - в processing — материалы в работе, правки не повлияют на текущую обработку
    #  - в book — книга собрана; можно догрузить новые материалы для пересборки
    is_editable = current_step != "processing"

    # Реальные стадии обработки (если есть)
    job_stages = []
    processing_progress = 0
    if current_step == "processing":
        job_stages = db.get_job_stages(project_id)
        if job_stages:
            done_count = sum(1 for s in job_stages if s["status"] == "done")
            running_count = sum(1 for s in job_stages if s["status"] == "running")
            total = len(job_stages)
            # 5% базовых + пропорция: done = полный шаг, running = половина шага
            processing_progress = int(5 + ((done_count + 0.5 * running_count) / total) * 90)
            processing_progress = min(95, processing_progress)
        else:
            # worker ещё не успел создать записи — показываем минимальный прогресс
            processing_progress = 3
    return render_template(
        "project.html",
        project=project,
        subject=subject,
        narrators=narrators,
        heroes=heroes,
        by_hero=by_hero,
        voice_count=len(voices),
        photo_count=len(photos),
        current_step=current_step,
        has_questions=has_questions,
        has_book=has_book,
        is_editable=is_editable,
        processing_progress=processing_progress,
        job_stages=job_stages,
        interview_question_blocks=INTERVIEW_QUESTIONS,
        interview_tips=INTERVIEW_TIPS,
        latest_questions=latest_questions,
    )


@app.route("/projects/<int:project_id>/submit-materials", methods=["POST"])
def project_submit_materials(project_id: int):
    """
    Клиент подтверждает: всё загружено, начинайте обработку.
    Запускает worker-процесс в фоне (subprocess.Popen — переживает падение Flask).
    """
    if "user_id" not in session:
        return redirect(url_for("auth"))
    if not db.submit_project_materials(project_id, session["user_id"]):
        return redirect(url_for("project_detail", project_id=project_id))

    # Запускаем worker в фоне (НЕ ждём, Flask сразу возвращает клиенту страницу)
    import subprocess
    import sys
    try:
        # Используем -m чтобы Python нашёл пакет cabinet (запуск из корня проекта)
        worker_cmd = [
            sys.executable, "-m", "cabinet.process_project",
            "--project-id", str(project_id),
        ]
        # cwd = корень репозитория (где лежит db.py, config.py)
        from pathlib import Path
        repo_root = Path(__file__).resolve().parent.parent
        subprocess.Popen(
            worker_cmd,
            cwd=str(repo_root),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            close_fds=True,
        )
        app.logger.info("Worker spawned for project %s", project_id)
    except Exception as e:
        app.logger.exception("Failed to spawn worker for project %s: %s", project_id, e)
        # Сама подтверждённая отправка не откатывается — клиент уже нажал.
        # В админке/логах поймём что worker не стартовал, перезапустим вручную.

    return redirect(url_for("project_detail", project_id=project_id))


@app.route("/projects/<int:project_id>/heroes", methods=["POST"])
def project_add_hero(project_id: int):
    """Добавить рассказчика к проекту."""
    if "user_id" not in session:
        return redirect(url_for("auth"))
    project = _check_project_writable(project_id)
    if not project:
        return redirect(url_for("project_detail", project_id=project_id))
    name = (request.form.get("name") or "").strip()
    relation = (request.form.get("relation") or "").strip()
    if name:
        db.create_hero(project_id=project_id, name=name, relation=relation or None)
    return redirect(url_for("project_detail", project_id=project_id))


@app.route("/projects/<int:project_id>/heroes/<int:hero_id>/update", methods=["POST"])
def project_update_hero(project_id: int, hero_id: int):
    """Изменить имя/отношение рассказчика."""
    if "user_id" not in session:
        return redirect(url_for("auth"))
    project = _check_project_writable(project_id)
    if not project:
        return redirect(url_for("project_detail", project_id=project_id))
    name = (request.form.get("name") or "").strip()
    relation = (request.form.get("relation") or "").strip()
    if name:
        db.update_hero(
            hero_id=hero_id,
            project_id=project_id,
            name=name,
            relation=relation or None,
        )
    return redirect(url_for("project_detail", project_id=project_id))


@app.route("/projects/<int:project_id>/heroes/<int:hero_id>/delete", methods=["POST"])
def project_delete_hero(project_id: int, hero_id: int):
    """Удалить рассказчика. Его аудио/фото остаются (hero_id обнуляется)."""
    if "user_id" not in session:
        return redirect(url_for("auth"))
    project = _check_project_writable(project_id)
    if not project:
        return redirect(url_for("project_detail", project_id=project_id))
    db.delete_hero(hero_id=hero_id, project_id=project_id)
    return redirect(url_for("project_detail", project_id=project_id))


# ── Загрузка интервью и фото в проект ─────────────────────────────────────────

import tempfile
from pathlib import Path as _Path

PROJECT_AUDIO_EXT = {".ogg", ".mp3", ".m4a", ".wav", ".opus", ".oga"}
PROJECT_TEXT_EXT = {".txt", ".docx", ".doc", ".pdf", ".rtf", ".md"}
PROJECT_INTERVIEW_EXT = PROJECT_AUDIO_EXT | PROJECT_TEXT_EXT
PROJECT_PHOTO_EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}
PROJECT_DOC_EXT = {".jpg", ".jpeg", ".png", ".webp", ".pdf"}
PROJECT_MAX_AUDIO_SIZE = 500 * 1024 * 1024  # 500 МБ
PROJECT_MAX_PHOTO_SIZE = 20 * 1024 * 1024   # 20 МБ


def _check_project_access(project_id: int):
    """Возвращает (project, heroes) если доступ есть, иначе (None, None)."""
    if "user_id" not in session:
        return None, None
    project = db.get_project(project_id, session["user_id"])
    if not project:
        return None, None
    heroes = db.get_project_heroes(project_id)
    return project, heroes


def _check_project_writable(project_id: int) -> dict | None:
    """
    Возвращает project если доступ есть И проект «открыт для правок».
    Закрыт когда:
    - клиент уже нажал «начать обработку» (materials_submitted_at IS NOT NULL), ИЛИ
    - уже есть готовая книга (повторно не пересобираем).
    """
    if "user_id" not in session:
        return None
    project = db.get_project(project_id, session["user_id"])
    if not project:
        return None
    if project.get("materials_submitted_at") is not None:
        return None
    if db.get_latest_project_book(project_id) is not None:
        return None
    return project


@app.route("/projects/<int:project_id>/upload", methods=["GET"])
def project_upload_page(project_id: int):
    """Страница загрузки интервью и фото для проекта.
    Зоны upload — только для narrators (рассказчиков), subject в них не показывается.
    """
    if "user_id" not in session:
        return redirect(url_for("auth"))
    project, heroes = _check_project_access(project_id)
    if project is None:
        return redirect(url_for("projects_list"))
    narrators = [h for h in heroes if h.get("role") != "subject"]
    return render_template(
        "project_upload.html",
        project=project,
        heroes=narrators,
    )


def _resolve_hero_id(project_id: int, raw_hero_id: str | None, heroes: list) -> int | None:
    """Парсит hero_id из формы, проверяет что он действительно в этом проекте."""
    if not raw_hero_id:
        return None
    try:
        hero_id = int(raw_hero_id)
    except (TypeError, ValueError):
        return None
    valid_ids = {h["id"] for h in heroes}
    return hero_id if hero_id in valid_ids else None


@app.route("/projects/<int:project_id>/upload/voice", methods=["POST"])
def project_upload_voice(project_id: int):
    """Приём аудио-файла интервью с привязкой к проекту и (опц.) рассказчику."""
    if "user_id" not in session:
        return jsonify({"ok": False, "error": "Не авторизован"}), 401
    project, heroes = _check_project_access(project_id)
    if project is None:
        return jsonify({"ok": False, "error": "Проект не найден"}), 404
    if project.get("materials_submitted_at") is not None:
        return jsonify({"ok": False, "error": "Материалы уже переданы в работу"}), 403

    if "file" not in request.files:
        return jsonify({"ok": False, "error": "Файл не получен"}), 400
    f = request.files["file"]
    if not f.filename:
        return jsonify({"ok": False, "error": "Пустое имя файла"}), 400

    ext = _Path(f.filename).suffix.lower()
    if ext not in PROJECT_INTERVIEW_EXT:
        return jsonify({
            "ok": False,
            "error": f"Формат {ext} не поддерживается. Аудио: " + ", ".join(sorted(PROJECT_AUDIO_EXT))
                     + ". Текст: " + ", ".join(sorted(PROJECT_TEXT_EXT)),
        }), 400

    hero_id = _resolve_hero_id(project_id, request.form.get("hero_id"), heroes)

    try:
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp_path = tmp.name
            f.save(tmp_path)
        try:
            file_size = os.path.getsize(tmp_path)
            if file_size > PROJECT_MAX_AUDIO_SIZE:
                return jsonify({"ok": False, "error": "Файл больше 500 МБ"}), 400
            storage_key = storage.upload_file(tmp_path, session["user_id"])
            voice = db.save_voice_for_project(
                user_id=session["user_id"],
                project_id=project_id,
                hero_id=hero_id,
                storage_key=storage_key,
                original_filename=f.filename,
            )
        finally:
            _Path(tmp_path).unlink(missing_ok=True)
        app.logger.info(
            "Project upload voice: user=%s project=%s hero=%s file=%s size=%s",
            session["user_id"], project_id, hero_id, f.filename, file_size,
        )
        return jsonify({
            "ok": True,
            "voice_id": voice["id"],
            "filename": f.filename,
            "size": file_size,
        })
    except Exception as e:
        app.logger.exception("project_upload_voice failed: %s", e)
        return jsonify({"ok": False, "error": "Ошибка загрузки"}), 500


@app.route("/projects/<int:project_id>/questions/download", methods=["GET"])
def project_questions_download(project_id: int):
    """Отдаёт вопросы как .txt файл для скачивания."""
    if "user_id" not in session:
        return redirect(url_for("auth"))
    project, _ = _check_project_access(project_id)
    if not project:
        return redirect(url_for("projects_list"))
    latest = db.get_latest_project_questions(project_id)
    if not latest:
        return redirect(url_for("project_questions", project_id=project_id))
    # Формируем текстовый файл
    lines = ["Вопросы для следующего интервью", "=" * 50, ""]
    for block in latest.get("blocks_json") or []:
        lines.append(block.get("title", "") or "")
        lines.append("-" * 50)
        for q in block.get("questions") or []:
            lines.append(f"  • {q}")
        lines.append("")
    blitz = latest.get("blitz_json") or []
    if blitz:
        lines.append("Блиц-вопросы")
        lines.append("-" * 50)
        for q in blitz:
            lines.append(f"  • {q}")
        lines.append("")
    body = "\n".join(lines).encode("utf-8")
    from flask import Response
    return Response(
        body,
        mimetype="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="questions_project_{project_id}_v{latest["version"]}.txt"',
        },
    )


@app.route("/projects/<int:project_id>/questions", methods=["GET"])
def project_questions(project_id: int):
    """Доп. вопросы по проекту (после первой обработки материалов)."""
    if "user_id" not in session:
        return redirect(url_for("auth"))
    project, heroes = _check_project_access(project_id)
    if project is None:
        return redirect(url_for("projects_list"))
    latest = db.get_latest_project_questions(project_id)
    if not latest:
        # Вопросов ещё нет — нечего показывать, отправляем в проект
        return redirect(url_for("project_detail", project_id=project_id))
    return render_template(
        "project_questions.html",
        project=project,
        heroes=heroes,
        first_hero=heroes[0] if heroes else None,
        latest=latest,
    )


@app.route("/projects/<int:project_id>/book", methods=["GET"])
def project_book(project_id: int):
    """
    Страница книги: HTML inline (если есть исходник) или PDF embed (fallback).
    Если книги ещё нет — редирект на страницу проекта (там клиент видит текущую фазу).
    """
    if "user_id" not in session:
        return redirect(url_for("auth"))
    project, heroes = _check_project_access(project_id)
    if project is None:
        return redirect(url_for("projects_list"))
    books = db.get_project_books(project_id)
    if not books:
        return redirect(url_for("project_detail", project_id=project_id))
    latest = books[0]
    html_url = None
    pdf_url = None
    if latest:
        pdf_url = storage.get_presigned_download_url(latest["storage_key"], expires_in=3600)
        if latest.get("html_storage_key"):
            html_url = storage.get_presigned_download_url(latest["html_storage_key"], expires_in=3600)
    return render_template(
        "project_book.html",
        project=project,
        heroes=heroes,
        first_hero=heroes[0] if heroes else None,
        books=books,
        latest=latest,
        html_url=html_url,
        pdf_url=pdf_url,
    )


@app.route("/projects/<int:project_id>/book/edit", methods=["GET"])
def project_book_edit(project_id: int):
    """
    Блочный редактор книги. Читает blocks_json из БД (структура из pipeline glava).
    С ?preview=<v> — показывает выбранную версию в read-only (без сохранения),
    в топбаре — баннер «Просмотр vN» с возможностью вернуться или восстановить.
    """
    if "user_id" not in session:
        return redirect(url_for("auth"))
    project, _ = _check_project_access(project_id)
    if project is None:
        return redirect(url_for("projects_list"))

    latest = db.get_latest_project_book(project_id)
    if not latest:
        return redirect(url_for("project_detail", project_id=project_id))

    preview_version = request.args.get("preview", type=int)
    is_preview = False
    preview_row = None
    if preview_version is not None and preview_version != latest["version"]:
        preview_row = db.get_project_book_version(project_id, preview_version)
        if preview_row and preview_row.get("blocks_json"):
            is_preview = True
        else:
            # Некорректная версия — молча уходим на актуальный редактор
            return redirect(url_for("project_book_edit", project_id=project_id))

    source = preview_row if is_preview else latest
    blocks_json = source.get("blocks_json")
    if not blocks_json and not is_preview:
        return render_template(
            "project_book_edit.html",
            project=project, latest=latest, book=None,
            is_preview=False, preview_version=None,
        )
    return render_template(
        "project_book_edit.html",
        project=project,
        latest=latest,
        book=blocks_json,
        is_preview=is_preview,
        preview_version=preview_version if is_preview else None,
    )


def _apply_photo_rotations(project_id: int, blocks_json: dict) -> None:
    """
    Проходит по всем photo_album блокам, для photos[i] с rotation в {90,180,270}
    скачивает файл из S3, поворачивает через Pillow, заливает обратно тем же
    ключом (перезаписывает оригинал). Сбрасывает rotation в 0 после успеха.
    Используется в /book/save перед render-pdf, чтобы pipeline получил уже
    правильно ориентированное изображение.
    """
    if not isinstance(blocks_json, dict):
        return
    # Строим map filename → storage_key через таблицу photos
    photos_by_file = {}
    for p in db.get_project_photos(project_id):
        key = p.get("storage_key")
        ext = os.path.splitext(key or "")[1] or ".jpg"
        photos_by_file[f"photo_{p['id']}{ext}"] = key
    try:
        from PIL import Image  # type: ignore
    except ImportError:
        app.logger.warning("Pillow не установлен — поворот фото пропущен")
        return
    import tempfile as _tf, os as _os
    rotated_count = 0
    for ch in blocks_json.get("chapters", []) or []:
        for bl in ch.get("blocks", []) or []:
            if bl.get("type") != "photo_album":
                continue
            for photo in bl.get("photos", []) or []:
                if not isinstance(photo, dict):
                    continue
                rot = photo.get("rotation") or 0
                try:
                    rot = int(rot) % 360
                except (TypeError, ValueError):
                    rot = 0
                if rot == 0:
                    photo.pop("rotation", None)
                    continue
                fname = photo.get("file")
                skey = photos_by_file.get(fname)
                if not skey:
                    app.logger.warning("rotate: не нашли storage_key для %s", fname)
                    photo["rotation"] = 0
                    continue
                # Скачиваем → крутим → заливаем обратно
                suffix = _os.path.splitext(skey)[1] or ".jpg"
                with _tf.NamedTemporaryFile(suffix=suffix, delete=False) as ftmp:
                    tmp_path = ftmp.name
                try:
                    storage.download_file(skey, tmp_path)
                    with Image.open(tmp_path) as img:
                        # expand=True — размер холста подстраивается под новую ориентацию
                        img.rotate(-rot, expand=True).save(tmp_path)
                    storage.upload_file_to_key(tmp_path, skey)
                    photo["rotation"] = 0
                    rotated_count += 1
                    # Инвалидируем локальный кэш файла в workspace, чтобы
                    # _prepare_workspace скачал уже повёрнутый вариант заново.
                    ws_local = f"/tmp/glava-jobs/project-{project_id}/input/{fname}"
                    try:
                        if _os.path.exists(ws_local):
                            _os.unlink(ws_local)
                    except Exception:
                        pass
                    app.logger.info("photo %s повёрнуто на %d°", fname, rot)
                except Exception as e:
                    app.logger.warning("не удалось повернуть %s: %s", fname, e)
                finally:
                    try: _os.unlink(tmp_path)
                    except Exception: pass
    if rotated_count:
        app.logger.info("apply_photo_rotations: %d фото повёрнуто", rotated_count)


@app.route("/projects/<int:project_id>/book/save", methods=["POST"])
def project_book_save(project_id: int):
    """
    Принимает обновлённый blocks_json (структуру после правок в редакторе),
    регенерит PDF из него (playwright → A5), заливает PDF+HTML в S3 под
    новым ключом и сохраняет запись версии.

    Если render PDF упал (playwright недоступен и т.п.) — сохраняем версию
    структуры со старым PDF и предупреждаем клиента: правки в БД, но скачивание
    остаётся на прошлой сборке.
    """
    if "user_id" not in session:
        return jsonify({"ok": False, "error": "Не авторизован"}), 401
    project, _ = _check_project_access(project_id)
    if project is None:
        return jsonify({"ok": False, "error": "Проект не найден"}), 404

    payload = request.get_json(silent=True) or {}
    blocks_json = payload.get("blocks_json")
    if not isinstance(blocks_json, dict) or "chapters" not in blocks_json:
        return jsonify({"ok": False, "error": "Некорректная структура (нужен dict с chapters)"}), 400
    notes = (payload.get("notes") or "").strip() or "правки клиента"

    prev = db.get_latest_project_book(project_id)
    if not prev:
        return jsonify({"ok": False, "error": "Нет исходной версии книги"}), 400

    # Заранее знаем номер новой версии, чтобы сформировать ключи S3
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COALESCE(MAX(version), 0) + 1 FROM project_books WHERE project_id = %s",
                (project_id,),
            )
            next_version = cur.fetchone()[0]

    pdf_key = f"books/{project_id}/v{next_version}.pdf"
    html_key = f"books/{project_id}/v{next_version}.html"

    pdf_bytes: bytes | None = None
    page_count = prev.get("page_count")
    render_error: str | None = None

    # Регенерируем PDF через ОРИГИНАЛЬНЫЙ pipeline (glava render-pdf) — тот же
    # рендер, что делал первую сборку, с полным дизайном (обложка, PT Serif,
    # шаблоны glava/render/templates/). Требует workspace с фото/обложкой;
    # если workspace нет — восстанавливаем через _prepare_workspace.
    try:
        import json as _json
        import tempfile as _tf, os as _os
        from cabinet.process_project import _prepare_workspace, _run_glava

        # ---- Применяем повороты фото (rotation ∈ {90,180,270}) ----
        # Клиент в редакторе крутит превью через CSS transform и сохраняет
        # угол в blocks_json.photos[i].rotation. Здесь скачиваем каждый файл
        # с rotation != 0 из S3, поворачиваем через Pillow, заливаем обратно.
        # После этого rotation сбрасываем в 0 (файл уже правильной ориентации).
        try:
            _apply_photo_rotations(project_id, blocks_json)
        except Exception as e:
            app.logger.warning("apply_photo_rotations failed: %s", e)

        # Готовим workspace (idempotent — создаст если нет, докачает новые фото).
        workspace, _info = _prepare_workspace(project_id)
        output_dir = workspace / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Sanitize blocks_json: pydantic-модели pipeline требуют строки, не null,
        # для name/relation в relatives_table и т.п. Полностью пустые строки
        # выбрасываем (pipeline иногда сам их генерит и потом падает).
        def _sanitize(book: dict) -> dict:
            for ch in book.get("chapters", []) or []:
                new_blocks = []
                for bl in ch.get("blocks", []) or []:
                    t = bl.get("type")
                    if t in ("relatives_table", "awards_table"):
                        rows = bl.get("rows") or []
                        filtered = []
                        for r in rows:
                            if not isinstance(r, dict):
                                continue
                            # Считаем строку "пустой" если все значения None/""
                            if not any((v is not None and str(v).strip()) for v in r.values()):
                                continue
                            # null → "" для всех строковых полей
                            for k, v in list(r.items()):
                                if v is None:
                                    r[k] = ""
                            filtered.append(r)
                        bl["rows"] = filtered
                    elif t == "timeline_visual":
                        events = bl.get("events") or []
                        filtered = []
                        for e in events:
                            if not isinstance(e, dict):
                                continue
                            if not any((v is not None and str(v).strip()) for v in e.values()):
                                continue
                            for k, v in list(e.items()):
                                if v is None:
                                    e[k] = ""
                            filtered.append(e)
                        bl["events"] = filtered
                    elif t == "pull_quote":
                        if bl.get("attribution") is None:
                            bl["attribution"] = ""
                    new_blocks.append(bl)
                ch["blocks"] = new_blocks
            return book

        blocks_json_clean = _sanitize(blocks_json)

        # Пишем отредактированный book.json в workspace (перезаписываем старый).
        book_json_path = output_dir / "book.json"
        book_json_path.write_text(
            _json.dumps(blocks_json_clean, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # Если обложка требует sketch.png, а его нет (workspace очищен) —
        # регенерим через assemble-cover (использует Replicate, ~$0.01).
        needs_sketch = any(
            bl.get("type") == "cover" and bl.get("sketch_path")
            for ch in (blocks_json_clean.get("chapters") or [])
            for bl in (ch.get("blocks") or [])
        )
        sketch_file = workspace / "input" / "sketch.png"
        if needs_sketch and not sketch_file.exists():
            app.logger.info("sketch.png отсутствует — перегенерируем через assemble-cover")
            rc_c, _oc, err_c = _run_glava(["assemble-cover"], workspace)
            if rc_c != 0:
                app.logger.warning("assemble-cover упал rc=%s, продолжаем без обложки: %s",
                                   rc_c, (err_c or '')[-300:])

        # Запускаем render-pdf через pipeline
        pdf_path = output_dir / f"book_edited_v{next_version}.pdf"
        rc, _out, err = _run_glava(
            ["render-pdf",
             "--book-json", "output/book.json",
             "--output", str(pdf_path.relative_to(workspace)).replace("\\", "/")],
            workspace,
        )
        if rc != 0:
            raise RuntimeError(f"glava render-pdf rc={rc}: {err[-500:] if err else ''}")
        if not pdf_path.exists():
            raise RuntimeError(f"render-pdf прошёл, но PDF не создан: {pdf_path}")

        pdf_bytes = pdf_path.read_bytes()
        storage.upload_file_to_key(str(pdf_path), pdf_key)

        try:
            from pypdf import PdfReader  # type: ignore
            import io as _io
            page_count = len(PdfReader(_io.BytesIO(pdf_bytes)).pages)
        except Exception:
            pass
    except Exception as e:
        app.logger.exception("project_book_save: PDF regen failed: %s", e)
        render_error = str(e)

    # html_key больше не создаём (pipeline генерит только PDF), храним старый
    html_key = prev.get("html_storage_key")

    # Если PDF не срендерился — фолбэк на прошлые ключи, чтобы «скачать PDF» не сломался.
    stored_pdf_key  = pdf_key  if pdf_bytes else prev["storage_key"]
    stored_html_key = html_key if pdf_bytes else prev.get("html_storage_key")
    stored_size     = len(pdf_bytes) if pdf_bytes else prev.get("size_bytes")

    record = db.save_edited_book_version(
        project_id=project_id,
        pdf_storage_key=stored_pdf_key,
        html_storage_key=stored_html_key,
        size_bytes=stored_size,
        page_count=page_count,
        edited_by_user_id=session["user_id"],
        notes=notes,
        blocks_json=blocks_json,
    )
    resp = {"ok": True, "version": record["version"], "pdf_regenerated": pdf_bytes is not None}
    if render_error:
        resp["warning"] = f"Правки сохранены, но PDF не пересобрался: {render_error}"
    return jsonify(resp)


@app.route("/projects/<int:project_id>/book/download", methods=["GET"])
def project_book_download(project_id: int):
    """Редирект на presigned URL последней версии книги."""
    if "user_id" not in session:
        return redirect(url_for("auth"))
    project, _ = _check_project_access(project_id)
    if project is None:
        return redirect(url_for("projects_list"))
    latest = db.get_latest_project_book(project_id)
    if not latest:
        return redirect(url_for("project_detail", project_id=project_id))
    url = storage.get_presigned_download_url(latest["storage_key"], expires_in=600)
    return redirect(url)


@app.route("/projects/<int:project_id>/book/v<int:version>/download", methods=["GET"])
def project_book_version_download(project_id: int, version: int):
    """Скачивание конкретной версии."""
    if "user_id" not in session:
        return redirect(url_for("auth"))
    project, _ = _check_project_access(project_id)
    if project is None:
        return redirect(url_for("projects_list"))
    books = db.get_project_books(project_id)
    target = next((b for b in books if b["version"] == version), None)
    if not target:
        return redirect(url_for("project_book", project_id=project_id))
    url = storage.get_presigned_download_url(target["storage_key"], expires_in=600)
    return redirect(url)


@app.route("/projects/<int:project_id>/photos/upload", methods=["POST"])
def project_photos_upload(project_id: int):
    """
    Загружает одно фото в S3 и БД (photo_type='photo'). Возвращает
    {ok, id, file, url, caption} — клиент вставляет это как новый photo-item
    в photo_album главы.
    """
    if "user_id" not in session:
        return jsonify({"ok": False, "error": "Не авторизован"}), 401
    project, _ = _check_project_access(project_id)
    if project is None:
        return jsonify({"ok": False, "error": "Проект не найден"}), 404

    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"ok": False, "error": "Файл не приложен"}), 400
    # Простая проверка mime — не image/* → отказ
    mime = (f.mimetype or "").lower()
    if not mime.startswith("image/"):
        return jsonify({"ok": False, "error": f"Неподдерживаемый тип: {mime}"}), 400

    import tempfile as _tf, os as _os
    from werkzeug.utils import secure_filename as _secure
    safe = _secure(f.filename) or "upload.jpg"
    suffix = _os.path.splitext(safe)[1] or ".jpg"
    with _tf.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        f.save(tmp.name)
        tmp_path = tmp.name
    try:
        storage_key = storage.upload_file(tmp_path, session["user_id"])
    finally:
        _os.unlink(tmp_path)

    record = db.save_photo_for_project(
        user_id=session["user_id"],
        project_id=project_id,
        hero_id=None,
        storage_key=storage_key,
        caption=None,
        photo_type="photo",
        source="cabinet_editor",
    )
    pid = record["id"]
    ext = _os.path.splitext(storage_key)[1] or ".jpg"
    file_name = f"photo_{pid}{ext}"
    try:
        url = storage.get_presigned_download_url(storage_key, expires_in=3600)
    except Exception:
        url = None
    return jsonify({
        "ok": True,
        "id": pid,
        "file": file_name,
        "url": url,
        "caption": "",
    })


@app.route("/projects/<int:project_id>/photos-map", methods=["GET"])
def project_photos_map(project_id: int):
    """
    Возвращает {id: {url, caption, file}} для всех фото проекта.
    URL — presigned S3 (1 час), клиент подставляет в <img src=...> в редакторе.
    """
    if "user_id" not in session:
        return jsonify({"ok": False, "error": "Не авторизован"}), 401
    project, _ = _check_project_access(project_id)
    if project is None:
        return jsonify({"ok": False, "error": "Проект не найден"}), 404
    photos = db.get_project_photos(project_id)
    result = {}
    for p in photos:
        pid = p["id"]
        key = p.get("storage_key")
        ext = os.path.splitext(key or "")[1] or ".jpg"
        try:
            url = storage.get_presigned_download_url(key, expires_in=3600)
        except Exception as e:
            app.logger.warning("presigned url failed for photo %s: %s", pid, e)
            url = None
        result[str(pid)] = {
            "url": url,
            "caption": p.get("caption") or "",
            "file": f"photo_{pid}{ext}",
            "photo_type": p.get("photo_type"),
        }
    return jsonify({"ok": True, "photos": result})


@app.route("/projects/<int:project_id>/book/versions", methods=["GET"])
def project_book_versions(project_id: int):
    """JSON-список всех версий книги для панели истории."""
    if "user_id" not in session:
        return jsonify({"ok": False, "error": "Не авторизован"}), 401
    project, _ = _check_project_access(project_id)
    if project is None:
        return jsonify({"ok": False, "error": "Проект не найден"}), 404
    books = db.get_project_books(project_id)
    latest_version = books[0]["version"] if books else None
    items = []
    for b in books:
        # Отображаем «свежее» время: правки клиента (edited_at) или создание версии
        ts = b.get("edited_at") or b.get("created_at")
        items.append({
            "version": b["version"],
            "notes": b.get("notes") or "",
            "size_bytes": b.get("size_bytes"),
            "page_count": b.get("page_count"),
            "has_blocks_json": bool(b.get("has_blocks_json")),
            "edited_by_email": b.get("edited_by_email"),
            "timestamp": ts.isoformat() if ts else None,
            "is_current": b["version"] == latest_version,
        })
    return jsonify({"ok": True, "versions": items})


@app.route("/projects/<int:project_id>/book/versions/<int:version>/restore", methods=["POST"])
def project_book_version_restore(project_id: int, version: int):
    """
    Восстанавливает выбранную версию: копирует её blocks_json (и PDF/HTML ключи)
    в новую версию поверх текущей. После этого редактор откроет её как последнюю.
    """
    if "user_id" not in session:
        return jsonify({"ok": False, "error": "Не авторизован"}), 401
    project, _ = _check_project_access(project_id)
    if project is None:
        return jsonify({"ok": False, "error": "Проект не найден"}), 404

    src = db.get_project_book_version(project_id, version)
    if not src:
        return jsonify({"ok": False, "error": f"Версия v{version} не найдена"}), 404
    if not src.get("blocks_json"):
        return jsonify({"ok": False, "error": "У этой версии нет структуры для восстановления"}), 400

    record = db.save_edited_book_version(
        project_id=project_id,
        pdf_storage_key=src["storage_key"],
        html_storage_key=src.get("html_storage_key"),
        size_bytes=src.get("size_bytes"),
        page_count=src.get("page_count"),
        edited_by_user_id=session["user_id"],
        notes=f"восстановлено из v{version}",
        blocks_json=src["blocks_json"],
    )
    return jsonify({"ok": True, "version": record["version"]})


@app.route("/projects/<int:project_id>/voice/<int:voice_id>/delete", methods=["POST"])
def project_delete_voice(project_id: int, voice_id: int):
    """Удалить голосовое (из БД и S3). JSON-ответ для AJAX, redirect для form POST."""
    is_ajax = request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest"
    if "user_id" not in session:
        if is_ajax:
            return jsonify({"ok": False, "error": "Не авторизован"}), 401
        return redirect(url_for("auth"))
    project = _check_project_writable(project_id)
    if not project:
        if is_ajax:
            return jsonify({"ok": False, "error": "Материалы уже переданы в работу"}), 403
        return redirect(url_for("project_detail", project_id=project_id))
    rec = db.delete_voice_in_project(voice_id, project_id, session["user_id"])
    if rec:
        try:
            storage.delete_object(rec["storage_key"])
        except Exception as e:
            app.logger.warning("S3 delete failed for %s: %s", rec.get("storage_key"), e)
    if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"ok": bool(rec)})
    return redirect(url_for("project_detail", project_id=project_id))


@app.route("/projects/<int:project_id>/photo/<int:photo_id>/caption", methods=["POST"])
def project_update_photo_caption(project_id: int, photo_id: int):
    """Обновить подпись фото. Возвращает JSON для AJAX или redirect для form."""
    is_ajax = request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest"
    if "user_id" not in session:
        if is_ajax:
            return jsonify({"ok": False, "error": "Не авторизован"}), 401
        return redirect(url_for("auth"))
    project = _check_project_writable(project_id)
    if not project:
        if is_ajax:
            return jsonify({"ok": False, "error": "Материалы уже переданы в работу"}), 403
        return redirect(url_for("project_detail", project_id=project_id))
    payload = request.get_json(silent=True) if request.is_json else None
    caption = ((payload or {}).get("caption") if payload else request.form.get("caption")) or ""
    rec = db.update_photo_caption_in_project(
        photo_id=photo_id,
        project_id=project_id,
        owner_user_id=session["user_id"],
        caption=caption,
    )
    if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"ok": bool(rec), "caption": rec.get("caption") if rec else None})
    return redirect(url_for("project_detail", project_id=project_id))


@app.route("/projects/<int:project_id>/photo/<int:photo_id>/delete", methods=["POST"])
def project_delete_photo(project_id: int, photo_id: int):
    """Удалить фото (из БД и S3). JSON-ответ для AJAX, redirect для form POST."""
    is_ajax = request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest"
    if "user_id" not in session:
        if is_ajax:
            return jsonify({"ok": False, "error": "Не авторизован"}), 401
        return redirect(url_for("auth"))
    project = _check_project_writable(project_id)
    if not project:
        if is_ajax:
            return jsonify({"ok": False, "error": "Материалы уже переданы в работу"}), 403
        return redirect(url_for("project_detail", project_id=project_id))
    rec = db.delete_photo_in_project(photo_id, project_id, session["user_id"])
    if rec:
        try:
            storage.delete_object(rec["storage_key"])
        except Exception as e:
            app.logger.warning("S3 delete failed for %s: %s", rec.get("storage_key"), e)
    if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"ok": bool(rec)})
    return redirect(url_for("project_detail", project_id=project_id))


@app.route("/projects/<int:project_id>/upload/photo", methods=["POST"])
def project_upload_photo(project_id: int):
    """Приём фото (обычного или документа) с подписью и привязкой к рассказчику."""
    if "user_id" not in session:
        return jsonify({"ok": False, "error": "Не авторизован"}), 401
    project, heroes = _check_project_access(project_id)
    if project is None:
        return jsonify({"ok": False, "error": "Проект не найден"}), 404
    if project.get("materials_submitted_at") is not None:
        return jsonify({"ok": False, "error": "Материалы уже переданы в работу"}), 403

    if "file" not in request.files:
        return jsonify({"ok": False, "error": "Файл не получен"}), 400
    f = request.files["file"]
    if not f.filename:
        return jsonify({"ok": False, "error": "Пустое имя файла"}), 400

    photo_type = (request.form.get("photo_type") or "photo").strip().lower()
    if photo_type not in ("photo", "document"):
        photo_type = "photo"
    allowed = PROJECT_DOC_EXT if photo_type == "document" else PROJECT_PHOTO_EXT
    ext = _Path(f.filename).suffix.lower()
    if ext not in allowed:
        return jsonify({
            "ok": False,
            "error": f"Формат {ext} не поддерживается для {photo_type}",
        }), 400

    hero_id = _resolve_hero_id(project_id, request.form.get("hero_id"), heroes)
    caption = (request.form.get("caption") or "").strip() or None
    # Если подпись не передали — используем имя файла без расширения как авто-подпись
    if not caption:
        caption = _Path(f.filename).stem or None

    try:
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp_path = tmp.name
            f.save(tmp_path)
        try:
            file_size = os.path.getsize(tmp_path)
            if file_size > PROJECT_MAX_PHOTO_SIZE:
                return jsonify({"ok": False, "error": "Фото больше 20 МБ"}), 400
            storage_key = storage.upload_file(tmp_path, session["user_id"])
            photo = db.save_photo_for_project(
                user_id=session["user_id"],
                project_id=project_id,
                hero_id=hero_id,
                storage_key=storage_key,
                caption=caption,
                photo_type=photo_type,
            )
        finally:
            _Path(tmp_path).unlink(missing_ok=True)
        app.logger.info(
            "Project upload photo: user=%s project=%s hero=%s type=%s file=%s size=%s",
            session["user_id"], project_id, hero_id, photo_type, f.filename, file_size,
        )
        return jsonify({
            "ok": True,
            "photo_id": photo["id"],
            "filename": f.filename,
            "size": file_size,
            "caption": caption,
            "photo_type": photo_type,
        })
    except Exception as e:
        app.logger.exception("project_upload_photo failed: %s", e)
        return jsonify({"ok": False, "error": "Ошибка загрузки"}), 500


# ── Magic-link авторизация по email ──────────────────────────────────────────
import secrets
import re
from cabinet.email_sender import send_magic_link as _send_magic_link

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@app.route("/auth", methods=["GET"])
def auth():
    """Главная страница входа: форма для email или ссылка на telegram-login."""
    if "user_id" in session:
        return redirect(url_for("projects_list"))
    return render_template("auth.html", stage="form")


@app.route("/auth/request", methods=["POST"])
def auth_request():
    """
    Принимает email, создаёт пользователя если нет, генерирует токен,
    отправляет ссылку. Всегда показывает «письмо отправлено» (anti-enumeration).
    """
    if "user_id" in session:
        return redirect(url_for("projects_list"))
    email = (request.form.get("email") or "").strip().lower()
    if not EMAIL_RE.match(email):
        return render_template("auth.html", stage="form",
                               error="Введите корректный email")
    # Создаём пользователя если ещё нет
    user = db.get_user_by_email(email)
    purpose = "login"
    if not user:
        user = db.create_user_with_email(email)
        purpose = "signup"
    # Генерируем токен (32 байта → 43 символа base64url)
    token = secrets.token_urlsafe(32)
    db.create_magic_link_token(
        user_id=user["id"],
        token=token,
        purpose=purpose,
        ttl_minutes=30,
        requested_ip=request.remote_addr,
    )
    link = url_for("auth_consume", token=token, _external=True)
    _send_magic_link(to_email=email, link=link)
    return render_template("auth.html", stage="sent", email=email)


@app.route("/auth/<token>", methods=["GET"])
def auth_consume(token: str):
    """Клик из письма — валидация токена, открытие сессии."""
    if "user_id" in session:
        return redirect(url_for("projects_list"))
    consumed = db.consume_magic_link_token(token)
    if not consumed:
        return render_template("auth.html", stage="expired"), 410
    user_id = consumed["user_id"]
    # Подтянем email/telegram для сессии
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, telegram_id, email FROM users WHERE id = %s",
                (user_id,),
            )
            row = cur.fetchone()
    if not row:
        return render_template("auth.html", stage="expired"), 410
    # Помечаем email подтверждённым (первый успешный клик)
    db.mark_user_email_verified(user_id)
    session["user_id"] = row[0]
    session["telegram_id"] = row[1]  # может быть None для web-only
    session["email"] = row[2]
    return redirect(url_for("projects_list"))


from cabinet.tma_api import tma_api
app.register_blueprint(tma_api)

from cabinet.upload_api import upload_api
app.register_blueprint(upload_api)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
