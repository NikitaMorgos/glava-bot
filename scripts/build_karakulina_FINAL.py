#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Glava PDF Builder — финальная версия с обложкой.
Читает:  exports/karakulina_proofreader_report_*.json
         exports/karakulina_photos/manifest.json
         exports/karakulina_cover_nanobana_FINAL.webp  (ink sketch портрет)
         exports/karakulina_stage4_cover_designer_call1_*.json  (композиция)
Пишет:   exports/karakulina_FINAL_<ts>.pdf

Запуск:  python3 scripts/build_karakulina_FINAL.py
"""
import json, pathlib, re, sys
sys.stdout.reconfigure(encoding='utf-8')
from datetime import datetime

ROOT    = pathlib.Path(__file__).resolve().parent.parent
EXPORTS = ROOT / "exports"
PHOTOS_DIR = EXPORTS / "karakulina_photos"

try:
    from reportlab.lib.pagesizes import A5
    from reportlab.lib.units import mm
    pt = 1  # 1 pt = 1 internal unit in ReportLab
    from reportlab.lib.colors import HexColor, white, black, Color
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, PageBreak,
        Image, Table, TableStyle, HRFlowable, KeepTogether,
        BaseDocTemplate, Frame, PageTemplate,
    )
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas as rl_canvas
    from PIL import Image as PILImage
except ImportError as e:
    print(f"[ERROR] {e}\npip install reportlab pillow")
    sys.exit(1)

# ── Fonts ────────────────────────────────────────────────────────
FONT_DIRS = [
    pathlib.Path(__file__).resolve().parent.parent / "fonts",  # project fonts/
    pathlib.Path("/opt/glava/fonts"),                          # Linux server
    pathlib.Path("/usr/share/fonts/truetype/freefont"),        # Linux FreeFont
    pathlib.Path("C:/Windows/Fonts"),                          # Windows fallback
]

def _find_font(names: list[str]) -> pathlib.Path | None:
    for d in FONT_DIRS:
        for n in names:
            p = d / n
            if p.exists():
                return p
    return None

def _register():
    registered = {}
    pairs = [
        ("Serif",        ["PTSerif-Regular.ttf",      "FreeSerif.ttf",     "times.ttf"]),
        ("Serif-Bold",   ["PTSerif-Bold.ttf",          "FreeSerifBold.ttf", "timesbd.ttf"]),
        ("Serif-Italic", ["PTSerif-Italic.ttf",        "FreeSerifItalic.ttf","timesi.ttf"]),
        ("Serif-BoldItalic", ["PTSerif-BoldItalic.ttf","FreeSerifBoldItalic.ttf","timesbi.ttf"]),
        ("Sans",         ["PTSans-Regular.ttf",        "FreeSans.ttf",      "arial.ttf"]),
        ("Sans-Bold",    ["PTSans-Bold.ttf",            "FreeSansBold.ttf",  "arialbd.ttf"]),
        ("Sans-Italic",  ["PTSans-Italic.ttf",          "FreeSansOblique.ttf","ariali.ttf"]),
    ]
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfbase import pdfmetrics
    for alias, candidates in pairs:
        p = _find_font(candidates)
        if p:
            try:
                pdfmetrics.registerFont(TTFont(alias, str(p)))
                registered[alias] = p.name
            except Exception as ex:
                print(f"[FONT] warn: {alias} → {ex}")
    if registered:
        print(f"[FONTS] Зарегистрированы: {', '.join(registered.keys())}")
        # Register family so <b>/<i> tags work
        try:
            from reportlab.pdfbase.ttfonts import TTFontFace
            from reportlab.pdfbase import pdfmetrics
            pdfmetrics.registerFontFamily(
                "Serif",
                normal="Serif", bold="Serif-Bold",
                italic="Serif-Italic", boldItalic="Serif-BoldItalic"
            )
            pdfmetrics.registerFontFamily(
                "Sans",
                normal="Sans", bold="Sans-Bold",
                italic="Sans-Italic", boldItalic="Sans-Italic"
            )
        except Exception:
            pass
    else:
        print("[FONTS] ⚠️  Шрифты не найдены — используются встроенные ReportLab")
    return registered

_FONTS = _register()

# ── Colours ──────────────────────────────────────────────────────
C_BG      = HexColor("#faf6f0")
C_TEXT    = HexColor("#333333")    # v3.14: #333333
C_HEAD    = HexColor("#111111")    # v3.14: #111111
C_ACCENT  = HexColor("#8b7355")
C_MUTED   = HexColor("#b8a88a")
C_RULE    = HexColor("#c4a070")
C_CALLOUT_FG  = HexColor("#333333")   # v3.14: no background, только линии
C_HIST_BG = HexColor("#f0ebe0")    # v3.14: тёплый бежевый, НЕ тёмный (#1a1a2e устарел)
C_HIST_TX = HexColor("#5a4a38")    # v3.14: #5a4a38
C_HIST_BORDER = HexColor("#c4a070") # v3.14: gold left border
C_CAPTION = HexColor("#666666")    # v3.14: #666

# ── Page ─────────────────────────────────────────────────────────
W, H = A5
ML, MR, MT, MB = 18*mm, 14*mm, 16*mm, 20*mm
TW = W - ML - MR

# ── Styles ───────────────────────────────────────────────────────
def make_styles():
    S = {}
    S["body"]     = ParagraphStyle("body",  fontName="Serif",      fontSize=10.5, leading=18,
                                    textColor=C_TEXT, alignment=TA_JUSTIFY, firstLineIndent=12.6, spaceAfter=0)
    # Chapter header: номер + название
    S["ch_num"]   = ParagraphStyle("ch_num", fontName="Sans",      fontSize=54, leading=54,
                                    textColor=HexColor("#e8e0d4"), alignment=TA_LEFT, spaceAfter=2)
    S["ch_title"] = ParagraphStyle("ch_t",  fontName="Serif-Bold", fontSize=14, leading=17,
                                    textColor=C_HEAD, alignment=TA_LEFT, spaceBefore=0, spaceAfter=5)
    S["ch_sub"]   = ParagraphStyle("ch_s",  fontName="Sans",       fontSize=7, leading=9,
                                    textColor=C_MUTED, alignment=TA_LEFT, spaceAfter=8, letterSpacing=1.5)
    # Section header: ## заголовок внутри главы (v3.14: 18pt PT Serif Bold, keepWithNext)
    S["section"]  = ParagraphStyle("section", fontName="Serif-Bold", fontSize=18, leading=22,
                                    textColor=C_HEAD, alignment=TA_LEFT,
                                    spaceBefore=10*mm, spaceAfter=4*mm, keepWithNext=1)
    # Callout: pull-quote (v3.14: PT Serif Italic 13pt, center, no background)
    S["callout"]  = ParagraphStyle("cq",    fontName="Serif-Italic", fontSize=13, leading=20,
                                    textColor=HexColor("#333333"), alignment=TA_CENTER, spaceAfter=10)
    S["callout_attr"] = ParagraphStyle("cqa", fontName="Sans",       fontSize=7, leading=10,
                                    textColor=HexColor("#999999"), alignment=TA_CENTER, letterSpacing=2)
    # Caption: PT Serif Italic 8pt (v3.14)
    S["caption"]  = ParagraphStyle("cap",   fontName="Serif-Italic", fontSize=8, leading=11,
                                    textColor=C_CAPTION, alignment=TA_LEFT, spaceAfter=6)
    # Historical block: label + text
    S["hist_lbl"] = ParagraphStyle("hlbl",  fontName="Sans-Bold",   fontSize=6.5, leading=10,
                                    textColor=C_RULE, alignment=TA_LEFT,
                                    leftIndent=14, spaceAfter=5, letterSpacing=2.5)
    S["hist"]     = ParagraphStyle("hist",  fontName="Serif-Italic", fontSize=9, leading=14,
                                    textColor=C_HIST_TX, alignment=TA_JUSTIFY,
                                    leftIndent=14, rightIndent=12)
    # TOC
    S["toc_h"]    = ParagraphStyle("toch",  fontName="Serif-Bold", fontSize=16, leading=20,
                                    textColor=C_HEAD, alignment=TA_LEFT, spaceAfter=10)
    S["toc_ch"]   = ParagraphStyle("tocch", fontName="Serif",      fontSize=10, leading=15,
                                    textColor=C_TEXT, alignment=TA_LEFT, spaceAfter=4)
    # Body without first-line indent (after ## or photo)
    S["body_ni"]  = ParagraphStyle("body_ni", parent=S["body"], firstLineIndent=0)
    return S

# ── Cover page (drawn on canvas) ─────────────────────────────────
def draw_cover(c, doc, portrait_path: pathlib.Path, comp: dict):
    """Рисует обложку напрямую на canvas."""
    c.saveState()
    # Background
    c.setFillColor(HexColor(comp.get("background_color", "#faf6f0")))
    c.rect(0, 0, W, H, fill=1, stroke=0)

    # Portrait (ink sketch) — центр, верхние 55%
    if portrait_path and portrait_path.exists():
        try:
            # Convert webp → temp PNG file (drawImage doesn't accept BytesIO in older RL)
            import tempfile, os
            img = PILImage.open(str(portrait_path)).convert("RGBA")
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            img.save(tmp.name, format="PNG")
            tmp.close()

            # Portrait zone: y from 25% to 80% of page height
            zone_top    = H * 0.25
            zone_bottom = H * 0.80
            zone_h      = zone_bottom - zone_top
            zone_w      = W * 0.75

            iw, ih = img.size
            scale = min(zone_w / iw, zone_h / ih)
            pw, ph = iw * scale, ih * scale
            px = (W - pw) / 2
            py = zone_top + (zone_h - ph) / 2

            c.drawImage(tmp.name, px, py, pw, ph, mask="auto")
            os.unlink(tmp.name)
        except Exception as ex:
            print(f"[WARN] cover portrait: {ex}")

    typ = comp.get("typography", {})
    accent = comp.get("accent_color", "#c4a070")

    # ─── Zone A: верхние 25% (0–52.5mm от верха) ───────────────────
    # Line 1: над фамилией (line_top_A)
    zone_a_top = H - 10*mm
    c.setStrokeColor(HexColor(accent))
    c.setLineWidth(0.5)
    c.line(ML, zone_a_top, W - MR, zone_a_top)

    # Surname (27pt, UPPERCASE, #3d2e1f)
    surname_cfg = typ.get("surname", {})
    surname = surname_cfg.get("text", "КАРАКУЛИНА")
    c.setFont("Serif-Bold", 27)
    c.setFillColor(HexColor(comp.get("text_primary_color", "#3d2e1f")))
    y_surname = H - 18*mm
    c.drawCentredString(W / 2, y_surname, surname)

    # First name (14pt italic, #8b7355)
    fn_cfg = typ.get("first_name", {})
    first_name = fn_cfg.get("text", "Валентина Ивановна")
    c.setFont("Serif-Italic", 14)
    c.setFillColor(HexColor(comp.get("text_secondary_color", "#8b7355")))
    y_fname = y_surname - 18
    c.drawCentredString(W / 2, y_fname, first_name)

    # Line 2: под именем-отчеством (line_bottom_A)
    c.setStrokeColor(HexColor(accent))
    c.setLineWidth(0.5)
    y_line2 = y_fname - 8
    c.line(ML, y_line2, W - MR, y_line2)

    # Bottom zone: years (Zone C: 80-100%)
    dec = comp.get("decorative_elements", {})
    years_cfg = dec.get("years_line", {})
    # v2.5: used years_line.text (full string) preferred, fallback to text_left/text_right
    years_text = years_cfg.get("text") or (
        years_cfg.get("text_left", "1920") + " — " + (years_cfg.get("text_right") or "2005")
    )

    # Zone C top line (над годами, y=80% from bottom = 20% from top)
    zone_c_y = H * 0.20   # y from bottom = 20% of H
    c.setStrokeColor(HexColor(accent))
    c.setLineWidth(0.5)
    c.line(ML, zone_c_y, W - MR, zone_c_y)

    c.setFont("Sans", 9)
    c.setFillColor(HexColor(comp.get("text_muted_color", "#b8a88a")))
    c.drawCentredString(W / 2, zone_c_y - 11, years_text)

    # Subtitle (under years)
    sub_cfg = typ.get("subtitle", {})
    subtitle = sub_cfg.get("text", "История жизни, рассказанная близкими")
    c.setFont("Sans", 6)
    c.drawCentredString(W / 2, zone_c_y - 20, subtitle.upper())

    c.restoreState()


# ── Helpers ──────────────────────────────────────────────────────
def img_block(path: pathlib.Path, caption: str, styles, max_h=70*mm):
    if not path.exists():
        return []
    try:
        img = PILImage.open(str(path))
        iw, ih = img.size
        scale = min(TW / iw, max_h / ih)
        w, h = iw * scale, ih * scale
        im = Image(str(path), width=w, height=h)
        items = [Spacer(1, 4*mm), im]
        if caption:
            items.append(Paragraph(caption, styles["caption"]))
        items.append(Spacer(1, 4*mm))
        return items
    except Exception as ex:
        print(f"[WARN] image {path.name}: {ex}")
        return []


def callout_box(text: str, styles):
    """Pull-quote callout (v3.14): линии сверху/снизу, без фона, PT Serif Italic 13pt, атрибуция."""
    content = [
        Paragraph(f"\u00ab{text}\u00bb", styles["callout"]),
        Paragraph("\u2014 \u0418\u0417 \u0412\u041e\u0421\u041f\u041e\u041c\u0418\u041d\u0410\u041d\u0418\u0419 \u0421\u0415\u041c\u042c\u0418", styles["callout_attr"]),
    ]
    t = Table([[content]], colWidths=[TW])
    t.setStyle(TableStyle([
        ("TOPPADDING",    (0, 0), (-1, -1), 16),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ("LINEABOVE",     (0, 0), (-1,  0), 0.5, HexColor("#c4a070")),
        ("LINEBELOW",     (0,-1), (-1, -1), 0.5, HexColor("#c4a070")),
    ]))
    return KeepTogether([Spacer(1, 5*mm), t, Spacer(1, 5*mm)])


def hist_block(text: str, styles):
    """Historical context block (v3.14): тёплый бежевый фон #f0ebe0, золотая левая черта."""
    label_para = Paragraph("КОНТЕКСТ ЭПОХИ", styles["hist_lbl"])
    text_para  = Paragraph(text, styles["hist"])
    t = Table([[label_para], [text_para]], colWidths=[TW])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), C_HIST_BG),
        ("TOPPADDING",    (0, 0), (0,  0),  10),
        ("BOTTOMPADDING", (0,-1), (-1,-1),  10),
        ("TOPPADDING",    (0, 1), (-1, -1),  0),
        ("LEFTPADDING",   (0, 0), (-1, -1), 12),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 12),
        ("LINEBEFORE",    (0, 0), (0, -1),  2, C_HIST_BORDER),
    ]))
    return KeepTogether([Spacer(1, 4*mm), t, Spacer(1, 4*mm)])


def parse_paragraphs(md: str, styles) -> list:
    out = []
    lines = md.split("\n")
    after_section = False  # убрать firstLineIndent после ## заголовка
    for line in lines:
        line = line.strip()
        if not line:
            out.append(Spacer(1, 2*mm))
            after_section = False
            continue
        if line.startswith("## "):
            # Section header: PT Serif Bold 18pt, keepWithNext (v3.14)
            out.append(Paragraph(line[3:], styles["section"]))
            after_section = True
        elif line.startswith("# "):
            out.append(Paragraph(line[2:], styles["ch_title"]))
            after_section = True
        else:
            # Escape XML-special chars
            line = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            # ***жирный курсив*** → historical context italic
            line = re.sub(r"\*\*\*(.+?)\*\*\*", r"<i>\1</i>", line)
            # **жирный** → callout marker → просто bold (pull-quote в callouts[])
            line = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", line)
            # _italic_
            line = re.sub(r"_(.+?)_", r"<i>\1</i>", line)
            style = styles["body_ni"] if after_section else styles["body"]
            out.append(Paragraph(line, style))
            after_section = False
    return out


# ── Load data ─────────────────────────────────────────────────────
def load_book():
    # Приоритет 1: одобренный чекпоинт (единственный источник истины)
    try:
        sys.path.insert(0, str(ROOT))
        from checkpoint_utils import load_approved
        data = load_approved("karakulina", "proofreader")
        print("[BOOK] ✅ Загружен из одобренного чекпоинта: karakulina/proofreader")
        return data.get("book_final", data)
    except Exception as e:
        print(f"[BOOK] ⚠️  Чекпоинт недоступен ({e}), ищу по glob...")

    # Fallback: последний proofreader_report в exports (старое поведение)
    candidates = sorted(EXPORTS.glob("karakulina_proofreader_report_*.json"))
    if not candidates:
        sys.exit(
            "[ERROR] Нет ни одобренного чекпоинта, ни karakulina_proofreader_report_*.json\n"
            "Запустите пайплайн или: python scripts/checkpoint_save.py save karakulina proofreader <file> --approve"
        )
    path = candidates[-1]
    print(f"[BOOK] (fallback) {path.name}")
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("book_final", data)


def load_photos():
    manifest = PHOTOS_DIR / "manifest.json"
    if not manifest.exists():
        return []
    items = json.loads(manifest.read_text(encoding="utf-8"))
    photos = []
    for e in sorted(items, key=lambda x: x["index"]):
        if e.get("exclude"):
            continue
        p = PHOTOS_DIR / e["filename"]
        if p.exists():
            photos.append({"path": p, "caption": e.get("caption", ""), "index": e["index"]})
    print(f"[PHOTOS] {len(photos)} фото")
    return photos


def load_cover_data():
    """Загружает портрет обложки и композицию от Cover Designer."""
    portrait_path = EXPORTS / "karakulina_cover_nanobana_FINAL.webp"

    # Latest call1 JSON
    candidates = sorted(EXPORTS.glob("karakulina_stage4_cover_designer_call1_*.json"))
    comp = {}
    if candidates:
        raw = json.loads(candidates[-1].read_text(encoding="utf-8"))
        comp = raw.get("cover_composition", {})
        print(f"[COVER] Композиция из: {candidates[-1].name}")
    else:
        print("[COVER] cover_designer_call1 не найден — используем дефолты")

    # Fill defaults
    if not comp.get("typography"):
        comp["typography"] = {
            "surname":    {"text": "КАРАКУЛИНА"},
            "first_name": {"text": "Валентина Ивановна"},
            "subtitle":   {"text": "История жизни, рассказанная родными"},
        }
    if not comp.get("decorative_elements"):
        comp["decorative_elements"] = {
            "years_line": {"text_left": "1920", "text_right": "2005"}
        }

    print(f"[COVER] Портрет: {portrait_path.name} {'✅' if portrait_path.exists() else '❌ не найден'}")
    return portrait_path, comp


# ── PDF build ─────────────────────────────────────────────────────
def build_pdf(book, photos, cover_portrait, cover_comp):
    styles = make_styles()
    chapters  = book.get("chapters", [])
    callouts  = {c["id"]: c for c in book.get("callouts", [])}
    hist_map  = {}
    for h in book.get("historical_notes", book.get("historical_inserts", [])):
        hist_map.setdefault(h.get("chapter_id", ""), []).append(h["text"])

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = EXPORTS / f"karakulina_FINAL_{ts}.pdf"

    # ─── Page callbacks ───────────────────────────────────────────
    cover_drawn = [False]

    def on_page(c, doc):
        pn = doc.page
        # Cover page
        if pn == 1 and not cover_drawn[0]:
            draw_cover(c, doc, cover_portrait, cover_comp)
            cover_drawn[0] = True
            return
        # Background on all pages
        c.saveState()
        c.setFillColor(C_BG)
        c.rect(0, 0, W, H, fill=1, stroke=0)
        # Header rule
        if pn > 2:
            c.setStrokeColor(HexColor("#e8e0d4"))
            c.setLineWidth(0.4)
            c.line(ML, H - MT + 4*mm, W - MR, H - MT + 4*mm)
            # Page number
            c.setFont("Sans", 7)
            c.setFillColor(C_MUTED)
            c.drawCentredString(W / 2, MB - 6*mm, str(pn - 2))  # -2 for cover+blank
        c.restoreState()

    # ─── Story ────────────────────────────────────────────────────
    story = []

    # Page 1: cover (drawn via on_page callback — just a minimal placeholder to trigger page)
    story.append(Spacer(1, 1*mm))
    story.append(PageBreak())

    # Page 2: blank (форзац)
    story.append(Spacer(1, 1*mm))
    story.append(PageBreak())

    # Page 3: TOC
    story.append(Spacer(1, 8*mm))
    story.append(Paragraph("Содержание", styles["toc_h"]))
    story.append(HRFlowable(width=TW, thickness=0.5, color=C_RULE, spaceAfter=6))
    for i, ch in enumerate(chapters, 1):
        story.append(Paragraph(f"{i}. {ch['title']}", styles["toc_ch"]))
    story.append(PageBreak())

    # Distribute photos: skip index 1 (portrait), use rest
    usable = [p for p in photos if p["index"] > 1]
    per_ch = max(1, len(usable) // max(len(chapters), 1)) if usable else 0
    photo_idx = 0

    # callout → chapter mapping
    ch_callouts = {}
    for cid, cobj in callouts.items():
        ch_id = cobj.get("chapter_id", "")
        ch_callouts.setdefault(ch_id, []).append(cobj["text"])

    # Chapters
    for num, ch in enumerate(chapters, 1):
        ch_id = ch["id"]

        # Chapter header: номер (54pt, #e8e0d4) + название (14pt) + линия 32mm (v3.14)
        story.append(Spacer(1, 8*mm))
        story.append(Paragraph(str(num), styles["ch_num"]))
        story.append(Paragraph(ch["title"], styles["ch_title"]))
        story.append(HRFlowable(width=32*mm, thickness=1.5, color=C_HEAD,
                                hAlign="LEFT", spaceAfter=10))

        # Chapter content
        story += parse_paragraphs(ch.get("content", ""), styles)

        # Historical blocks for this chapter
        for ht in hist_map.get(ch_id, []):
            story.append(hist_block(ht, styles))

        # Callouts
        for ct in ch_callouts.get(ch_id, []):
            story.append(callout_box(ct, styles))

        # Photos
        for _ in range(per_ch):
            if photo_idx < len(usable):
                ph = usable[photo_idx]
                story += img_block(ph["path"], ph["caption"], styles)
                photo_idx += 1

        story.append(PageBreak())

    # Remaining photos
    remaining = usable[photo_idx:]
    if remaining:
        story.append(Paragraph("Фотографии", styles["ch_title"]))
        story.append(HRFlowable(width=TW, thickness=0.5, color=C_RULE, spaceAfter=6))
        for ph in remaining:
            story += img_block(ph["path"], ph["caption"], styles)

    # Final page
    story.append(PageBreak())
    story.append(Spacer(1, 60*mm))
    story.append(Paragraph("Glava", ParagraphStyle(
        "glava_end", fontName="Sans", fontSize=10, leading=14,
        textColor=C_RULE, alignment=TA_CENTER)))
    story.append(Paragraph(f"Создано в {datetime.now().year}", ParagraphStyle(
        "yr_end", fontName="Sans", fontSize=7, leading=10,
        textColor=C_MUTED, alignment=TA_CENTER)))

    # ─── Build ────────────────────────────────────────────────────
    doc = SimpleDocTemplate(
        str(out), pagesize=A5,
        leftMargin=ML, rightMargin=MR, topMargin=MT, bottomMargin=MB,
        title=f"Каракулина Валентина Ивановна — История жизни",
        author="Glava",
    )
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return out


def main():
    book          = load_book()
    photos        = load_photos()
    portrait, comp = load_cover_data()

    print(f"\n[BUILD] Глав: {len(book.get('chapters', []))} | "
          f"Callouts: {len(book.get('callouts', []))} | "
          f"Фото: {len(photos)}")

    out = build_pdf(book, photos, portrait, comp)
    size_mb = out.stat().st_size / 1024 / 1024
    print(f"\n✅ PDF готов: {out.name} ({size_mb:.1f} МБ)")


if __name__ == "__main__":
    main()
