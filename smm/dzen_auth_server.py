"""
Server-side Dzen authentication manager.
Runs a Playwright browser on the server, takes screenshots every second,
and allows interaction (click, type, navigate) via API routes.
This solves the IP-binding issue: the session is created from the server's IP.
"""
import base64
import logging
import threading
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_DEFAULT_SESSION_FILE = (
    Path(__file__).resolve().parent.parent / "cookies" / "dzen_session.json"
)

_PLAYWRIGHT_LAUNCH_ARGS = [
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-blink-features=AutomationControlled",
]

_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


class _State:
    def __init__(self):
        self.lock = threading.Lock()
        self.status = "idle"  # idle | running | saved | error
        self.message = ""
        self.url = ""
        self.screenshot: bytes = b""
        self.page = None
        self.ctx = None
        self._browser = None
        self._thread: Optional[threading.Thread] = None


_state = _State()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_state() -> dict:
    return {
        "status": _state.status,
        "url": _state.url,
        "message": _state.message,
        "screenshot_b64": (
            base64.b64encode(_state.screenshot).decode()
            if _state.screenshot
            else ""
        ),
    }


def start(session_path: Optional[Path] = None) -> None:
    """Start Playwright browser session in a background thread."""
    with _state.lock:
        if _state.status == "running":
            return
        _state.status = "running"
        _state.message = "Запуск браузера…"
        _sp = session_path or _DEFAULT_SESSION_FILE

    t = threading.Thread(target=_run, args=(_sp,), daemon=True)
    _state._thread = t
    t.start()


def stop() -> None:
    with _state.lock:
        if _state.status == "running":
            _state.status = "stopping"


def navigate(url: str) -> None:
    if _state.page:
        try:
            _state.page.goto(url, wait_until="domcontentloaded", timeout=20_000)
            time.sleep(1)
            _snap()
        except Exception as e:
            logger.warning("dzen_auth navigate error: %s", e)


def click(x: int, y: int) -> None:
    if _state.page:
        try:
            _state.page.mouse.click(x, y)
            time.sleep(0.7)
            _snap()
        except Exception as e:
            logger.warning("dzen_auth click error: %s", e)


def type_text(text: str) -> None:
    if _state.page:
        try:
            _state.page.keyboard.type(text, delay=60)
            time.sleep(0.3)
            _snap()
        except Exception as e:
            logger.warning("dzen_auth type error: %s", e)


def press_key(key: str) -> None:
    if _state.page:
        try:
            _state.page.keyboard.press(key)
            time.sleep(0.7)
            _snap()
        except Exception as e:
            logger.warning("dzen_auth key error: %s", e)


def save_session(session_path: Optional[Path] = None) -> bool:
    sp = session_path or _DEFAULT_SESSION_FILE
    if _state.page and _state.ctx:
        try:
            sp.parent.mkdir(parents=True, exist_ok=True)
            _state.ctx.storage_state(path=str(sp))
            with _state.lock:
                _state.status = "saved"
                _state.message = f"✓ Сессия сохранена: {sp}"
            logger.info("dzen_auth: session saved to %s", sp)
            return True
        except Exception as e:
            with _state.lock:
                _state.status = "error"
                _state.message = str(e)
    return False


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _snap() -> None:
    """Take a screenshot and update state."""
    if _state.page:
        try:
            _state.screenshot = _state.page.screenshot(type="jpeg", quality=75)
            _state.url = _state.page.url
        except Exception:
            pass


def _run(session_path: Path) -> None:
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=_PLAYWRIGHT_LAUNCH_ARGS,
            )
            ctx = browser.new_context(
                viewport={"width": 1280, "height": 900},
                user_agent=_USER_AGENT,
            )
            page = ctx.new_page()
            _state.page = page
            _state.ctx = ctx
            _state._browser = browser

            _state.message = "Открываем dzen.ru…"
            try:
                page.goto("https://dzen.ru", wait_until="domcontentloaded", timeout=30_000)
            except Exception:
                pass
            time.sleep(2)
            _snap()
            _state.message = "Готово. Нажмите «Войти» на скриншоте."

            # Keep alive until status changes
            while _state.status == "running":
                time.sleep(1)
                _snap()

            browser.close()
            _state.page = None
            _state.ctx = None
            _state._browser = None

    except Exception as e:
        logger.exception("dzen_auth_server error: %s", e)
        with _state.lock:
            _state.status = "error"
            _state.message = str(e)
