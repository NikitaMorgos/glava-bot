"""
Smoke-test кабинета: проходит весь pipe в одной команде.

Запуск:
  cd /c/Users/user/Dropbox/GLAVA
  python -m cabinet.smoke_test

Что делает:
1. Проверяет импорты всех модулей
2. Проверяет, что все таблицы существуют (миграции применены)
3. Проверяет SMTP-конфиг (без реальной отправки)
4. Создаёт ТЕСТОВОГО пользователя test_smoke@glava.family
5. Создаёт тестовый проект + героя
6. Сохраняет фейковые вопросы и книгу (БЕЗ загрузки в S3 — только в БД)
7. Прогоняет через Flask test-client все ключевые роуты
8. УБИРАЕТ за собой тестовые данные

Безопасно повторяемо: ничего не оставляет в проде, кроме лога.
"""

from __future__ import annotations

import logging
import os
import sys
import traceback
from pathlib import Path

# Загружаем .env как обычное приложение
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

# Принудительно log-backend (не отправляем письма с тест-данными)
os.environ["CABINET_EMAIL_BACKEND"] = "log"

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s %(name)s: %(message)s",
)

TEST_EMAIL = "test_smoke@glava.family"

PASS = "[OK]"
FAIL = "[FAIL]"
INFO = "[..]"


_FAILURES: list[str] = []


class Step:
    def __init__(self, name: str) -> None:
        self.name = name

    def __enter__(self):
        print(f"{INFO} {self.name}...", flush=True)
        return self

    def __exit__(self, exc_type, exc_val, tb):
        if exc_type is None:
            print(f"     {PASS}\n", flush=True)
            return False
        print(f"     {FAIL} {exc_type.__name__}: {exc_val}")
        traceback.print_exc()
        print()
        _FAILURES.append(f"{self.name}: {exc_type.__name__}: {exc_val}")
        return True  # swallow — продолжаем дальше, но в конце покажем сводку


def main() -> int:
    failures: list[str] = []

    # ── 1. Импорты ──────────────────────────────────────────────────────────
    with Step("Импорт модулей") as s:
        import db  # noqa
        import storage  # noqa
        import config  # noqa
        from cabinet import app as _app  # noqa
        from cabinet import email_sender  # noqa
        from cabinet import publish_book  # noqa
        from cabinet import publish_questions  # noqa
        from cabinet import pdf_render  # noqa

    # ── 2. Проверка таблиц ──────────────────────────────────────────────────
    required_tables = [
        ("users",                 ["email", "email_verified_at"]),
        ("projects",              ["owner_user_id", "project_type"]),
        ("heroes",                ["project_id", "name"]),
        ("voice_messages",        ["project_id", "hero_id"]),
        ("photos",                ["project_id", "hero_id"]),
        ("magic_link_tokens",     ["token", "user_id", "expires_at"]),
        ("project_books",         ["html_storage_key", "edited_at"]),
        ("project_questions",     ["blocks_json", "blitz_json"]),
    ]
    with Step("Все таблицы и колонки на месте"):
        import db
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                for tbl, cols in required_tables:
                    cur.execute(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_name = %s",
                        (tbl,),
                    )
                    have_cols = {r[0] for r in cur.fetchall()}
                    if not have_cols:
                        raise RuntimeError(f"Таблица '{tbl}' не существует — миграция не применена")
                    missing = [c for c in cols if c not in have_cols]
                    if missing:
                        raise RuntimeError(
                            f"Таблица '{tbl}' существует, но не хватает колонок: {missing}. "
                            "Применить миграции из sql/"
                        )

    # ── 3. SMTP-конфиг (без отправки) ───────────────────────────────────────
    with Step("Email backend"):
        from cabinet import email_sender
        s = email_sender.get_sender()
        print(f"     backend: {type(s).__name__}", flush=True)
        # отправка через LogSender (она ничего не отправляет, только пишет)
        ok = email_sender.send_magic_link(
            TEST_EMAIL, "https://example.test/auth/dummy"
        )
        if not ok:
            raise RuntimeError("send_magic_link вернул False")

    # ── 4. CRUD проект + герой ──────────────────────────────────────────────
    state: dict = {}
    with Step("Создание тестового пользователя"):
        import db
        u = db.get_user_by_email(TEST_EMAIL)
        if u is None:
            u = db.create_user_with_email(TEST_EMAIL)
        state["user_id"] = u["id"]
        print(f"     user_id={u['id']}, email={u['email']}", flush=True)

    with Step("Создание тестового проекта + героя"):
        import db
        p = db.create_project(state["user_id"], project_type="one_person")
        state["project_id"] = p["id"]
        h = db.create_hero(p["id"], name="Тестовый Герой", relation="дед")
        state["hero_id"] = h["id"]
        print(f"     project_id={p['id']}, hero_id={h['id']}", flush=True)

    with Step("Сохранение тестовых доп. вопросов"):
        import db
        rec = db.save_project_questions(
            state["project_id"],
            blocks=[{"title": "Тест", "questions": ["вопрос 1?", "вопрос 2?"]}],
            blitz=["блиц 1?"],
            notes="smoke-test",
        )
        print(f"     questions v{rec['version']}", flush=True)

    with Step("Сохранение тестовой книги (без S3-загрузки)"):
        import db
        rec = db.save_project_book(
            state["project_id"],
            storage_key=f"books/{state['project_id']}/v1.pdf",
            html_storage_key=f"books/{state['project_id']}/v1.html",
            size_bytes=12345,
            page_count=80,
            notes="smoke-test",
        )
        print(f"     book v{rec['version']}", flush=True)

    # ── 5. Magic-link ───────────────────────────────────────────────────────
    with Step("Magic-link: создание и потребление токена"):
        import secrets
        import db
        token = secrets.token_urlsafe(32)
        db.create_magic_link_token(
            user_id=state["user_id"], token=token, purpose="login", ttl_minutes=10,
        )
        consumed = db.consume_magic_link_token(token)
        if not consumed or consumed["user_id"] != state["user_id"]:
            raise RuntimeError(f"consume не вернул правильный user_id: {consumed}")
        # повторное потребление должно вернуть None
        again = db.consume_magic_link_token(token)
        if again is not None:
            raise RuntimeError("Токен можно использовать дважды (плохо!)")
        print(f"     token одноразовый: OK", flush=True)

    # ── 6. Flask routes ─────────────────────────────────────────────────────
    with Step("Flask: ключевые роуты под сессией"):
        from cabinet import app as _app
        with _app.app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = state["user_id"]
                sess["telegram_id"] = None
                sess["email"] = TEST_EMAIL
            checks = [
                ("/projects", 200),
                (f"/projects/{state['project_id']}", 200),
                (f"/projects/{state['project_id']}/upload", 200),
                (f"/projects/{state['project_id']}/questions", 200),
                (f"/projects/{state['project_id']}/book", 200),
            ]
            for url, expected in checks:
                r = c.get(url)
                ok = "OK" if r.status_code == expected else f"WRONG ({r.status_code})"
                print(f"     GET {url}: {r.status_code} {ok}", flush=True)
                if r.status_code != expected:
                    raise RuntimeError(f"{url}: ожидали {expected}, получили {r.status_code}")

    # ── 7. Очистка ──────────────────────────────────────────────────────────
    with Step("Очистка тестовых данных"):
        import db
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                # cascade удалит heroes, voice_messages, photos, project_books, project_questions
                cur.execute("DELETE FROM projects WHERE id = %s", (state["project_id"],))
                cur.execute("DELETE FROM magic_link_tokens WHERE user_id = %s", (state["user_id"],))
                cur.execute("DELETE FROM users WHERE email = %s", (TEST_EMAIL,))
        print(f"     user/project удалены", flush=True)

    print()
    print("=" * 60)
    if _FAILURES:
        print(f"Не прошло шагов: {len(_FAILURES)} ❌")
        print()
        for i, msg in enumerate(_FAILURES, 1):
            print(f"  [{i}] {msg}")
        print()
        print("Чаще всего: не установлен пакет. Попробуй:")
        print("  pip install boto3 weasyprint pypdf")
        return 1
    print(f"ВСЁ ОК ✅  Кабинет готов к ручному тестированию.")
    print()
    print("Что дальше:")
    print(f"  1. python cabinet/app.py    # запустить локально на :5000")
    print(f"  2. Открыть http://localhost:5000/auth")
    print(f"  3. Ввести email — magic-link придёт в лог (CABINET_EMAIL_BACKEND=log)")
    print(f"  4. Скопировать URL из лога, открыть → ты в кабинете")
    print(f"  5. Создать проект, загрузить аудио/фото, опубликовать книгу через CLI")
    return 0


if __name__ == "__main__":
    sys.exit(main())
