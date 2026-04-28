"""
Диагностика страницы Яндекс Дзен — находит кнопку создания статьи.
Запускать на сервере:
  cd /opt/glava && python scripts/_dzen_debug.py

Сохраняет скриншот /tmp/smm_images/dzen_debug_publications.png
и выводит все кнопки/ссылки на странице публикаций.
"""
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SESSION_FILE = Path(os.environ.get("SMM_DZEN_SESSION", "")) or (
    Path(__file__).resolve().parent.parent / "cookies" / "dzen_session.json"
)
PUBLICATIONS_URL = "https://dzen.ru/profile/editor/glava_family/publications"
OUT_DIR = Path("/tmp/smm_images")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def main():
    from playwright.sync_api import sync_playwright

    print(f"Сессия: {SESSION_FILE} (exists={SESSION_FILE.exists()})")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            storage_state=str(SESSION_FILE) if SESSION_FILE.exists() else None,
            viewport={"width": 1280, "height": 900},
        )
        page = ctx.new_page()

        # ── Страница публикаций ───────────────────────────────────────
        print(f"\nОткрываю: {PUBLICATIONS_URL}")
        page.goto(PUBLICATIONS_URL, wait_until="domcontentloaded", timeout=30_000)
        time.sleep(3)

        scr = OUT_DIR / "dzen_debug_publications.png"
        page.screenshot(path=str(scr), full_page=True)
        print(f"Скриншот: {scr}")
        print(f"URL после загрузки: {page.url}")

        # ── Все кнопки ────────────────────────────────────────────────
        print("\n=== Кнопки (button) ===")
        for btn in page.locator("button").all()[:30]:
            try:
                txt = btn.inner_text().strip()[:80]
                if txt:
                    print(f"  BUTTON: {txt!r}")
            except Exception:
                pass

        # ── Все ссылки с href ─────────────────────────────────────────
        print("\n=== Ссылки (a[href]) ===")
        for link in page.locator("a[href]").all()[:40]:
            try:
                txt  = link.inner_text().strip()[:60]
                href = link.get_attribute("href") or ""
                if txt or "editor" in href or "new" in href or "creat" in href:
                    print(f"  A: {txt!r} → {href}")
            except Exception:
                pass

        browser.close()
        print("\nГотово.")


if __name__ == "__main__":
    main()
