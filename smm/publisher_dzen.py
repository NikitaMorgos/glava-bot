"""
Playwright-публикатор для Яндекс Дзен.
Использует сохранённую сессию из cookies/dzen_session.json.
"""
import logging
import os
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_DZEN_PUBLICATIONS_URL = "https://dzen.ru/profile/editor/glava_family/publications"
_SESSION_FILE = Path(os.environ.get("SMM_DZEN_SESSION", "")) or (
    Path(__file__).resolve().parent.parent / "cookies" / "dzen_session.json"
)


def publish_to_dzen(post: dict) -> Optional[str]:
    """
    Публикует статью на Яндекс Дзен через Playwright.
    Возвращает URL опубликованного материала.

    Требует:
    - установленного playwright: pip install playwright && playwright install chromium
    - сохранённой сессии: python scripts/_dzen_auth.py
    """
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    except ImportError:
        raise RuntimeError(
            "playwright не установлен. "
            "Выполните: pip install playwright && playwright install chromium"
        )

    title = (post.get("article_title") or "").strip()
    body = (post.get("article_body") or "").strip()
    image_url_path = post.get("image_url") or ""

    if not title:
        raise ValueError("Нет заголовка для публикации")
    if not body:
        raise ValueError("Нет текста статьи для публикации")

    session_file = _resolve_session_file()
    image_path = _resolve_image_path(image_url_path)

    logger.info(
        "Dzen publisher: публикуем «%s» (image=%s, session=%s)",
        title[:60], image_path, session_file,
    )

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            storage_state=str(session_file) if session_file and session_file.exists() else None,
            viewport={"width": 1280, "height": 900},
        )
        page = ctx.new_page()

        try:
            page.goto(_DZEN_PUBLICATIONS_URL, wait_until="domcontentloaded", timeout=30_000)
            time.sleep(2)

            # Check auth
            if "passport.yandex" in page.url or "login" in page.url.lower():
                browser.close()
                raise RuntimeError(
                    "Не авторизованы в Яндекс Дзен. "
                    "Запустите scripts/_dzen_auth.py для сохранения сессии."
                )

            # Click "Написать статью"
            _click_write_button(page)
            page.wait_for_load_state("domcontentloaded", timeout=20_000)
            time.sleep(2)

            # Fill title
            _fill_title(page, title)
            time.sleep(1)

            # Fill body
            _fill_body(page, body)
            time.sleep(1)

            # Upload image
            if image_path and image_path.exists():
                _upload_cover(page, image_path)

            # Publish
            _click_publish(page)
            time.sleep(4)
            page.wait_for_load_state("domcontentloaded", timeout=20_000)

            published_url = page.url
            logger.info("Dzen publisher: опубликовано, url=%s", published_url)
            browser.close()
            return published_url

        except Exception as e:
            # Save screenshot for debug
            try:
                screenshots_dir = Path(os.environ.get("SMM_IMAGES_DIR", "/tmp/smm_images"))
                screenshots_dir.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(screenshots_dir / f"dzen_error_post{post.get('id', 'unknown')}.png"))
            except Exception:
                pass
            browser.close()
            raise RuntimeError(f"Ошибка публикации в Дзен: {e}") from e


def _resolve_session_file() -> Optional[Path]:
    env_path = os.environ.get("SMM_DZEN_SESSION", "")
    if env_path:
        p = Path(env_path)
        return p if p.exists() else None
    default = Path(__file__).resolve().parent.parent / "cookies" / "dzen_session.json"
    return default if default.exists() else None


def _resolve_image_path(image_url: str) -> Optional[Path]:
    if not image_url:
        return None
    filename = image_url.split("/")[-1]
    images_dir = Path(os.environ.get("SMM_IMAGES_DIR", "/tmp/smm_images"))
    candidate = images_dir / filename
    return candidate if candidate.exists() else None


def _click_write_button(page) -> None:
    selectors = [
        "text=Написать статью",
        "text=Создать статью",
        "[data-testid='create-article']",
        "a[href*='/editor/new']",
        "button:has-text('Написать')",
    ]
    for sel in selectors:
        try:
            btn = page.locator(sel).first
            if btn.is_visible(timeout=2000):
                btn.click()
                return
        except Exception:
            pass
    raise RuntimeError("Не найдена кнопка 'Написать статью' на странице Дзена")


def _fill_title(page, title: str) -> None:
    selectors = [
        "[data-testid='title-input']",
        "input[placeholder*='заголовок' i]",
        "h1[contenteditable='true']",
        ".article-title [contenteditable='true']",
        "[placeholder*='Заголовок']",
    ]
    for sel in selectors:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=2000):
                el.click()
                el.fill(title)
                return
        except Exception:
            pass
    # Last resort: type into focused element
    page.keyboard.type(title)


def _fill_body(page, body: str) -> None:
    """Вставляет текст в редактор статьи."""
    selectors = [
        "[data-testid='editor-content'] [contenteditable='true']",
        ".editor-content [contenteditable='true']",
        ".article-body [contenteditable='true']",
        "[contenteditable='true']:not([data-testid='title-input'])",
    ]
    for sel in selectors:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=2000):
                el.click()
                # Clear and set via JS to handle rich editor
                page.evaluate(
                    """(args) => {
                        const el = document.querySelector(args.sel);
                        if (el) {
                            el.focus();
                            el.innerText = args.text;
                            el.dispatchEvent(new Event('input', {bubbles: true}));
                        }
                    }""",
                    {"sel": sel, "text": body},
                )
                return
        except Exception:
            pass
    # Fallback: click second contenteditable
    try:
        els = page.locator("[contenteditable='true']").all()
        if len(els) >= 2:
            els[1].click()
            page.evaluate(
                "document.querySelectorAll('[contenteditable=\"true\"]')[1].innerText = arguments[0]",
                body,
            )
    except Exception as e:
        logger.warning("Dzen publisher: не удалось заполнить тело статьи: %s", e)


def _upload_cover(page, image_path: Path) -> None:
    """Загружает обложку статьи."""
    try:
        upload_trigger_selectors = [
            "[data-testid='cover-upload']",
            "button:has-text('Добавить обложку')",
            "button:has-text('обложк')",
        ]
        for sel in upload_trigger_selectors:
            try:
                btn = page.locator(sel).first
                if btn.is_visible(timeout=1500):
                    with page.expect_file_chooser(timeout=5000) as fc_info:
                        btn.click()
                    fc_info.value.set_files(str(image_path))
                    time.sleep(3)
                    return
            except Exception:
                pass

        # Try direct file input
        file_input = page.locator("input[type='file']").first
        if file_input:
            file_input.set_input_files(str(image_path))
            time.sleep(2)
    except Exception as e:
        logger.warning("Dzen publisher: ошибка загрузки обложки: %s", e)


def _click_publish(page) -> None:
    selectors = [
        "[data-testid='publish-button']",
        "button:has-text('Опубликовать')",
        "button:has-text('Публикую')",
    ]
    for sel in selectors:
        try:
            btn = page.locator(sel).first
            if btn.is_visible(timeout=3000):
                btn.click()
                return
        except Exception:
            pass
    raise RuntimeError("Не найдена кнопка 'Опубликовать'")
