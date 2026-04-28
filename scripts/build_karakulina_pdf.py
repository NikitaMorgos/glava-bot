#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Glava PDF Builder — собирает PDF из данных пайплайна.
Читает:  exports/karakulina_proofreader_report_*.json  — текст книги
         exports/karakulina_photos/manifest.json       — фотографии
Пишет:   exports/karakulina_book_STAGE4_<ts>.pdf

Запуск:  python3 scripts/build_karakulina_pdf.py
"""

import json
import pathlib
import re
import sys
from datetime import datetime

ROOT = pathlib.Path(__file__).resolve().parent.parent
EXPORTS = ROOT / "exports"
PHOTOS_DIR = EXPORTS / "karakulina_photos"

# ── ReportLab ────────────────────────────────────────────────────
try:
    from reportlab.lib.pagesizes import A5
    from reportlab.lib.units import mm
    from reportlab.lib.colors import HexColor, black, white
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, PageBreak,
        Image, Table, TableStyle, HRFlowable, KeepTogether,
    )
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
except ImportError:
    print("[ERROR] pip install reportlab pillow")
    sys.exit(1)

# ── Fonts ─────────────────────────────────────────────────────────
FONT_PATHS = {
    "Serif":        "/usr/share/fonts/truetype/freefont/FreeSerif.ttf",
    "Serif-Bold":   "/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf",
    "Serif-Italic": "/usr/share/fonts/truetype/freefont/FreeSerifItalic.ttf",
    "Sans":         "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    "Sans-Bold":    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    "Mono":         "/usr/share/fonts/truetype/freefont/FreeMono.ttf",
}

for name, path in FONT_PATHS.items():
    if pathlib.Path(path).exists():
        pdfmetrics.registerFont(TTFont(name, path))
    else:
        print(f"[WARN] Font not found: {path}")

# ── Colours ───────────────────────────────────────────────────────
C_BG        = HexColor("#faf6f0")   # page background
C_TEXT      = HexColor("#2d2318")   # main text
C_HEADING   = HexColor("#3d2e1f")   # chapter titles
C_ACCENT    = HexColor("#8b5e3c")   # section headers
C_RULE      = HexColor("#c4a070")   # decorative lines
C_CALLOUT   = HexColor("#f5ede0")   # callout bg
C_HIST      = HexColor("#e8f0e8")   # historical note bg
C_CAPTION   = HexColor("#6b5a45")   # photo caption

# ── Page setup ────────────────────────────────────────────────────
W, H = A5  # 148 × 210 mm
MARGIN_L = 18 * mm
MARGIN_R = 14 * mm
MARGIN_T = 16 * mm
MARGIN_B = 20 * mm
TEXT_W = W - MARGIN_L - MARGIN_R

# ── Styles ────────────────────────────────────────────────────────
def make_styles():
    S = {}
    S["body"] = ParagraphStyle(
        "body",
        fontName="Serif", fontSize=9.5, leading=14,
        textColor=C_TEXT, alignment=TA_JUSTIFY,
        firstLineIndent=12, spaceAfter=4,
    )
    S["body_first"] = ParagraphStyle(
        "body_first",
        parent=S["body"], firstLineIndent=0,
    )
    S["ch_title"] = ParagraphStyle(
        "ch_title",
        fontName="Serif-Bold", fontSize=16, leading=20,
        textColor=C_HEADING, alignment=TA_LEFT,
        spaceBefore=6, spaceAfter=8,
    )
    S["section"] = ParagraphStyle(
        "section",
        fontName="Serif-Bold", fontSize=11, leading=14,
        textColor=C_ACCENT, alignment=TA_LEFT,
        spaceBefore=10, spaceAfter=4,
    )
    S["callout"] = ParagraphStyle(
        "callout",
        fontName="Serif-Italic", fontSize=11, leading=16,
        textColor=C_HEADING, alignment=TA_CENTER,
        spaceBefore=4, spaceAfter=4,
        leftIndent=10, rightIndent=10,
    )
    S["hist_note"] = ParagraphStyle(
        "hist_note",
        fontName="Serif-Italic", fontSize=8.5, leading=12,
        textColor=HexColor("#3a5a3a"), alignment=TA_JUSTIFY,
        leftIndent=6, rightIndent=6, spaceBefore=2, spaceAfter=2,
    )
    S["caption"] = ParagraphStyle(
        "caption",
        fontName="Sans", fontSize=7.5, leading=10,
        textColor=C_CAPTION, alignment=TA_CENTER,
        spaceAfter=8,
    )
    S["page_num"] = ParagraphStyle(
        "page_num",
        fontName="Sans", fontSize=8, textColor=C_CAPTION,
        alignment=TA_CENTER,
    )
    S["toc_ch"] = ParagraphStyle(
        "toc_ch",
        fontName="Serif-Bold", fontSize=10, leading=14,
        textColor=C_HEADING, spaceBefore=4, spaceAfter=2,
    )
    S["toc_title"] = ParagraphStyle(
        "toc_title",
        fontName="Serif-Bold", fontSize=14, leading=18,
        textColor=C_HEADING, alignment=TA_CENTER,
        spaceBefore=0, spaceAfter=12,
    )
    return S

# ── Markdown → ReportLab paragraphs ──────────────────────────────
def md_inline(text: str) -> str:
    """Convert inline markdown to ReportLab XML."""
    # Bold+italic: ***text*** or ___text___
    text = re.sub(r'\*\*\*(.*?)\*\*\*', r'<b><i>\1</i></b>', text)
    # Bold: **text**
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    # Italic: *text* or _text_
    text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
    # Escape bare ampersands that aren't already entities
    text = re.sub(r'&(?!amp;|lt;|gt;|quot;|#)', '&amp;', text)
    return text

def parse_chapter_content(content: str, styles: dict) -> list:
    """Parse markdown chapter content into ReportLab flowables."""
    flowables = []
    lines = content.split("\n")
    i = 0
    first_para = True

    while i < len(lines):
        line = lines[i].rstrip()

        if not line:
            i += 1
            continue

        # ## Section heading
        if line.startswith("## "):
            heading = line[3:].strip()
            flowables.append(Spacer(1, 2 * mm))
            flowables.append(Paragraph(md_inline(heading), styles["section"]))
            flowables.append(HRFlowable(
                width=TEXT_W * 0.3, thickness=0.5,
                color=C_RULE, spaceAfter=3,
            ))
            first_para = True
            i += 1
            continue

        # ### Sub-section
        if line.startswith("### "):
            heading = line[4:].strip()
            sub_style = ParagraphStyle(
                "sub", parent=styles["section"], fontSize=10,
                textColor=C_ACCENT,
            )
            flowables.append(Paragraph(md_inline(heading), sub_style))
            first_para = True
            i += 1
            continue

        # ***historical note*** as standalone paragraph
        hist_match = re.match(r'^\*\*\*(.*?)\*\*\*$', line)
        if hist_match:
            note_text = hist_match.group(1)
            table_data = [[Paragraph(md_inline(note_text), styles["hist_note"])]]
            t = Table(table_data, colWidths=[TEXT_W - 8 * mm])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), C_HIST),
                ("LEFTPADDING",  (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING",   (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
                ("BOX", (0, 0), (-1, -1), 0.5, HexColor("#6a9a6a")),
                ("ROUNDEDCORNERS", [3]),
            ]))
            flowables.append(Spacer(1, 3 * mm))
            flowables.append(t)
            flowables.append(Spacer(1, 3 * mm))
            first_para = True
            i += 1
            continue

        # Regular paragraph
        style = styles["body_first"] if first_para else styles["body"]
        first_para = False
        flowables.append(Paragraph(md_inline(line), style))
        i += 1

    return flowables

def make_callout_box(text: str, styles: dict) -> Table:
    """Pull-quote callout box."""
    para = Paragraph(f'\u201c{md_inline(text)}\u201d', styles["callout"])
    t = Table([[para]], colWidths=[TEXT_W - 12 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_CALLOUT),
        ("LEFTPADDING",  (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING",   (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 8),
        ("LINEABOVE",  (0, 0), (-1, 0), 1.5, C_RULE),
        ("LINEBELOW",  (0, -1), (-1, -1), 1.5, C_RULE),
    ]))
    return t

def make_photo_block(photo_path: str, caption: str, styles: dict, max_h: float = 70 * mm) -> list:
    """Photo + caption flowable block."""
    p = pathlib.Path(photo_path)
    if not p.exists():
        return []
    try:
        from PIL import Image as PILImage
        with PILImage.open(p) as img:
            pw, ph = img.size
        ratio = pw / ph
        img_w = min(TEXT_W, max_h * ratio)
        img_h = img_w / ratio
        img_flowable = Image(str(p), width=img_w, height=img_h)
        img_flowable.hAlign = "CENTER"
        items = [
            Spacer(1, 4 * mm),
            img_flowable,
        ]
        if caption:
            items.append(Paragraph(caption, styles["caption"]))
        items.append(Spacer(1, 2 * mm))
        return items
    except Exception as e:
        print(f"[WARN] Photo error {p.name}: {e}")
        return []

# ── Load data ─────────────────────────────────────────────────────
def load_book():
    reports = sorted(EXPORTS.glob("karakulina_proofreader_report_*.json"))
    if not reports:
        print("[ERROR] No proofreader report found")
        sys.exit(1)
    src = reports[-1]
    print(f"[INPUT] Book: {src.name}")
    return json.loads(src.read_text(encoding="utf-8"))

def load_photos():
    manifest_path = PHOTOS_DIR / "manifest.json"
    if not manifest_path.exists():
        print("[WARN] No photo manifest")
        return []
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    photos = []
    for e in sorted(manifest, key=lambda x: x["index"]):
        if e.get("exclude"):
            continue
        fpath = PHOTOS_DIR / e["filename"]
        if fpath.exists():
            photos.append({
                "id":      f"photo_{e['index']:03d}",
                "path":    str(fpath),
                "caption": e.get("caption", ""),
                "index":   e["index"],
            })
    print(f"[INPUT] Photos: {len(photos)}")
    return photos

# ── Page header/footer ────────────────────────────────────────────
def on_page(canvas, doc):
    canvas.saveState()
    # Top rule
    canvas.setStrokeColor(C_RULE)
    canvas.setLineWidth(0.4)
    canvas.line(MARGIN_L, H - MARGIN_T + 4 * mm, W - MARGIN_R, H - MARGIN_T + 4 * mm)
    # Bottom rule + page number
    canvas.line(MARGIN_L, MARGIN_B - 6 * mm, W - MARGIN_R, MARGIN_B - 6 * mm)
    canvas.setFont("Sans", 8)
    canvas.setFillColor(C_CAPTION)
    canvas.drawCentredString(W / 2, MARGIN_B - 10 * mm, str(doc.page))
    canvas.restoreState()

# ── Build story ────────────────────────────────────────────────────
def build_story(book: dict, photos: list, styles: dict) -> list:
    story = []
    chapters = book.get("chapters", [])
    callouts = {c["id"]: c["text"] for c in book.get("callouts", [])}
    hist_inserts = {h["chapter_id"]: h for h in book.get("historical_inserts", [])} if "historical_inserts" in book else {}

    # Distribute photos across chapters
    # Skip first photo (index 1 = portrait, keep for potential cover) — use from index 2
    usable_photos = [p for p in photos if p["index"] > 1]
    photos_per_chapter = max(1, len(usable_photos) // max(len(chapters), 1))

    # ── Title page ────────────────────────────────────────────────
    story.append(Spacer(1, 20 * mm))
    story.append(Paragraph("КАРАКУЛИНА", ParagraphStyle(
        "main_title",
        fontName="Serif-Bold", fontSize=28, leading=32,
        textColor=C_HEADING, alignment=TA_CENTER,
        letterSpacing=6,
    )))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph("Валентина Ивановна", ParagraphStyle(
        "sub_title",
        fontName="Serif-Italic", fontSize=14, leading=18,
        textColor=C_ACCENT, alignment=TA_CENTER,
    )))
    story.append(Spacer(1, 4 * mm))
    story.append(HRFlowable(
        width=TEXT_W * 0.5, thickness=1, color=C_RULE, hAlign="CENTER",
        spaceBefore=2, spaceAfter=2,
    ))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph("1920 — 2005", ParagraphStyle(
        "years",
        fontName="Sans", fontSize=10, leading=14,
        textColor=C_CAPTION, alignment=TA_CENTER,
    )))
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph("История жизни, рассказанная родными", ParagraphStyle(
        "subtitle_small",
        fontName="Sans", fontSize=8, leading=12,
        textColor=C_CAPTION, alignment=TA_CENTER,
        letterSpacing=1.5,
    )))

    # Add portrait photo if available
    if photos:
        portrait = photos[0]  # first photo = portrait
        story += make_photo_block(portrait["path"], portrait["caption"], styles, max_h=80 * mm)

    story.append(PageBreak())

    # ── Table of Contents ─────────────────────────────────────────
    story.append(Paragraph("Содержание", styles["toc_title"]))
    story.append(HRFlowable(width=TEXT_W, thickness=0.5, color=C_RULE, spaceAfter=6))
    for i, ch in enumerate(chapters, 1):
        story.append(Paragraph(f"{i}. {ch['title']}", styles["toc_ch"]))
    story.append(PageBreak())

    # ── Chapters ──────────────────────────────────────────────────
    chapter_callouts = {}
    for cid, text in callouts.items():
        # Find which chapter this callout belongs to
        ch_match = next((c for c in book.get("callouts", []) if c["id"] == cid), None)
        if ch_match:
            ch_id = ch_match.get("chapter_id", "")
            chapter_callouts.setdefault(ch_id, []).append(text)

    photo_idx = 1  # start after portrait

    for ch_num, chapter in enumerate(chapters, 1):
        ch_id = chapter["id"]
        title = chapter["title"]
        content = chapter.get("content", "")

        # Chapter title
        story.append(KeepTogether([
            HRFlowable(width=TEXT_W * 0.15, thickness=2, color=C_RULE, spaceAfter=4),
            Paragraph(f"{ch_num}. {title}", styles["ch_title"]),
        ]))

        # Chapter content
        story += parse_chapter_content(content, styles)

        # Callout(s) for this chapter
        for callout_text in chapter_callouts.get(ch_id, []):
            story.append(Spacer(1, 4 * mm))
            story.append(make_callout_box(callout_text, styles))
            story.append(Spacer(1, 4 * mm))

        # Insert photos for this chapter
        for _ in range(photos_per_chapter):
            if photo_idx < len(photos):
                ph = photos[photo_idx]
                story += make_photo_block(ph["path"], ph["caption"], styles)
                photo_idx += 1

        story.append(PageBreak())

    # Remaining photos on a final spread
    remaining = photos[photo_idx:]
    if remaining:
        story.append(Paragraph("Фотографии", styles["ch_title"]))
        story.append(HRFlowable(width=TEXT_W, thickness=0.5, color=C_RULE, spaceAfter=6))
        for ph in remaining:
            story += make_photo_block(ph["path"], ph["caption"], styles)

    return story

# ── Main ──────────────────────────────────────────────────────────
def main():
    book = load_book()
    photos = load_photos()
    styles = make_styles()
    story = build_story(book, photos, styles)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = EXPORTS / f"karakulina_book_STAGE4_{ts}.pdf"

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=A5,
        leftMargin=MARGIN_L,
        rightMargin=MARGIN_R,
        topMargin=MARGIN_T,
        bottomMargin=MARGIN_B,
        title="Каракулина Валентина Ивановна",
        author="Glava",
    )

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)

    size = out_path.stat().st_size
    print(f"\n[OK] PDF: {out_path.name} ({size:,} bytes)")
    return str(out_path)

if __name__ == "__main__":
    main()
