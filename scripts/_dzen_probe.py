"""Проверка: загружаются ли cookies и работают ли они на dzen.ru с сервера."""
import json, time
from pathlib import Path
from playwright.sync_api import sync_playwright

SESSION = Path("/opt/glava/cookies/dzen_session.json")
print(f"Session file: {SESSION} exists={SESSION.exists()} size={SESSION.stat().st_size}")

# Покажем что в cookies
data = json.loads(SESSION.read_text())
cookies = data.get("cookies", [])
print(f"Total cookies: {len(cookies)}")
for c in cookies:
    print(f"  {c['domain']} | {c['name']} | expires={c.get('expires', 'session')}")

print("\n--- Test Playwright ---")
with sync_playwright() as p:
    br = p.chromium.launch(headless=True)
    ctx = br.new_context(
        storage_state=str(SESSION),
        viewport={"width": 1280, "height": 900},
        user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    )
    # Проверяем, что cookies загружены
    loaded_cookies = ctx.cookies(["https://dzen.ru", "https://yandex.ru"])
    print(f"Loaded cookies for dzen/yandex: {len(loaded_cookies)}")
    for c in loaded_cookies:
        print(f"  {c['domain']} {c['name']}")

    pg = ctx.new_page()
    pg.goto("https://dzen.ru", wait_until="domcontentloaded", timeout=30_000)
    time.sleep(3)
    print(f"\nURL after navigation: {pg.url}")
    # Ищем признаки залогиненности
    page_text = pg.inner_text("body")
    if "Войти" in page_text and "Выйти" not in page_text and "Настройки" not in page_text:
        print("STATUS: NOT LOGGED IN")
    else:
        print("STATUS: POSSIBLY LOGGED IN")
    pg.screenshot(path="/tmp/dzen_check.png")
    br.close()
print("done")
