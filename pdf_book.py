# -*- coding: utf-8 -*-
"""
Генератор PDF-книги из bio_text.

Использует reportlab для создания книжного PDF формата A5.
Стиль: тёплый, книжный, аккуратный.

Использование:
    from pdf_book import generate_book_pdf
    pdf_bytes = generate_book_pdf(bio_text, character_name="Мария")
"""
import io
import re
import logging

from reportlab.lib.pagesizes import A5
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, HRFlowable,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus.flowables import KeepTogether

logger = logging.getLogger(__name__)

# ── Цвета ──────────────────────────────────────────────────────────────
CREAM       = HexColor("#FAF6F0")
INK         = HexColor("#1A1208")
GOLD        = HexColor("#A8823C")
MUTED       = HexColor("#7A6B5A")
LIGHT_LINE  = HexColor("#DDD5C8")

# ── Шрифты ─────────────────────────────────────────────────────────────
# Кириллица требует TTF-шрифта. Ищем DejaVuSerif (есть на большинстве Linux).
# Резерв — проверяем локальную папку fonts/ рядом с модулем.

import os as _os

_HERE = _os.path.dirname(_os.path.abspath(__file__))

_FONT_CANDIDATES = {
    "DejaVuSerif": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        _os.path.join(_HERE, "fonts", "DejaVuSerif.ttf"),
    ],
    "DejaVuSerif-Bold": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
        _os.path.join(_HERE, "fonts", "DejaVuSerif-Bold.ttf"),
    ],
    "DejaVuSerif-Italic": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-BoldItalic.ttf",
        _os.path.join(_HERE, "fonts", "DejaVuSerif-BoldItalic.ttf"),
    ],
}


def _register_cyrillic_fonts() -> tuple[str, str, str]:
    """
    Регистрирует DejaVuSerif (поддерживает кириллицу).
    Возвращает (serif, bold, italic).
    Если TTF не найден — возвращает встроенные шрифты (кириллица будет квадратами).
    """
    registered = {}
    for name, paths in _FONT_CANDIDATES.items():
        for path in paths:
            if _os.path.isfile(path):
                try:
                    pdfmetrics.registerFont(TTFont(name, path))
                    registered[name] = True
                    logger.info("pdf_book: шрифт %s загружен из %s", name, path)
                    break
                except Exception as e:
                    logger.warning("pdf_book: не удалось загрузить %s: %s", path, e)

    if "DejaVuSerif" in registered:
        return (
            "DejaVuSerif",
            "DejaVuSerif-Bold" if "DejaVuSerif-Bold" in registered else "DejaVuSerif",
            "DejaVuSerif-Italic" if "DejaVuSerif-Italic" in registered else "DejaVuSerif",
        )

    logger.warning("pdf_book: DejaVu-шрифты не найдены, кириллица будет нечитаема!")
    return "Times-Roman", "Times-Bold", "Times-Italic"


FONT_SERIF, FONT_BOLD, FONT_ITALIC = _register_cyrillic_fonts()


def _build_styles(cover_has_image: bool = False) -> dict:
    # На обложке с изображением текст белый, иначе — стандартные тёмные цвета
    cover_text_color  = white if cover_has_image else INK
    cover_muted_color = HexColor("#E8DDD0") if cover_has_image else MUTED
    cover_gold_color  = HexColor("#F5C87A") if cover_has_image else GOLD

    return {
        "title": ParagraphStyle(
            "title",
            fontName=FONT_BOLD,
            fontSize=26,
            textColor=cover_text_color,
            alignment=TA_CENTER,
            leading=32,
            spaceAfter=6 * mm,
        ),
        "subtitle": ParagraphStyle(
            "subtitle",
            fontName=FONT_ITALIC,
            fontSize=13,
            textColor=cover_muted_color,
            alignment=TA_CENTER,
            leading=18,
            spaceAfter=4 * mm,
        ),
        "cover_label": ParagraphStyle(
            "cover_label",
            fontName=FONT_SERIF,
            fontSize=10,
            textColor=cover_muted_color,
            alignment=TA_CENTER,
            leading=14,
            spaceAfter=2 * mm,
        ),
        "_cover_gold": cover_gold_color,  # используется для HRFlowable на обложке
        "chapter_heading": ParagraphStyle(
            "chapter_heading",
            fontName=FONT_BOLD,
            fontSize=14,
            textColor=INK,
            alignment=TA_LEFT,
            leading=20,
            spaceBefore=8 * mm,
            spaceAfter=4 * mm,
        ),
        "section_heading": ParagraphStyle(
            "section_heading",
            fontName=FONT_BOLD,
            fontSize=11,
            textColor=GOLD,
            alignment=TA_LEFT,
            leading=16,
            spaceBefore=5 * mm,
            spaceAfter=2 * mm,
        ),
        "body": ParagraphStyle(
            "body",
            fontName=FONT_SERIF,
            fontSize=10,
            textColor=INK,
            alignment=TA_JUSTIFY,
            leading=17,
            spaceAfter=3 * mm,
            firstLineIndent=5 * mm,
        ),
        "body_first": ParagraphStyle(
            "body_first",
            fontName=FONT_SERIF,
            fontSize=10,
            textColor=INK,
            alignment=TA_JUSTIFY,
            leading=17,
            spaceAfter=3 * mm,
        ),
        "footer_text": ParagraphStyle(
            "footer_text",
            fontName=FONT_SERIF,
            fontSize=8,
            textColor=MUTED,
            alignment=TA_CENTER,
            leading=12,
        ),
    }


def _is_chapter_heading(line: str) -> bool:
    """Определяет, является ли строка заголовком главы."""
    stripped = line.strip()
    if not stripped:
        return False
    patterns = [
        r"^(Глава|Chapter)\s+\d+",
        r"^\d+\.\s+[А-ЯA-Z]",
        r"^[IVX]+\.\s+",
        r"^#{1,3}\s+",
        r"^[А-ЯA-Z][А-ЯA-Z\s]{4,40}$",  # Строка полностью заглавными (название главы)
    ]
    for p in patterns:
        if re.match(p, stripped):
            return True
    # Короткая строка без точки в конце, начинается с заглавной
    if len(stripped) < 60 and stripped[0].isupper() and not stripped.endswith(('.', ',', ';', ':')):
        words = stripped.split()
        if len(words) <= 6:
            return True
    return False


def _is_section_heading(line: str) -> bool:
    """Определяет подзаголовок секции (курсивный раздел)."""
    stripped = line.strip()
    if not stripped or len(stripped) > 80:
        return False
    if stripped.startswith('**') and stripped.endswith('**'):
        return True
    if stripped.startswith('##'):
        return True
    return False


def _clean(text: str) -> str:
    """Очищает markdown-разметку и лишние символы."""
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'^#{1,6}\s*', '', text, flags=re.MULTILINE)
    text = text.replace('—', '\u2014').replace('–', '\u2013')
    text = text.replace('"', '\u00ab').replace('"', '\u00bb')
    text = text.replace("'", '\u2019')
    return text.strip()


def _add_page_border(canvas, doc):
    """Рисует тонкую рамку и колонтитул на каждой странице."""
    canvas.saveState()
    w, h = A5
    margin = 10 * mm

    # Нижний колонтитул
    canvas.setFont(FONT_SERIF, 7)
    canvas.setFillColor(MUTED)
    canvas.drawCentredString(w / 2, margin - 4 * mm, "Глава — семейная биография · glava.family")

    # Номер страницы
    page_num = canvas.getPageNumber()
    if page_num > 1:
        canvas.drawCentredString(w / 2, margin - 8 * mm, str(page_num))

    canvas.restoreState()


def _make_cover_callback(cover_image_bytes: bytes | None):
    """
    Возвращает onFirstPage-callback для SimpleDocTemplate.
    Если cover_image_bytes задан — рисует full-bleed изображение + тёмный оверлей
    поверх которого платформа рендерит story-элементы (белый текст).
    """
    def on_first_page(canvas, doc):
        if cover_image_bytes:
            from io import BytesIO
            from reportlab.lib.utils import ImageReader
            try:
                page_w, page_h = A5
                img_reader = ImageReader(BytesIO(cover_image_bytes))
                canvas.saveState()
                # full-bleed изображение
                canvas.drawImage(
                    img_reader, 0, 0,
                    width=page_w, height=page_h,
                    preserveAspectRatio=False,
                    mask="auto",
                )
                # Полупрозрачный тёмный оверлей для читаемости текста
                canvas.setFillColor(black)
                canvas.setFillAlpha(0.52)
                canvas.rect(0, 0, page_w, page_h, fill=1, stroke=0)
                canvas.setFillAlpha(1.0)
                canvas.restoreState()
            except Exception as e:
                logger.warning("pdf_book: не удалось нарисовать cover image: %s", e)
        # Колонтитул пропускаем на обложке
    return on_first_page


def generate_book_pdf(
    bio_text: str,
    character_name: str = "Герой книги",
    subtitle: str = "Семейная биография",
    cover_spec: dict | None = None,
    cover_image_bytes: bytes | None = None,
) -> bytes:
    """
    Генерирует PDF-книгу из bio_text.

    Args:
        bio_text: текст биографии
        character_name: имя героя (запасной заголовок)
        subtitle: подзаголовок (запасной)
        cover_spec: словарь от Cover Designer агента с полями
                    title, subtitle, tagline, visual_style
        cover_image_bytes: AI-сгенерированное изображение обложки (PNG/WebP).
                           Если задано — full-bleed обложка с тёмным оверлеем
                           и белым текстом; иначе — текстовая обложка.

    Returns:
        bytes: содержимое PDF-файла
    """
    cs = cover_spec or {}
    book_title    = cs.get("title") or character_name
    book_subtitle = cs.get("subtitle") or subtitle
    book_tagline  = cs.get("tagline", "")

    buf = io.BytesIO()
    page_w, page_h = A5

    doc = SimpleDocTemplate(
        buf,
        pagesize=A5,
        leftMargin=18 * mm,
        rightMargin=15 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=f"{book_title} — семейная биография",
        author="Глава · glava.family",
        subject="Семейная биография",
    )

    has_image = bool(cover_image_bytes)
    styles = _build_styles(cover_has_image=has_image)
    cover_hr_color = styles.pop("_cover_gold")  # цвет разделителей на обложке
    story = []

    # ── Обложка (title page) ───────────────────────────────────────────
    # При наличии изображения: больше пространства сверху, текст ниже
    story.append(Spacer(1, 30 * mm if has_image else 22 * mm))
    story.append(Paragraph("Глава", styles["cover_label"]))
    story.append(Spacer(1, 6 * mm))
    story.append(HRFlowable(width="60%", thickness=0.5, color=cover_hr_color, hAlign="CENTER"))
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph(_clean(book_title), styles["title"]))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(_clean(book_subtitle), styles["subtitle"]))
    if book_tagline:
        story.append(Spacer(1, 3 * mm))
        story.append(Paragraph(_clean(book_tagline), styles["cover_label"]))
    story.append(Spacer(1, 8 * mm))
    story.append(HRFlowable(width="60%", thickness=0.5, color=cover_hr_color, hAlign="CENTER"))
    story.append(Spacer(1, 18 * mm))
    story.append(Paragraph("glava.family", styles["cover_label"]))
    story.append(PageBreak())

    # ── Контент ────────────────────────────────────────────────────────
    lines = bio_text.strip().split('\n')
    first_para_in_chapter = True

    for line in lines:
        line = line.rstrip()

        if not line:
            first_para_in_chapter = False
            continue

        if _is_section_heading(line):
            clean = _clean(line)
            story.append(Paragraph(clean, styles["section_heading"]))
            first_para_in_chapter = True
            continue

        if _is_chapter_heading(line):
            clean = _clean(line)
            story.append(Paragraph(clean, styles["chapter_heading"]))
            story.append(HRFlowable(width="30%", thickness=0.3, color=LIGHT_LINE, hAlign="LEFT"))
            story.append(Spacer(1, 2 * mm))
            first_para_in_chapter = True
            continue

        # Обычный текстовый параграф
        clean = _clean(line)
        if not clean:
            continue

        style = styles["body_first"] if first_para_in_chapter else styles["body"]
        story.append(Paragraph(clean, style))
        first_para_in_chapter = False

    # ── Финальная страница ─────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Spacer(1, 40 * mm))
    story.append(HRFlowable(width="40%", thickness=0.5, color=GOLD, hAlign="CENTER"))
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph("Создано с любовью", styles["subtitle"]))
    story.append(Paragraph("glava.family", styles["cover_label"]))

    cover_cb = _make_cover_callback(cover_image_bytes)

    def on_first_page(canvas, doc):
        cover_cb(canvas, doc)
        if not has_image:
            _add_page_border(canvas, doc)

    try:
        doc.build(story, onFirstPage=on_first_page, onLaterPages=_add_page_border)
    except Exception as e:
        logger.error("pdf_book: ошибка сборки PDF: %s", e)
        raise

    pdf_bytes = buf.getvalue()
    buf.close()
    logger.info("pdf_book: сгенерирован PDF %d байт для '%s'", len(pdf_bytes), character_name)
    return pdf_bytes
