#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
glava.pdf_builder — детерминированный сборщик PDF.

Интерфейс (из спеки):
    from glava.pdf_builder import build_pdf

    pdf_path = build_pdf(
        layout_instructions=dict,   # JSON от Верстальщика (pages[])
        book_json_path=str,         # путь к book_final.json
        photos_dir=str,             # папка с фото (manifest.json там же)
        cover_portrait=str|None,    # путь к PNG/webp обложки
        output_path=str,            # куда сохранить PDF
    ) -> str | None                 # путь к PDF или None при ошибке
"""
import json
import pathlib
import re
import sys
import tempfile
import logging
from datetime import datetime
from typing import Optional

log = logging.getLogger(__name__)

# ── ReportLab imports ─────────────────────────────────────────────
try:
    from reportlab.lib.pagesizes import A5
    from reportlab.lib.units import mm
    from reportlab.lib.colors import HexColor, white, black
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY, TA_RIGHT
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, PageBreak,
        Image, Table, TableStyle, HRFlowable, KeepTogether,
    )
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from PIL import Image as PILImage
    _RL_OK = True
except ImportError as e:
    log.error(f"Missing dependency: {e}. Run: pip install reportlab pillow")
    _RL_OK = False

# ── Font registration ─────────────────────────────────────────────
FONT_DIR = pathlib.Path("/opt/glava/fonts")
FALLBACK_SERIF = "/usr/share/fonts/truetype/freefont/FreeSerif.ttf"
FALLBACK_SANS  = "/usr/share/fonts/truetype/freefont/FreeSans.ttf"

_FONTS_REGISTERED = False

def _register_fonts():
    global _FONTS_REGISTERED
    if _FONTS_REGISTERED or not _RL_OK:
        return
    defs = [
        ("PTSerif",           FONT_DIR / "PTSerif-Regular.ttf",     FALLBACK_SERIF),
        ("PTSerif-Bold",      FONT_DIR / "PTSerif-Bold.ttf",        FALLBACK_SERIF),
        ("PTSerif-Italic",    FONT_DIR / "PTSerif-Italic.ttf",      FALLBACK_SERIF),
        ("PTSerif-BoldItalic",FONT_DIR / "PTSerif-BoldItalic.ttf",  FALLBACK_SERIF),
        ("PTSans",            FONT_DIR / "PTSans-Regular.ttf",      FALLBACK_SANS),
        ("PTSans-Bold",       FONT_DIR / "PTSans-Bold.ttf",         FALLBACK_SANS),
    ]
    for name, primary, fallback in defs:
        path = str(primary) if primary.exists() else fallback
        try:
            pdfmetrics.registerFont(TTFont(name, path))
            log.debug(f"Font registered: {name} ← {path}")
        except Exception as ex:
            log.warning(f"Font {name} failed ({ex}), trying fallback {fallback}")
            try:
                pdfmetrics.registerFont(TTFont(name, fallback))
            except Exception as ex2:
                log.error(f"Font {name} fallback also failed: {ex2}")
    _FONTS_REGISTERED = True


# ── Palette ───────────────────────────────────────────────────────
C_BG        = HexColor("#faf8f5") if _RL_OK else None
C_TEXT      = HexColor("#111111") if _RL_OK else None
C_HEAD      = HexColor("#111111") if _RL_OK else None
C_MUTED     = HexColor("#999999") if _RL_OK else None
C_ACCENT    = HexColor("#8b7355") if _RL_OK else None
C_RULE      = HexColor("#e8e0d4") if _RL_OK else None
C_CALLOUT   = HexColor("#f5ede0") if _RL_OK else None
C_HIST_BG   = HexColor("#1a1a2e") if _RL_OK else None
C_HIST_TX   = HexColor("#c4bfb3") if _RL_OK else None
C_CAPTION   = HexColor("#666666") if _RL_OK else None

# ── Page geometry ─────────────────────────────────────────────────
W, H    = A5 if _RL_OK else (419, 595)
ML = 22 * mm    # inner margin
MR = 18 * mm    # outer margin
MT = 20 * mm
MB = 25 * mm
TW = W - ML - MR


# ══════════════════════════════════════════════════════════════════
# Styles
# ══════════════════════════════════════════════════════════════════

def make_styles():
    S = {}
    S["body"] = ParagraphStyle(
        "body", fontName="PTSerif", fontSize=10.5, leading=18,
        textColor=C_TEXT, alignment=TA_LEFT,
        firstLineIndent=12, spaceAfter=0,
    )
    S["ch_label"] = ParagraphStyle(
        "ch_label", fontName="PTSans", fontSize=7, leading=10,
        textColor=C_MUTED, alignment=TA_LEFT,
        letterSpacing=3, spaceBefore=10*mm, spaceAfter=3,
    )
    S["ch_title"] = ParagraphStyle(
        "ch_title", fontName="PTSerif-Bold", fontSize=24, leading=28,
        textColor=C_HEAD, alignment=TA_LEFT, spaceAfter=6,
    )
    S["ch_sub"] = ParagraphStyle(
        "ch_sub", fontName="PTSerif-Bold", fontSize=11, leading=15,
        textColor=C_HEAD, alignment=TA_LEFT,
        spaceBefore=8*mm, spaceAfter=3*mm,
    )
    S["callout"] = ParagraphStyle(
        "callout", fontName="PTSerif-Italic", fontSize=14, leading=20,
        textColor=C_ACCENT, alignment=TA_CENTER,
    )
    S["callout_attr"] = ParagraphStyle(
        "callout_attr", fontName="PTSans", fontSize=7, leading=10,
        textColor=C_MUTED, alignment=TA_CENTER,
        letterSpacing=2, spaceBefore=4,
    )
    S["caption"] = ParagraphStyle(
        "caption", fontName="PTSerif-Italic", fontSize=8, leading=11,
        textColor=C_CAPTION, alignment=TA_LEFT, spaceAfter=3,
    )
    S["hist_label"] = ParagraphStyle(
        "hist_label", fontName="PTSans", fontSize=7, leading=9,
        textColor=HexColor("#8b8577"), alignment=TA_LEFT,
        letterSpacing=3, spaceAfter=4,
    )
    S["hist_body"] = ParagraphStyle(
        "hist_body", fontName="PTSerif-Italic", fontSize=9.5, leading=14,
        textColor=C_HIST_TX, alignment=TA_LEFT, spaceAfter=0,
    )
    S["toc_title"] = ParagraphStyle(
        "toc_title", fontName="PTSans", fontSize=11, leading=14,
        textColor=C_MUTED, alignment=TA_LEFT,
        letterSpacing=3, spaceBefore=8*mm, spaceAfter=10,
    )
    S["toc_entry"] = ParagraphStyle(
        "toc_entry", fontName="PTSerif", fontSize=13, leading=26,
        textColor=C_HEAD, alignment=TA_LEFT,
    )
    S["toc_page"] = ParagraphStyle(
        "toc_page", fontName="PTSans", fontSize=10, leading=26,
        textColor=C_MUTED, alignment=TA_RIGHT,
    )
    S["title_name"] = ParagraphStyle(
        "title_name", fontName="PTSerif-Bold", fontSize=28, leading=32,
        textColor=C_HEAD, alignment=TA_LEFT, spaceAfter=4,
    )
    S["title_years"] = ParagraphStyle(
        "title_years", fontName="PTSans", fontSize=11, leading=14,
        textColor=C_MUTED, alignment=TA_LEFT, spaceAfter=8,
    )
    S["epigraph"] = ParagraphStyle(
        "epigraph", fontName="PTSerif-Italic", fontSize=12, leading=18,
        textColor=HexColor("#666666"), alignment=TA_LEFT,
    )
    S["chapter_end"] = ParagraphStyle(
        "chapter_end", fontName="PTSerif", fontSize=14, leading=18,
        textColor=C_RULE, alignment=TA_CENTER,
    )
    S["final_logo"] = ParagraphStyle(
        "final_logo", fontName="PTSans", fontSize=10, leading=14,
        textColor=C_RULE, alignment=TA_CENTER,
    )
    S["final_sub"] = ParagraphStyle(
        "final_sub", fontName="PTSans", fontSize=7, leading=10,
        textColor=C_MUTED, alignment=TA_CENTER,
    )
    return S


# ══════════════════════════════════════════════════════════════════
# Data loaders
# ══════════════════════════════════════════════════════════════════

def _load_book(book_json_path: str) -> dict:
    p = pathlib.Path(book_json_path)
    if not p.exists():
        raise FileNotFoundError(f"book_json not found: {book_json_path}")
    data = json.loads(p.read_text(encoding="utf-8"))
    return data.get("book_final", data)


def _load_photos(photos_dir: str) -> dict:
    """Returns dict: photo_id -> {path, caption, ...}

    Keys use the same format the orchestrator and Layout Designer agree on:
    photo_001, photo_002, ... (padded index from manifest).
    """
    d = pathlib.Path(photos_dir)
    manifest = d / "manifest.json"
    if not manifest.exists():
        return {}
    items = json.loads(manifest.read_text(encoding="utf-8"))
    result = {}
    for item in items:
        idx = item.get("index", 0)
        # Primary key: photo_NNN (matches orchestrator + layout_instructions)
        pid = f"photo_{idx:03d}"
        fname = item.get("filename", "")
        fpath = d / fname
        if not fpath.exists():
            fpath = pathlib.Path(item.get("local_path", ""))
        if fpath.exists():
            result[pid] = {
                "path": fpath,
                "caption": item.get("caption", ""),
                "index": idx,
                "period": item.get("period", ""),
            }
    return result


def _build_chapter_index(book: dict) -> dict:
    """Returns dict: chapter_id -> chapter_dict"""
    return {ch["id"]: ch for ch in book.get("chapters", [])}


def _build_callout_index(book: dict) -> dict:
    return {c["id"]: c for c in book.get("callouts", [])}


def _build_hist_index(book: dict) -> dict:
    idx = {}
    for h in book.get("historical_notes", book.get("historical_inserts", [])):
        idx[h.get("id", "")] = h
    return idx


# ══════════════════════════════════════════════════════════════════
# Content resolvers
# ══════════════════════════════════════════════════════════════════

def _resolve_ref(content_ref: str, book: dict, ch_idx: dict) -> str:
    """Resolve content_ref like 'ch_01.content', 'ch_01.title', or 'subject_name'."""
    if not content_ref:
        return ""
    if content_ref == "subject_name":
        return book.get("subject_name", "")
    parts = content_ref.split(".", 1)
    ch_id = parts[0]
    field = parts[1] if len(parts) > 1 else "content"
    ch = ch_idx.get(ch_id, {})
    if field == "content":
        return ch.get("content", "")
    if field == "title":
        return ch.get("title", "")
    return ""


def _parse_md_paragraphs(text: str, styles: dict) -> list:
    """Convert Markdown-ish chapter text to ReportLab flowables."""
    out = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            out.append(Spacer(1, 2*mm))
            continue
        if line.startswith("### "):
            out.append(Paragraph(line[4:], styles["ch_sub"]))
        elif line.startswith("## "):
            out.append(Paragraph(line[3:], styles["ch_sub"]))
        elif line.startswith("# "):
            out.append(Paragraph(line[2:], styles["ch_sub"]))
        else:
            line = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            line = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", line)
            line = re.sub(r"_(.+?)_",       r"<i>\1</i>", line)
            out.append(Paragraph(line, styles["body"]))
    return out


# ══════════════════════════════════════════════════════════════════
# Element builders
# ══════════════════════════════════════════════════════════════════

def _make_photo_block(photo: dict, caption_override: str, styles: dict, layout: str = "full_width") -> list:
    path = photo["path"]
    caption = caption_override or photo.get("caption", "")
    try:
        img_obj = PILImage.open(str(path))
        iw, ih = img_obj.size
        if layout == "full_page":
            max_w, max_h = TW, H - MT - MB - 15*mm
        elif layout in ("inline_small", "wrap_left", "wrap_right"):
            max_w, max_h = TW * 0.5, 50*mm
        else:
            max_w, max_h = TW, 80*mm
        scale = min(max_w / iw, max_h / ih)
        w, h = iw * scale, ih * scale

        # webp → temp png
        if str(path).lower().endswith(".webp"):
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            img_obj.save(tmp.name, "PNG")
            tmp.close()
            img_flowable = Image(tmp.name, width=w, height=h)
        else:
            img_flowable = Image(str(path), width=w, height=h)

        items = [Spacer(1, 3*mm), img_flowable]
        if caption:
            items.append(Paragraph(caption, styles["caption"]))
        items.append(Spacer(1, 3*mm))
        return [KeepTogether(items)]
    except Exception as ex:
        log.warning(f"Photo {path.name}: {ex}")
        return []


def _make_callout(text: str, styles: dict) -> list:
    inner = [
        Paragraph(f"\u00ab{text}\u00bb", styles["callout"]),
        Paragraph("\u2014 из воспоминаний семьи", styles["callout_attr"]),
    ]
    tbl = Table(
        [[inner]],
        colWidths=[TW],
        style=TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), C_CALLOUT),
            ("TOPPADDING",    (0, 0), (-1, -1), 12),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ("LEFTPADDING",   (0, 0), (-1, -1), 8*mm),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 8*mm),
            ("LINEABOVE",     (0, 0), (-1, 0), 0.5, C_ACCENT),
            ("LINEBELOW",     (0,-1), (-1,-1), 0.5, C_ACCENT),
        ]),
    )
    return [Spacer(1, 5*mm), tbl, Spacer(1, 5*mm)]


def _make_hist_block(text: str, styles: dict) -> list:
    inner = [
        Paragraph("▌ ИСТОРИЧЕСКАЯ СПРАВКА", styles["hist_label"]),
        Paragraph(text, styles["hist_body"]),
    ]
    tbl = Table(
        [[inner]],
        colWidths=[TW],
        style=TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), C_HIST_BG),
            ("TOPPADDING",    (0, 0), (-1, -1), 14),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
            ("LEFTPADDING",   (0, 0), (-1, -1), 8*mm),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 8*mm),
        ]),
    )
    return [Spacer(1, 5*mm), tbl, Spacer(1, 5*mm)]


def _make_chapter_end() -> list:
    return [
        Spacer(1, 10*mm),
        Paragraph("⁂", ParagraphStyle(
            "_end", fontName="PTSerif", fontSize=14, leading=18,
            textColor=C_RULE, alignment=TA_CENTER,
        )),
        PageBreak(),
    ]


# ══════════════════════════════════════════════════════════════════
# Cover page (drawn on canvas)
# ══════════════════════════════════════════════════════════════════

def _draw_cover(canvas, doc, cover_portrait_path: Optional[str],
                cover_composition: Optional[dict], subject_name: str):
    comp = cover_composition or {}
    canvas.saveState()

    # Background
    bg = comp.get("background_color", "#faf8f5")
    canvas.setFillColor(HexColor(bg))
    canvas.rect(0, 0, W, H, fill=1, stroke=0)

    # Portrait
    if cover_portrait_path and pathlib.Path(cover_portrait_path).exists():
        try:
            img = PILImage.open(cover_portrait_path).convert("RGBA")
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            img.save(tmp.name, "PNG")
            tmp.close()
            iw, ih = img.size
            zone_w, zone_h = W * 0.75, H * 0.55
            scale = min(zone_w / iw, zone_h / ih)
            pw, ph = iw * scale, ih * scale
            px = (W - pw) / 2
            py = H * 0.25
            canvas.drawImage(tmp.name, px, py, pw, ph, mask="auto")
        except Exception as ex:
            log.warning(f"Cover portrait: {ex}")

    accent = comp.get("accent_color", "#c4a070")
    typ = comp.get("typography", {})

    # Top line
    canvas.setStrokeColor(HexColor(accent))
    canvas.setLineWidth(1)
    canvas.line(ML, H - 10*mm, W - MR, H - 10*mm)

    # Surname
    surname = typ.get("surname", {}).get("text", subject_name.split()[-1].upper() if subject_name else "")
    canvas.setFont("PTSerif-Bold", 26)
    canvas.setFillColor(HexColor(comp.get("text_primary_color", "#111111")))
    y_s = H - 18*mm
    canvas.drawCentredString(W / 2, y_s, surname)

    # First name
    first_name = typ.get("first_name", {}).get("text", "")
    if first_name:
        canvas.setFont("PTSerif-Italic", 13)
        canvas.setFillColor(HexColor(comp.get("text_secondary_color", "#8b7355")))
        canvas.drawCentredString(W / 2, y_s - 16, first_name)

    # Subtitle
    subtitle = typ.get("subtitle", {}).get("text", "")
    if subtitle:
        canvas.setFont("PTSans", 6)
        canvas.setFillColor(HexColor(comp.get("text_muted_color", "#999999")))
        canvas.drawCentredString(W / 2, y_s - 31, subtitle.upper())

    # Separator under name
    canvas.setStrokeColor(HexColor(accent))
    canvas.setLineWidth(0.5)
    canvas.line(W/2 - 25*mm, y_s - 23, W/2 + 25*mm, y_s - 23)

    # Years at bottom
    dec = comp.get("decorative_elements", {})
    yl = dec.get("years_line", {})
    years = f"{yl.get('text_left', '')} — {yl.get('text_right', '')}".strip(" —")
    if years:
        canvas.setFont("PTSans", 8)
        canvas.setFillColor(HexColor(comp.get("text_muted_color", "#999999")))
        canvas.drawCentredString(W / 2, 14*mm, years)

    # Logo
    canvas.setFont("PTSans", 7)
    canvas.setFillColor(HexColor(accent))
    canvas.drawCentredString(W / 2, 9*mm, "Glava")

    # Bottom line
    canvas.setStrokeColor(HexColor(accent))
    canvas.setLineWidth(1)
    canvas.line(ML, 8*mm, W - MR, 8*mm)

    canvas.restoreState()


# ══════════════════════════════════════════════════════════════════
# Page callbacks
# ══════════════════════════════════════════════════════════════════

def _make_page_callbacks(cover_portrait, cover_composition, subject_name):
    cover_drawn = [False]

    def on_page(canvas, doc):
        pn = doc.page
        if pn == 1 and not cover_drawn[0]:
            _draw_cover(canvas, doc, cover_portrait, cover_composition, subject_name)
            cover_drawn[0] = True
            return
        canvas.saveState()
        canvas.setFillColor(C_BG)
        canvas.rect(0, 0, W, H, fill=1, stroke=0)
        if pn > 3:
            # Header rule
            canvas.setStrokeColor(C_RULE)
            canvas.setLineWidth(0.4)
            canvas.line(ML, H - MT + 4*mm, W - MR, H - MT + 4*mm)
            # Running header: left = hero name
            canvas.setFont("PTSans", 7)
            canvas.setFillColor(C_MUTED)
            canvas.drawString(ML, H - MT + 6*mm, subject_name.upper())
            # Page number (logical: page 4 physical → page 1 logical)
            logical_pn = pn - 2  # pages 1–2 are cover+blank, page 3 is TOC
            if logical_pn > 0:
                canvas.setFont("PTSans", 8)
                canvas.setFillColor(C_MUTED)
                canvas.drawCentredString(W / 2, MB - 6*mm, str(logical_pn))
        canvas.restoreState()

    return on_page


def _build_toc_from_pages(pages: list, styles: dict) -> list:
    """Build a TOC table using page_number from layout_instructions pages."""
    story = []
    for page in pages:
        ptype = page.get("type", "")
        if ptype == "chapter_start":
            title = page.get("chapter_title", "")
            if not title:
                for elem in page.get("elements", []):
                    if elem.get("type") in ("heading", "chapter_title", "chapter_label"):
                        title = elem.get("text", "")
                        break
            page_num = page.get("page_number", "")
            # Logical page number: physical page_number - 2 (cover+blank before TOC)
            logical_num = (page_num - 2) if isinstance(page_num, int) and page_num > 2 else ""
            row = Table(
                [[Paragraph(title or "—", styles["toc_entry"]),
                  Paragraph(str(logical_num) if logical_num else "—", styles["toc_page"])]],
                colWidths=[TW * 0.85, TW * 0.15],
                style=TableStyle([
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]),
            )
            story.append(row)
    return story


# ══════════════════════════════════════════════════════════════════
# Story builder — reads layout_instructions.pages[]
# ══════════════════════════════════════════════════════════════════

def _resolve_pages(layout_instructions: dict) -> list:
    """Extract pages[] from layout_instructions or pages[] at top level."""
    if isinstance(layout_instructions, dict):
        pages = layout_instructions.get("pages", [])
        if pages:
            return pages
    return []


def _build_story_from_layout(pages: list, book: dict, photos: dict,
                              styles: dict) -> list:
    """Build ReportLab story from layout_instructions.pages[]."""
    story = []
    ch_idx  = _build_chapter_index(book)
    cal_idx = _build_callout_index(book)
    hist_idx= _build_hist_index(book)
    subject = book.get("subject_name", "")

    for page in pages:
        ptype = page.get("type", "")

        # ── Cover: just a spacer (drawn on canvas) ────────────────
        if ptype == "cover":
            story.append(Spacer(1, 1*mm))
            story.append(PageBreak())
            continue

        # ── Blank ─────────────────────────────────────────────────
        if ptype == "blank":
            story.append(Spacer(1, 1*mm))
            story.append(PageBreak())
            continue

        # ── TOC ───────────────────────────────────────────────────
        if ptype == "toc":
            story.append(Spacer(1, 8*mm))
            story.append(Paragraph("СОДЕРЖАНИЕ", styles["toc_title"]))
            story.append(HRFlowable(width=TW, thickness=0.4, color=C_RULE, spaceAfter=8))
            # Build TOC using page_number from layout_instructions
            toc_rows = _build_toc_from_pages(pages, styles)
            if toc_rows:
                story += toc_rows
            else:
                # Fallback: chapters without page numbers
                for ch in book.get("chapters", []):
                    row = Table(
                        [[Paragraph(ch["title"], styles["toc_entry"]),
                          Paragraph("—", styles["toc_page"])]],
                        colWidths=[TW * 0.85, TW * 0.15],
                    )
                    story.append(row)
            story.append(PageBreak())
            continue

        # ── Title spread ──────────────────────────────────────────
        if ptype == "title_spread":
            story.append(Spacer(1, 20*mm))
            story.append(Paragraph(subject, styles["title_name"]))
            years = book.get("years", "")
            if years:
                story.append(Paragraph(years, styles["title_years"]))
            # Best callout as epigraph
            callouts = book.get("callouts", [])
            if callouts:
                ep = callouts[0]["text"]
                story.append(Paragraph(f"\u00ab{ep}\u00bb", styles["epigraph"]))
            story.append(PageBreak())
            continue

        # ── Chapter start or chapter body ─────────────────────────
        if ptype in ("chapter_start", "chapter_body", "text_only", "text_with_photo",
                     "text_with_callout"):
            elems = page.get("elements", [])
            ch_id = page.get("chapter_id", "")
            for elem in elems:
                etype = elem.get("type", "")

                if etype == "chapter_label":
                    text = elem.get("text", "")
                    story.append(Spacer(1, 10*mm))
                    story.append(Paragraph(text, styles["ch_label"]))

                elif etype == "chapter_title":
                    ref = elem.get("content_ref", "")
                    text = _resolve_ref(ref, book, ch_idx) if ref else elem.get("text", "")
                    story.append(Paragraph(text, styles["ch_title"]))
                    story.append(HRFlowable(width=TW * 0.1, thickness=2.5,
                                            color=C_RULE, spaceAfter=4))

                elif etype == "paragraph":
                    text = elem.get("text", "")
                    if text:
                        text = text.replace("&", "&amp;").replace("<","&lt;").replace(">","&gt;")
                        text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
                        text = re.sub(r"_(.+?)_", r"<i>\1</i>", text)
                        story.append(Paragraph(text, styles["body"]))

                elif etype == "text":
                    ref = elem.get("content_ref", "")
                    raw = _resolve_ref(ref, book, ch_idx) if ref else elem.get("text", "")
                    # paragraph_range support
                    pr = elem.get("paragraph_range")
                    if pr and raw:
                        paras = [p.strip() for p in raw.split("\n") if p.strip()]
                        raw = "\n".join(paras[pr[0]:pr[1]])
                    if raw:
                        story += _parse_md_paragraphs(raw, styles)

                elif etype == "photo":
                    pid = elem.get("photo_id", "")
                    ph = photos.get(pid)
                    if ph:
                        cap = elem.get("caption", ph.get("caption", ""))
                        layout = elem.get("layout", "full_width")
                        story += _make_photo_block(ph, cap, styles, layout)

                elif etype == "callout":
                    cid = elem.get("callout_id", "")
                    c = cal_idx.get(cid)
                    text = c["text"] if c else elem.get("text", "")
                    if text:
                        story += _make_callout(text, styles)

                elif etype == "historical_note":
                    hid = elem.get("note_id", "")
                    h = hist_idx.get(hid)
                    text = h["text"] if h else elem.get("text", "")
                    if text:
                        story += _make_hist_block(text, styles)

            # Chapter end ornament (for chapter_start / end of chapter)
            if ptype == "chapter_start" and page.get("is_last_page", False):
                story += _make_chapter_end()
            continue

        # ── Full page photo ───────────────────────────────────────
        if ptype == "full_page_photo":
            pid = page.get("photo_id", "")
            ph = photos.get(pid)
            if ph:
                story += _make_photo_block(ph, page.get("caption", ""), styles, "full_page")
            story.append(PageBreak())
            continue

        # ── Photo page (multiple) ─────────────────────────────────
        if ptype == "photo_page":
            for elem in page.get("elements", []):
                if elem.get("type") == "photo":
                    pid = elem.get("photo_id", "")
                    ph = photos.get(pid)
                    if ph:
                        story += _make_photo_block(ph, elem.get("caption", ""), styles,
                                                   elem.get("layout", "full_width"))
            story.append(PageBreak())
            continue

        # ── Final page ────────────────────────────────────────────
        if ptype in ("final_page", "end_page"):
            story.append(Spacer(1, 60*mm))
            story.append(Paragraph("Glava", styles["final_logo"]))
            story.append(Paragraph(f"Создано в {datetime.now().year}",
                                   styles["final_sub"]))
            continue

    return story


# ══════════════════════════════════════════════════════════════════
# Fallback: build from book_final directly (no layout_instructions)
# ══════════════════════════════════════════════════════════════════

def _build_story_fallback(book: dict, photos: dict, styles: dict) -> list:
    """Build story directly from book_final if no layout_instructions."""
    story = []
    chapters  = book.get("chapters", [])
    callouts  = {c.get("chapter_id", ""): [] for c in book.get("callouts", [])}
    for c in book.get("callouts", []):
        callouts.setdefault(c.get("chapter_id", ""), []).append(c["text"])
    hist_map: dict = {}
    for h in book.get("historical_notes", book.get("historical_inserts", [])):
        hist_map.setdefault(h.get("chapter_id", ""), []).append(h["text"])

    # Cover placeholder
    story.append(Spacer(1, 1*mm))
    story.append(PageBreak())

    # Blank
    story.append(Spacer(1, 1*mm))
    story.append(PageBreak())

    # Title spread
    subject = book.get("subject_name", "")
    if subject:
        story.append(Spacer(1, 20*mm))
        story.append(Paragraph(subject, styles["title_name"]))
        cal = book.get("callouts", [])
        if cal:
            story.append(Paragraph(f"\u00ab{cal[0]['text']}\u00bb", styles["epigraph"]))
        story.append(PageBreak())

    # TOC
    story.append(Spacer(1, 8*mm))
    story.append(Paragraph("СОДЕРЖАНИЕ", styles["toc_title"]))
    story.append(HRFlowable(width=TW, thickness=0.4, color=C_RULE, spaceAfter=8))
    for i, ch in enumerate(chapters, 1):
        story.append(Paragraph(f"{i}. {ch['title']}", styles["toc_entry"]))
    story.append(PageBreak())

    usable = [v for v in photos.values() if v["index"] > 1]
    usable.sort(key=lambda x: x["index"])
    per_ch = max(1, len(usable) // max(len(chapters), 1)) if usable else 0
    photo_idx = 0

    for i, ch in enumerate(chapters, 1):
        ch_id = ch["id"]
        story.append(Spacer(1, 10*mm))
        story.append(Paragraph(f"ГЛАВА {i}", styles["ch_label"]))
        story.append(Paragraph(ch["title"], styles["ch_title"]))
        story.append(HRFlowable(width=TW*0.1, thickness=2.5, color=C_RULE, spaceAfter=4))
        story += _parse_md_paragraphs(ch.get("content", ""), styles)
        for ht in hist_map.get(ch_id, []):
            story += _make_hist_block(ht, styles)
        for ct in callouts.get(ch_id, []):
            story += _make_callout(ct, styles)
        for _ in range(per_ch):
            if photo_idx < len(usable):
                ph = usable[photo_idx]
                story += _make_photo_block(ph, ph["caption"], styles)
                photo_idx += 1
        story += _make_chapter_end()

    if photo_idx < len(usable):
        story.append(Paragraph("Фотографии", styles["ch_title"]))
        for ph in usable[photo_idx:]:
            story += _make_photo_block(ph, ph["caption"], styles)

    story.append(Spacer(1, 60*mm))
    story.append(Paragraph("Glava", styles["final_logo"]))
    story.append(Paragraph(f"Создано в {datetime.now().year}", styles["final_sub"]))
    return story


# ══════════════════════════════════════════════════════════════════
# Public API
# ══════════════════════════════════════════════════════════════════

def build_pdf(
    layout_instructions: Optional[dict],
    book_json_path: str,
    photos_dir: str,
    cover_portrait: Optional[str] = None,
    output_path: Optional[str] = None,
    cover_composition: Optional[dict] = None,
) -> Optional[str]:
    """
    Build PDF from layout_instructions JSON + book data.

    Returns path to generated PDF, or None on failure.
    """
    if not _RL_OK:
        log.error("ReportLab/Pillow not available")
        return None

    _register_fonts()

    try:
        book = _load_book(book_json_path)
    except Exception as ex:
        log.error(f"Cannot load book: {ex}")
        return None

    photos = _load_photos(photos_dir)
    styles = make_styles()
    subject_name = book.get("subject_name", "")

    # Determine output path
    if not output_path:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = str(pathlib.Path(photos_dir).parent / f"book_{ts}.pdf")

    # Build story
    pages = _resolve_pages(layout_instructions or {})
    if pages:
        log.info(f"Building from layout_instructions: {len(pages)} pages")
        story = _build_story_from_layout(pages, book, photos, styles)
    else:
        log.info("No layout_instructions.pages — using fallback builder")
        story = _build_story_fallback(book, photos, styles)
    on_page = _make_page_callbacks(cover_portrait, cover_composition, subject_name)

    try:
        doc = SimpleDocTemplate(
            output_path, pagesize=A5,
            leftMargin=ML, rightMargin=MR, topMargin=MT, bottomMargin=MB,
            title=subject_name,
            author="Glava",
        )
        doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
        size_mb = pathlib.Path(output_path).stat().st_size / 1024 / 1024
        log.info(f"PDF built: {output_path} ({size_mb:.1f} MB)")
        return output_path
    except Exception as ex:
        log.error(f"PDF build failed: {ex}")
        import traceback
        traceback.print_exc()
        return None


# ══════════════════════════════════════════════════════════════════
# CLI entry point (for subprocess use)
# ══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    ap = argparse.ArgumentParser(description="Glava PDF Builder")
    ap.add_argument("--layout-json",  required=True,  help="Path to layout_instructions JSON")
    ap.add_argument("--book-json",    required=True,  help="Path to book_final JSON")
    ap.add_argument("--photos-dir",   required=True,  help="Path to photos dir (with manifest.json)")
    ap.add_argument("--cover",        default=None,   help="Path to cover portrait PNG/webp")
    ap.add_argument("--output",       default=None,   help="Output PDF path")
    args = ap.parse_args()

    layout = None
    if pathlib.Path(args.layout_json).exists():
        layout = json.loads(pathlib.Path(args.layout_json).read_text(encoding="utf-8"))
        layout = layout.get("layout_instructions", layout)

    result = build_pdf(
        layout_instructions=layout,
        book_json_path=args.book_json,
        photos_dir=args.photos_dir,
        cover_portrait=args.cover,
        output_path=args.output,
    )
    if result:
        print(f"OK: {result}")
        sys.exit(0)
    else:
        print("ERROR: PDF build failed", file=sys.stderr)
        sys.exit(1)
