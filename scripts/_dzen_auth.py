#!/usr/bin/env python3
"""
Сохранение сессии Яндекс Дзен для автопубликатора SMM.

Использование:
    python scripts/_dzen_auth.py

Что делает:
    1. Открывает браузер Chromium (НЕ headless — нужна ручная авторизация)
    2. Переходит на passport.yandex.ru/auth
    3. Ждёт, пока пользователь войдёт в аккаунт
    4. Сохраняет cookies + localStorage в cookies/dzen_session.json
    5. Проверяет, что авторизация прошла (открывает профиль канала)

После запуска publisher_dzen.py будет использовать сохранённый файл сессии
автоматически (SMM_DZEN_SESSION=cookies/dzen_session.json или дефолтный путь).

Требования:
    pip install playwright
    playwright install chromium
"""
import os
import sys
import time
from pathlib import Path

# Добавляем корень проекта в sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

_AUTH_URL = "https://passport.yandex.ru/auth"
_DZEN_CHANNEL_URL = "https://dzen.ru/profile/editor/publications"
_DZEN_CHECK_URL = "https://dzen.ru"

_DEFAULT_SESSION_DIR = Path(__file__).resolve().parent.parent / "cookies"
_DEFAULT_SESSION_FILE = _DEFAULT_SESSION_DIR / "dzen_session.json"


def main() -> None:
    session_file = Path(
        os.environ.get("SMM_DZEN_SESSION", "") or _DEFAULT_SESSION_FILE
    )

    print("=" * 60)
    print("  Авторизация Яндекс Дзен — GLAVA SMM")
    print("=" * 60)
    print(f"\nСессия будет сохранена в: {session_file}")
    print("\nШаги:")
    print("  1. Откроется браузер Chromium")
    print("  2. Войдите в аккаунт Яндекса вручную")
    print("  3. После успешного входа нажмите Enter здесь\n")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ОШИБКА: playwright не установлен.")
        print("Выполните: pip install playwright && playwright install chromium")
        sys.exit(1)

    session_file.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=200)
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        page = ctx.new_page()

        print(f"Открываем: {_AUTH_URL}")
        page.goto(_AUTH_URL, wait_until="domcontentloaded", timeout=30_000)

        print("\nВойдите в аккаунт Яндекса в открывшемся браузере.")
        print("Когда авторизация завершится, нажмите Enter здесь...")
        input()

        # Проверяем, что залогинились
        page.goto(_DZEN_CHECK_URL, wait_until="domcontentloaded", timeout=30_000)
        time.sleep(3)

        current_url = page.url
        if "passport.yandex" in current_url or "login" in current_url.lower():
            print("\nОШИБКА: Авторизация не завершена. Попробуйте ещё раз.")
            browser.close()
            sys.exit(1)

        print(f"\nАвторизация подтверждена (URL: {current_url})")

        # Проверяем доступ к редакторскому профилю
        print(f"Проверяем доступ к каналу: {_DZEN_CHANNEL_URL}")
        page.goto(_DZEN_CHANNEL_URL, wait_until="domcontentloaded", timeout=30_000)
        time.sleep(2)

        editor_url = page.url
        if "login" in editor_url.lower() or "passport" in editor_url:
            print("\nПРЕДУПРЕЖДЕНИЕ: Нет доступа к редакторскому каналу Дзен.")
            print("Убедитесь, что аккаунт подключён к каналу GLAVA на Дзене.")
            print("Сессия всё равно будет сохранена — попробуйте вручную.")
        else:
            print(f"Редакторский профиль доступен (URL: {editor_url})")

        # Сохраняем сессию
        ctx.storage_state(path=str(session_file))
        browser.close()

    print(f"\n✓ Сессия сохранена: {session_file}")
    print("  Теперь publisher_dzen.py сможет публиковать статьи автоматически.")
    print("\nДля проверки запустите:")
    print("  python scripts/_dzen_auth.py --check")


def check_session() -> None:
    """Проверяет существующую сессию без открытия браузера для входа."""
    session_file = Path(
        os.environ.get("SMM_DZEN_SESSION", "") or _DEFAULT_SESSION_FILE
    )

    if not session_file.exists():
        print(f"ОШИБКА: Файл сессии не найден: {session_file}")
        print("Запустите: python scripts/_dzen_auth.py")
        sys.exit(1)

    print(f"Проверяем сессию: {session_file}")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ОШИБКА: playwright не установлен.")
        sys.exit(1)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            storage_state=str(session_file),
            viewport={"width": 1280, "height": 900},
        )
        page = ctx.new_page()
        page.goto(_DZEN_CHANNEL_URL, wait_until="domcontentloaded", timeout=30_000)
        time.sleep(3)

        url = page.url
        browser.close()

    if "passport.yandex" in url or "login" in url.lower():
        print(f"ОШИБКА: Сессия устарела (редирект на: {url})")
        print("Перезапустите авторизацию: python scripts/_dzen_auth.py")
        sys.exit(1)
    else:
        print(f"✓ Сессия действительна (URL: {url})")


if __name__ == "__main__":
    if "--check" in sys.argv:
        check_session()
    else:
        main()
