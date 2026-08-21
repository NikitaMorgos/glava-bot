"""
Рендеринг HTML → PDF на сервере для регенерации книги после inline-правок.

Backends:
- weasyprint  — чистый Python, легче ставится (зависит от cairo/pango), лучше типографика.
- playwright  — Chromium headless, идентичен браузеру; уже используется в pipeline glava.

Выбор: env CABINET_PDF_BACKEND={weasyprint|playwright}, по умолчанию weasyprint.
Каждый backend пытается импортироваться по требованию — если модуль не установлен,
автоматически даунгрейдим на доступный.
"""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


class PdfRenderError(Exception):
    """Не удалось отрендерить PDF."""


def _render_with_weasyprint(html: str, base_url: str | None) -> bytes:
    from weasyprint import HTML  # type: ignore
    pdf_bytes = HTML(string=html, base_url=base_url).write_pdf()
    if pdf_bytes is None:
        raise PdfRenderError("weasyprint вернул пустой PDF")
    return pdf_bytes


def _render_with_playwright(html: str, base_url: str | None) -> bytes:
    from playwright.sync_api import sync_playwright  # type: ignore
    # Записываем HTML во временный файл, чтобы Chromium его открыл
    with tempfile.NamedTemporaryFile(
        suffix=".html", delete=False, mode="w", encoding="utf-8"
    ) as tmp:
        tmp.write(html)
        tmp_path = Path(tmp.name)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(tmp_path.as_uri(), wait_until="networkidle")
            pdf_bytes = page.pdf(
                format="A5",
                margin={"top": "20mm", "right": "20mm", "bottom": "20mm", "left": "20mm"},
                print_background=True,
            )
            browser.close()
        return pdf_bytes
    finally:
        tmp_path.unlink(missing_ok=True)


def render_html_to_pdf(html: str, base_url: str | None = None) -> bytes:
    """
    Рендерит HTML в PDF.
    base_url — если в HTML есть <img src="relative"> ссылки, нужна точка отсчёта.
    """
    backend = (os.environ.get("CABINET_PDF_BACKEND") or "weasyprint").strip().lower()
    candidates = (
        [_render_with_weasyprint, _render_with_playwright]
        if backend == "weasyprint"
        else [_render_with_playwright, _render_with_weasyprint]
    )
    last_err: Exception | None = None
    for fn in candidates:
        try:
            return fn(html, base_url)
        except ImportError as e:
            logger.warning("PDF backend недоступен (%s), пробую следующий", e)
            last_err = e
            continue
        except Exception as e:
            logger.exception("PDF backend %s упал: %s", fn.__name__, e)
            last_err = e
            continue
    raise PdfRenderError(
        f"Ни один PDF-backend не сработал. Последняя ошибка: {last_err}"
    )
