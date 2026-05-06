#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Renderer — строит PDF из layout_result.json (pages[] формат Верстальщика v3).

Архитектура: Вариант B (JSON → детерминированный рендерер).
Верстальщик возвращает структурированный pages[], этот скрипт рендерит его через ReportLab.

Вход:
  --layout exports/karakulina_stage4_layout_iter*.json  (pages[] от LLM)
  --book   exports/karakulina_book_FINAL_*.json          (book_FINAL с paragraphs[] — для lookup по ID)
  --photos-dir exports/karakulina_photos/               (фотографии + manifest.json)
  --portrait exports/karakulina_stage4_cover_portrait_*.webp  (опционально)
  --output exports/karakulina_rendered_<ts>.pdf

Начиная с v3.19 Layout Designer ссылается на абзацы по {chapter_id, paragraph_id}
вместо копирования текста. Рендерер восстанавливает текст из book_FINAL.json.
Обратная совместимость: если paragraph-элемент содержит поле "text" — используется
напрямую (legacy-формат).
"""
import argparse
import copy
import json
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── ReportLab ─────────────────────────────────────────────────────────────────
try:
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.lib.pagesizes import A5
    from reportlab.lib.units import mm
    from reportlab.lib.colors import HexColor, white, black
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY, TA_RIGHT
    from reportlab.platypus import (
        Paragraph, Image as RLImage, Table, TableStyle, Spacer, KeepTogether,
        Flowable, PageBreak,
    )
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
except ImportError:
    print("[ERROR] pip install reportlab pillow")
    sys.exit(1)

# ── Font registration ─────────────────────────────────────────────────────────
# PT Serif + PT Sans — установлены на Linux (paratype), для Windows можно скачать
# в fonts/ директорию проекта.
_FONT_CANDIDATES = [
    # (internal_name, linux_path, win_rel_path)
    ("PTSerif",        "/usr/share/fonts/truetype/paratype/PTF55F.ttf",  "fonts/PTSerif-Regular.ttf"),
    ("PTSerif-Bold",   "/usr/share/fonts/truetype/paratype/PTF75F.ttf",  "fonts/PTSerif-Bold.ttf"),
    ("PTSerif-Italic", "/usr/share/fonts/truetype/paratype/PTF56F.ttf",  "fonts/PTSerif-Italic.ttf"),
    ("PTSans",         "/usr/share/fonts/truetype/paratype/PTS55F.ttf",  "fonts/PTSans-Regular.ttf"),
    ("PTSans-Bold",    "/usr/share/fonts/truetype/paratype/PTS75F.ttf",  "fonts/PTSans-Bold.ttf"),
    ("PTSans-Italic",  "/usr/share/fonts/truetype/paratype/PTS56F.ttf",  "fonts/PTSans-Italic.ttf"),
    # DejaVu как запасные (обычно есть и там и там)
    ("DejaVuSerif",        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",         "fonts/DejaVuSerif.ttf"),
    ("DejaVuSerif-Bold",   "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",    "fonts/DejaVuSerif-Bold.ttf"),
    ("DejaVuSans",         "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",          "fonts/DejaVuSans.ttf"),
    ("DejaVuSans-Bold",    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",     "fonts/DejaVuSans-Bold.ttf"),
]
_REGISTERED: set[str] = set()


def _register_fonts():
    for name, linux_path, win_rel in _FONT_CANDIDATES:
        # Попробуем linux-путь, потом fonts/ рядом с корнем проекта
        for candidate in (linux_path, str(ROOT / win_rel)):
            if Path(candidate).exists():
                try:
                    pdfmetrics.registerFont(TTFont(name, candidate))
                    _REGISTERED.add(name)
                    break
                except Exception:
                    pass


_register_fonts()


def _pick(preferred: str, fallback: str) -> str:
    """Вернуть зарегистрированный шрифт или PDF built-in fallback."""
    if preferred in _REGISTERED:
        return preferred
    return fallback


# Финальные имена шрифтов для рендерера
BODY_FONT         = _pick("PTSerif",        _pick("DejaVuSerif",      "Times-Roman"))
BODY_BOLD_FONT    = _pick("PTSerif-Bold",   _pick("DejaVuSerif-Bold", "Times-Bold"))
BODY_ITALIC_FONT  = _pick("PTSerif-Italic", _pick("DejaVuSerif",      "Times-Italic"))
SANS_FONT         = _pick("PTSans",         _pick("DejaVuSans",       "Helvetica"))
SANS_BOLD_FONT    = _pick("PTSans-Bold",    _pick("DejaVuSans-Bold",  "Helvetica-Bold"))
SANS_ITALIC_FONT  = _pick("PTSans-Italic",  _pick("DejaVuSans",       "Helvetica-Oblique"))

# Удобные алиасы для Platypus Story
BODY_FONT_ITALIC  = BODY_ITALIC_FONT
SANS_FONT_BOLD    = SANS_BOLD_FONT


# Маппинг дизайн-шрифтов (из Cover Designer v2.2 / Layout Designer v3.2)
# к зарегистрированным TTF. Позволяет LLM указывать "Playfair Display",
# а рендерер автоматически переводит на PT Serif/PT Sans.
_FONT_ALIASES: dict[str, str] = {
    # Playfair Display → PT Serif Bold (книжная засечковая)
    "playfair display":     BODY_BOLD_FONT,
    "playfair":             BODY_BOLD_FONT,
    # Cormorant Garamond → PT Serif Italic (лёгкий курсив)
    "cormorant garamond":   BODY_ITALIC_FONT,
    "cormorant":            BODY_ITALIC_FONT,
    # Raleway / Montserrat / Open Sans → PT Sans (гротеск)
    "raleway":              SANS_FONT,
    "montserrat":           SANS_FONT,
    "open sans":            SANS_FONT,
    "lato":                 SANS_FONT,
    # Прямые PT-имена
    "pt serif":             BODY_FONT,
    "pt serif bold":        BODY_BOLD_FONT,
    "pt serif italic":      BODY_ITALIC_FONT,
    "pt sans":              SANS_FONT,
    "pt sans bold":         SANS_BOLD_FONT,
    "pt sans italic":       SANS_ITALIC_FONT,
}


def _resolve_font(font_name: str | None, default: str | None = None) -> str:
    """Преобразует дизайн-название шрифта в зарегистрированный внутренний шрифт.

    Если font_name не распознан — возвращает default (или BODY_FONT).
    """
    if not font_name:
        return default or BODY_FONT
    key = font_name.strip().lower()
    return _FONT_ALIASES.get(key, default or BODY_FONT)


def _elem_font(elem: dict, default_font: str, default_size: float = 10.0) -> tuple[str, float]:
    """Извлекает шрифт и кегль из полей элемента (font_family/font/font_weight/font_style/font_size/size).

    Поддерживает оба соглашения Layout Designer:
      - v3.2: font_family + font_weight + font_style + font_size
      - v1:   font + size
    """
    family = (elem.get("font_family") or elem.get("font") or "").strip()
    size   = float(elem.get("font_size") or elem.get("size") or elem.get("size_pt") or default_size)
    weight = elem.get("font_weight", "").lower()
    style  = elem.get("font_style",  "").lower()

    if not family:
        base = default_font
    else:
        key = family.lower()
        # Пробуем составное имя (например "pt sans bold")
        if "bold" in weight:
            full_key = key + " bold"
            base = _FONT_ALIASES.get(full_key) or _FONT_ALIASES.get(key, default_font)
        elif "italic" in style:
            full_key = key + " italic"
            base = _FONT_ALIASES.get(full_key) or _FONT_ALIASES.get(key, default_font)
        else:
            base = _FONT_ALIASES.get(key, default_font)

    # Если базовый шрифт найден, применяем weight/style через суффикс
    if "bold" in weight and "-Bold" not in base and "Bold" not in base:
        candidate = base + "-Bold"
        if candidate in _REGISTERED or candidate in ("Times-Bold", "Helvetica-Bold"):
            base = candidate
    if "italic" in style and "-Italic" not in base and "Italic" not in base and "Oblique" not in base:
        candidate = base + "-Italic"
        if candidate in _REGISTERED or candidate in ("Times-Italic", "Helvetica-Oblique"):
            base = candidate

    return base, size


def _draw_spaced_string(c, text: str, x: float, y: float,
                        letter_spacing: float, align: str = "center") -> None:
    """Рисует строку с межбуквенным интервалом (letter_spacing в pt).

    align: "center", "left", "right"
    """
    if not text:
        return
    if not letter_spacing:
        if align == "center":
            c.drawCentredString(x, y, text)
        elif align == "right":
            c.drawRightString(x, y, text)
        else:
            c.drawString(x, y, text)
        return

    from reportlab.pdfbase import pdfmetrics as _pm
    fn   = c._fontname
    fsize = c._fontsize
    char_widths = [_pm.stringWidth(ch, fn, fsize) for ch in text]
    total_w = sum(char_widths) + letter_spacing * (len(text) - 1)

    if align == "center":
        cur_x = x - total_w / 2
    elif align == "right":
        cur_x = x - total_w
    else:
        cur_x = x

    for ch, cw in zip(text, char_widths):
        c.drawString(cur_x, y, ch)
        cur_x += cw + letter_spacing


def _log_fonts():
    print(f"[RENDERER] Шрифты: body={BODY_FONT} body-bold={BODY_BOLD_FONT} "
          f"body-italic={BODY_ITALIC_FONT} sans={SANS_FONT}")


# ── Paragraph helpers ─────────────────────────────────────────────────────────
def make_style(font: str, size: float, color_hex: str,
               leading: float | None = None, alignment=TA_JUSTIFY) -> ParagraphStyle:
    if leading is None:
        leading = size * 1.45
    return ParagraphStyle(
        "auto",
        fontName=font,
        fontSize=size,
        leading=leading,
        textColor=HexColor(color_hex),
        alignment=alignment,
        spaceBefore=0,
        spaceAfter=0,
    )


def make_para(text: str, font: str, size: float, color_hex: str,
              leading: float | None = None, alignment=TA_JUSTIFY) -> Paragraph:
    safe = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return Paragraph(safe, make_style(font, size, color_hex, leading, alignment))


def draw_para(c, para: Paragraph, x: float, y: float, w: float, h: float) -> float:
    """Рисует параграф, возвращает использованную высоту."""
    pw, ph = para.wrap(w, h)
    if ph <= 0:
        return 0.0
    para.drawOn(c, x, y - ph)
    return ph


# ── Photo loader ──────────────────────────────────────────────────────────────
class PhotoManager:
    def __init__(self, photos_dir: Path | None):
        self.photos_dir = photos_dir
        self._map: dict[str, Path] = {}
        if photos_dir and photos_dir.exists():
            self._build_map()

    def _build_map(self):
        manifest_path = self.photos_dir / "manifest.json"
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            for entry in manifest:
                idx = entry.get("index", 0)
                key = f"photo_{idx:03d}"
                fname = entry.get("filename", "")
                full = self.photos_dir / fname
                if full.exists():
                    self._map[key] = full
        else:
            for f in sorted(self.photos_dir.glob("*.jpg")) + sorted(self.photos_dir.glob("*.png")):
                try:
                    idx = int(f.name.split("_")[0])
                    self._map[f"photo_{idx:03d}"] = f
                except (ValueError, IndexError):
                    pass

    def get(self, photo_id: str) -> Path | None:
        return self._map.get(photo_id)


# ── Book index (paragraph lookup) ─────────────────────────────────────────────
class BookIndex:
    """Индекс абзацев / выносок / исторических справок книги для lookup по ref.

    Layout Designer v3.21+ возвращает ссылки вида:
      {"type": "paragraph",        "chapter_id": "ch_02", "paragraph_ref":        "p3"}
      {"type": "callout",          "chapter_id": "ch_02", "callout_ref":          "callout_01"}
      {"type": "historical_note",  "chapter_id": "ch_02", "historical_note_ref":  "hist_01"}
    Этот класс восстанавливает текст из book_FINAL.json по этим ключам.

    Обратная совместимость:
      paragraph: paragraph_id (v3.19 legacy) — поддерживается через тот же .get()
      callout: callout_id (текущие сохранённые layout'ы 04-09) — get_callout()
      historical_note: note_id / без id (legacy text inline) — fallback в renderer

    Fallback: если ref не найден — поведение зависит от strict_refs:
    - strict_refs=False: возвращает None (renderer переходит к legacy text или пропуску)
    - strict_refs=True:  raises ValueError (ошибка пайплайна)
    """

    def __init__(self, book: dict | None):
        self._index: dict[str, dict[str, dict]] = {}  # ch_id -> {para_id -> {"text": ..., "type": ...}}
        self._bio_data: dict[str, dict] = {}
        self._callouts: dict[str, str] = {}            # callout_id -> text
        self._historical_notes: dict[str, str] = {}    # note_id -> text
        self._raw_chapters: list[dict] = []
        if not book:
            return
        self._raw_chapters = book.get("chapters", [])
        for ch in self._raw_chapters:
            ch_id = ch.get("id", "")
            if not ch_id:
                continue
            # Сохраняем bio_data для ch_01
            if ch.get("bio_data"):
                self._bio_data[ch_id] = ch["bio_data"]
            # Используем paragraphs[] если есть, иначе разбиваем content
            paras = ch.get("paragraphs")
            if paras:
                self._index[ch_id] = {
                    p["id"]: {"text": p.get("text", ""), "type": p.get("type", "paragraph")}
                    for p in paras if p.get("id") and p.get("text")
                }
            else:
                content = ch.get("content") or ""
                parts = [p.strip() for p in content.split("\n\n") if p.strip()]
                self._index[ch_id] = {
                    f"p{i + 1}": {"text": t, "type": "paragraph"}
                    for i, t in enumerate(parts)
                }

        # Top-level коллекции callouts и historical_notes
        for co in book.get("callouts", []) or []:
            co_id = co.get("id")
            text = co.get("text", "")
            if co_id and text:
                self._callouts[co_id] = text
        for hn in book.get("historical_notes", []) or []:
            hn_id = hn.get("id")
            text = hn.get("text", "")
            if hn_id and text:
                self._historical_notes[hn_id] = text

    def get(self, chapter_id: str, paragraph_id: str) -> str | None:
        ch = self._index.get(chapter_id)
        if ch is None:
            return None
        entry = ch.get(paragraph_id)
        if entry is None:
            return None
        return entry["text"] if isinstance(entry, dict) else entry

    def get_type(self, chapter_id: str, paragraph_id: str) -> str:
        """Возвращает тип элемента: 'paragraph', 'subheading' и т.д."""
        ch = self._index.get(chapter_id)
        if ch is None:
            return "paragraph"
        entry = ch.get(paragraph_id)
        if entry is None:
            return "paragraph"
        return entry.get("type", "paragraph") if isinstance(entry, dict) else "paragraph"

    def get_callout(self, callout_id: str) -> str | None:
        """Возвращает текст выноски по id или None если не найден."""
        return self._callouts.get(callout_id)

    def get_historical_note(self, note_id: str) -> str | None:
        """Возвращает текст исторической справки по id или None если не найден."""
        return self._historical_notes.get(note_id)

    def chapter_paragraphs(self, chapter_id: str) -> list[tuple[str, str]]:
        """Возвращает [(paragraph_id, text), ...] в порядке главы."""
        ch = self._index.get(chapter_id, {})
        # Сортируем p1, p2, ... p10, p11 числово
        def _sort_key(pid: str) -> int:
            try:
                return int(pid.lstrip("p"))
            except ValueError:
                return 0
        return sorted(
            [(pid, (e["text"] if isinstance(e, dict) else e)) for pid, e in ch.items()],
            key=lambda kv: _sort_key(kv[0])
        )

    def chapter_bio_data(self, chapter_id: str) -> dict | None:
        """Возвращает структурированный bio_data для главы (personal/education/military/awards/family)."""
        return self._bio_data.get(chapter_id)

    @property
    def is_empty(self) -> bool:
        return not self._index


class RenderOptions:
    """Опции рендеринга слоёв для acceptance gates."""

    def __init__(
        self,
        text_only: bool = False,
        with_bio_block: bool = False,
        no_photos: bool = False,
        with_cover: bool = False,
        strict_refs: bool = False,
        allow_missing_refs: bool = False,
    ):
        self.text_only = text_only
        self.with_bio_block = with_bio_block
        self.no_photos = no_photos
        self.with_cover = with_cover
        self.strict_refs = strict_refs
        self.allow_missing_refs = allow_missing_refs

    def mode_label(self) -> str:
        if self.text_only and self.with_bio_block:
            return "text_only+bio"
        if self.text_only:
            return "text_only"
        if self.no_photos:
            return "no_photos"
        return "full"

    def story_mode_applicable(self) -> bool:
        """True когда Story flow подходит: текстовые ворота без обложки (2a, 2b, 2c).
        Canvas-режим используется для ворот 3/4 где нужно точное размещение фото/обложки.
        """
        return (self.text_only or self.no_photos) and not self.with_cover


# ── Timeline flowable (Story mode) ───────────────────────────────────────────

class _TimelineFlowable(Flowable):
    """Вертикальная линия + точки + текст хронологии для Platypus Story.

    Спецификация (согласовано с Дашей):
      - вертикальная линия x = 10мм, #c4a070, 1pt
      - точка-маркер: круг r=1.5мм, #c4a070, без обводки
      - период: PT Sans Bold 7pt, #8b7355, uppercase
      - название: PT Serif Bold 10pt, #3d2e1f
      - описание: PT Serif 9pt, leading 13pt, #3d2e1f
      - отступ между этапами: 5мм
      - расстояние точка → текст: 6мм
    """

    _ACCENT   = HexColor("#c4a070")
    _PERIOD_C = HexColor("#8b7355")
    _TEXT_C   = HexColor("#3d2e1f")
    _X_LINE   = 10 * mm
    _X_TEXT   = 16 * mm   # _X_LINE + 6mm
    _DOT_R    = 1.5 * mm
    _STAGE_GAP = 5 * mm

    def __init__(self, entries: list, sans_bold: str, serif: str,
                 serif_bold: str, avail_width: float):
        Flowable.__init__(self)
        self.entries    = [e for e in entries if isinstance(e, dict)]
        self._sf        = sans_bold
        self._rf        = serif
        self._rb        = serif_bold or serif
        self._aw        = avail_width
        self._layout: list[dict] = []
        self._total_h   = 0.0

    def _tw(self) -> float:
        return self._aw - self._X_TEXT

    def _make_paras(self):
        tw = self._tw()
        result = []
        for entry in self.entries:
            period = str(entry.get("period") or entry.get("years") or "").upper()
            title  = str(entry.get("title")  or entry.get("name")  or entry.get("stage") or "")
            events = entry.get("events") or entry.get("key_events") or entry.get("text") or ""
            if isinstance(events, list):
                events = ". ".join(str(e).rstrip(".") for e in events) + "."

            pp = Paragraph(period, ParagraphStyle(
                "TlPer", fontName=self._sf, fontSize=7,
                textColor=self._PERIOD_C, leading=9))

            pt = Paragraph(title, ParagraphStyle(
                "TlTit", fontName=self._rb, fontSize=10,
                textColor=self._TEXT_C, leading=13, spaceBefore=1)) if title else None

            pd = Paragraph(str(events), ParagraphStyle(
                "TlDes", fontName=self._rf, fontSize=9,
                textColor=self._TEXT_C, leading=13, spaceBefore=1)) if events else None

            result.append((pp, pt, pd))
        return result

    def wrap(self, availWidth, availHeight):
        self._aw = availWidth
        paras = self._make_paras()
        tw = self._tw()

        self._layout = []
        total = 0.0
        for i, (pp, pt, pd) in enumerate(paras):
            _, hp = pp.wrap(tw, 9999)
            ht = pt.wrap(tw, 9999)[1] if pt else 0
            hd = pd.wrap(tw, 9999)[1] if pd else 0
            entry_h = hp + ht + hd
            gap = self._STAGE_GAP if i < len(paras) - 1 else 0
            self._layout.append(dict(
                y_start=total, hp=hp, ht=ht, hd=hd,
                entry_h=entry_h, pp=pp, pt=pt, pd=pd))
            total += entry_h + gap

        self._total_h = total
        self.width  = availWidth
        self.height = total
        return availWidth, total

    def draw(self):
        c = self.canv
        H = self._total_h

        # dot y-coordinates (canvas: y=0 at bottom)
        dot_ys = [H - info["y_start"] - info["hp"] * 0.5
                  for info in self._layout]

        # вертикальная линия
        if len(dot_ys) >= 2:
            c.setStrokeColor(self._ACCENT)
            c.setLineWidth(1)
            c.line(self._X_LINE, dot_ys[0], self._X_LINE, dot_ys[-1])

        # точки + текст
        for i, info in enumerate(self._layout):
            y_top = H - info["y_start"]

            # золотая точка
            c.setFillColor(self._ACCENT)
            c.circle(self._X_LINE, dot_ys[i], self._DOT_R, stroke=0, fill=1)

            # period
            info["pp"].drawOn(c, self._X_TEXT, y_top - info["hp"])
            # title
            if info["pt"]:
                info["pt"].drawOn(c, self._X_TEXT,
                                  y_top - info["hp"] - info["ht"])
            # description
            if info["pd"]:
                info["pd"].drawOn(c, self._X_TEXT,
                                  y_top - info["hp"] - info["ht"] - info["hd"])

    def split(self, availWidth, availHeight):
        """Разбивает timeline между записями если не помещается целиком."""
        if not self._layout:
            self.wrap(availWidth, availHeight)
        if self._total_h <= availHeight:
            return [self]
        # Ищем точку разрыва (целая запись умещается)
        split_idx = 0
        current_h = 0.0
        for i, info in enumerate(self._layout):
            entry_h = info["entry_h"] + (self._STAGE_GAP if i < len(self._layout) - 1 else 0.0)
            if current_h + entry_h > availHeight:
                split_idx = i
                break
            current_h += entry_h
        if split_idx == 0:
            return [self]   # даже первая запись не влезает — отдаём всё
        first = _TimelineFlowable(
            self.entries[:split_idx], self._sf, self._rf, self._rb, availWidth)
        rest  = _TimelineFlowable(
            self.entries[split_idx:], self._sf, self._rf, self._rb, availWidth)
        return [first, rest]


# ── Main renderer ─────────────────────────────────────────────────────────────
class PdfRenderer:
    def __init__(self, layout: dict, photos: PhotoManager,
                 portrait_path: Path | None, output: Path,
                 book_index: BookIndex | None = None,
                 options: RenderOptions | None = None):
        self.options = options or RenderOptions()
        self.pages = copy.deepcopy(layout.get("pages", []))
        self.sg = layout.get("style_guide", {})
        self.photo_captions: dict = layout.get("photo_captions", {})
        self.photos = photos
        self.portrait_path = portrait_path
        self.output = output
        self.book_index = book_index or BookIndex(None)
        self.pages = self._filter_pages_for_mode(self.pages)
        self._inject_page_chapter_ids()
        # Счётчики резолвинга paragraph_ref (для post-render аудита)
        self._ref_resolved: int = 0
        self._ref_missing: int = 0

        # ── Page geometry (A5)
        self.W, self.H = A5  # 419.5 × 595.3 pt
        m = self.sg.get("page", {}).get("margins", {})
        self.MT = m.get("top_mm", 20) * mm
        self.MB = m.get("bottom_mm", 20) * mm
        self.ML = m.get("inner_mm", 20) * mm
        self.MR = m.get("outer_mm", 15) * mm
        self.TW = self.W - self.ML - self.MR
        self.TH = self.H - self.MT - self.MB
        self.TX = self.ML
        self.TY = self.H - self.MT   # top of text area (y decreases downward)

        # ── Typography
        typ = self.sg.get("typography", {})
        bf = typ.get("body_font", {})
        self.body_size  = bf.get("size_pt", 10)
        self.body_color = bf.get("color", "#111111")
        self.body_lead  = self.body_size * bf.get("line_height", 1.6)

        hf = typ.get("heading_font", {})
        self.chapter_size  = hf.get("chapter_title_size_pt", 24)
        self.section_size  = hf.get("section_title_size_pt", 16)
        self.heading_color = hf.get("color", "#111111")

        cf = typ.get("caption_font", {})
        self.caption_size  = cf.get("size_pt", 8)
        self.caption_color = cf.get("color", "#666666")

        co = typ.get("callout_font", {})
        self.callout_size  = co.get("size_pt", 11)
        self.callout_color = co.get("color", "#3d2e1f")

        hn = typ.get("historical_note_font", {})
        self.hist_size  = hn.get("size_pt", 9)
        self.hist_color = hn.get("color", "#5a4a38")

        # ── Colors
        col = self.sg.get("colors", {})
        self.c_bg          = col.get("background", "#faf8f5")
        self.c_text        = col.get("text_primary", "#111111")
        self.c_accent      = col.get("accent", "#c4a070")
        self.c_callout_bg  = col.get("callout_background", "#f5f2ed")
        self.c_callout_br  = col.get("callout_border", "#e8e0d4")
        self.c_hist_bg     = col.get("historical_background", "#f0ebe0")
        self.c_divider     = col.get("chapter_divider", "#e8e0d4")
        self.c_secondary   = col.get("text_secondary", "#666666")

        # ── Spacing
        sp = self.sg.get("spacing", {})
        self.para_space   = sp.get("paragraph_spacing_pt", 12)
        self.photo_margin = sp.get("photo_margin_pt", 12)
        self.callout_pad  = sp.get("callout_padding_pt", 16)

        # Уплотнение страниц нужно только в canvas-режиме (с фото/обложкой).
        # В Story flow Platypus сам заполняет страницы — rebalance не нужен.
        if not self.options.story_mode_applicable():
            self._rebalance_text_pages()

    def _inject_page_chapter_ids(self):
        """Проставляет chapter_id из страницы в элементы, у которых его нет.

        Layout Designer v3.20 иногда ставит chapter_id только на уровне страницы,
        опуская его в элементах-абзацах. Fidelity validator и verify_and_patch
        корректно обрабатывают этот случай через fallback на page.chapter_id,
        но _elem_para_text и _render_paragraph смотрят только на elem.chapter_id.
        Этот метод устраняет расхождение, внося chapter_id напрямую в элементы.
        """
        for page in self.pages:
            page_ch = page.get("chapter_id", "")
            if not page_ch:
                continue
            for elem in page.get("elements", []):
                if elem.get("type") == "paragraph" and not elem.get("chapter_id"):
                    elem["chapter_id"] = page_ch

    # ── Entry point ──────────────────────────────────────────────────────────

    def render(self):
        _log_fonts()
        print(f"[RENDERER] Режим: {self.options.mode_label()}")
        if self.options.story_mode_applicable():
            result = self._render_as_story()
        else:
            result = self._render_as_canvas()
        self._report_ref_resolution()
        return result

    def _report_ref_resolution(self):
        """Выводит итог резолвинга paragraph_ref и падает если потеряно слишком много."""
        total = self._ref_resolved + self._ref_missing
        if total == 0:
            return
        pct = self._ref_resolved / total * 100
        print(f"[RENDERER] Refs: {self._ref_resolved}/{total} резолвилось ({pct:.0f}%)")
        if self._ref_missing > 0:
            print(f"[RENDERER] ⚠️  {self._ref_missing} paragraph_ref не найдено в book_FINAL "
                  f"— текст этих абзацев отсутствует в PDF")
        if total >= 5 and pct < 50:
            print(f"[RENDERER] ❌ КРИТИЧНО: резолвинг {pct:.0f}% < 50% — PDF потерял большую "
                  f"часть контента. Проверьте совпадение chapter_id и paragraph IDs "
                  f"между layout и book_FINAL.")
            sys.exit(1)

    def _story_bio_data_block(self, elem: dict, body_style, accent_color) -> list:
        """Возвращает список Platypus-flowables для bio_data_block (ch_01)."""
        from reportlab.platypus import Paragraph as PlatPara, Table, TableStyle, KeepTogether, CondPageBreak
        sections = elem.get("sections", [])
        timeline = elem.get("timeline", [])
        content  = elem.get("content", "")
        if isinstance(content, dict):
            if not sections and isinstance(content.get("sections"), list):
                sections = content["sections"]
            if not timeline and isinstance(content.get("timeline"), list):
                timeline = content["timeline"]
            content = content.get("content", "")

        rows = []

        if sections:
            for sec in sections:
                sec_title = sec.get("title") or sec.get("label", "")
                if sec_title:
                    rows.append(("_SEC_", sec_title.upper()))
                for item in sec.get("items", []):
                    lbl = item.get("label", "")
                    val = item.get("value", "")
                    if lbl or val:
                        rows.append((lbl, val))
        elif content:
            for line in content.split("\n"):
                line = line.strip()
                if not line:
                    continue
                if line.startswith("**") and line.endswith("**"):
                    rows.append(("_SEC_", line.strip("* ")))
                elif ":" in line:
                    lbl, _, val = line.partition(":")
                    rows.append((lbl.strip(" *"), val.strip()))
                else:
                    # Первое слово — метка (Родилась, Умерла, ...), остальное — значение
                    parts = line.split(None, 1)
                    if len(parts) == 2:
                        rows.append((parts[0].rstrip(".,"), parts[1]))
                    else:
                        rows.append(("", line))

        if not rows and not timeline:
            return []

        SANS_B = SANS_FONT_BOLD
        SERIF  = BODY_FONT
        LABEL_CLR = HexColor("#aaaaaa")

        story_items = []
        story_items.append(Spacer(1, 6))

        # Строим таблицы данных, накапливая пары (sec_label, [data_tables])
        # чтобы обернуть sec_label + первую строку в KeepTogether
        pending_sec: "Paragraph | None" = None
        pending_rows: list = []

        def _flush_pending():
            """Отправляет накопленные строки в story_items, оборачивая sec_label с первой."""
            nonlocal pending_sec, pending_rows
            if not pending_rows:
                if pending_sec is not None:
                    story_items.append(pending_sec)
            else:
                if pending_sec is not None:
                    story_items.append(KeepTogether([pending_sec, pending_rows[0]]))
                    story_items.extend(pending_rows[1:])
                else:
                    story_items.extend(pending_rows)
            pending_sec = None
            pending_rows = []

        for lbl, val in rows:
            if lbl == "_SEC_":
                _flush_pending()
                pending_sec = PlatPara(val, ParagraphStyle(
                    "BioSec", fontName=SANS_B, fontSize=6, textColor=accent_color,
                    spaceBefore=6, spaceAfter=2))
            else:
                data = [[
                    PlatPara(lbl.upper(), ParagraphStyle("BioLbl", fontName=SANS_B,
                        fontSize=7, textColor=LABEL_CLR, leading=9)),
                    PlatPara(val, ParagraphStyle("BioVal", fontName=SERIF,
                        fontSize=8.5, textColor=HexColor("#222222"), leading=11)),
                ]]
                tw = self.TW
                t = Table(data, colWidths=[tw * 0.36, tw * 0.64])
                t.setStyle(TableStyle([
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 1),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ]))
                pending_rows.append(t)

        _flush_pending()

        # ── Хронология жизни — вертикальная линия + точки ──
        if timeline:
            tl_header = PlatPara("ХРОНОЛОГИЯ ЖИЗНИ", ParagraphStyle(
                "TlSec", fontName=SANS_B, fontSize=6, textColor=accent_color,
                spaceBefore=10, spaceAfter=4))
            tl_flowable = _TimelineFlowable(
                timeline, SANS_B, BODY_FONT, BODY_BOLD_FONT, self.TW)
            # CondPageBreak + KeepTogether: заголовок обязан быть вместе с первым этапом
            story_items.append(CondPageBreak(80 * mm))
            story_items.append(KeepTogether([tl_header, tl_flowable]))

        story_items.append(Spacer(1, 6))
        return story_items

    def _render_as_canvas(self):
        """Постраничный рендер через ReportLab canvas (для ворот с фото/обложкой)."""
        c = rl_canvas.Canvas(str(self.output), pagesize=A5)
        for page in self.pages:
            ptype = page.get("type", "")
            handler = {
                "cover":            self._render_cover,
                "toc":              self._render_toc,
                "full_page_photo":  self._render_full_page_photo,
                "chapter_start":    self._render_chapter_start,
                "text":                self._render_text_page,
                "text_with_photo":     self._render_text_page,
                "text_with_photos":    self._render_text_page,
                "text_only":           self._render_text_page,
                "text_with_callouts":  self._render_text_page,
                "text_with_callout":   self._render_text_page,
                "text_with_bio":       self._render_text_page,
                "text_with_sidebar":   self._render_text_page,
                "bio_timeline":       self._render_bio_timeline,
                "photo_section":      self._render_photo_section,
                "photo_section_start": self._render_photo_section,
            }.get(ptype, self._render_unknown)
            handler(c, page)
            c.showPage()
        c.save()
        kb = self.output.stat().st_size // 1024
        print(f"[RENDERER] ✅  PDF: {self.output.name} ({kb} KB, {len(self.pages)} стр.)")
        return self.output

    # ── Story flow (Platypus) ─────────────────────────────────────────────────

    def _render_as_story(self):
        """Рендер через ReportLab Platypus Story — непрерывный поток, страницы заполняются сами."""
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph as PlatPara, Spacer,
            PageBreak, KeepTogether, HRFlowable, CondPageBreak,
        )
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_CENTER
        import re as _re

        BG = HexColor(self.c_bg)
        ACCENT = HexColor(self.c_accent)
        TEXT = HexColor(self.c_text)
        CALLOUT_BG = HexColor(self.c_callout_bg)
        CALLOUT_BR = HexColor(self.c_callout_br)

        body_size   = 9.5
        body_lead   = body_size * 1.6
        sect_size   = 11
        ch_size     = 17
        call_size   = 13
        hist_size   = 9.0

        GOLD = HexColor("#c4a070")

        ST_BODY = ParagraphStyle("story_body",
            fontName=BODY_FONT, fontSize=body_size, leading=body_lead,
            textColor=TEXT, alignment=TA_JUSTIFY,
            firstLineIndent=12, spaceBefore=0, spaceAfter=body_size * 0.8,
        )
        ST_SECTION = ParagraphStyle("story_section",
            fontName=SANS_FONT_BOLD, fontSize=sect_size, leading=sect_size * 1.3,
            textColor=TEXT, alignment=TA_LEFT,
            spaceBefore=sect_size, spaceAfter=sect_size * 0.5,
            keepWithNext=1,
        )
        ST_CHAPTER = ParagraphStyle("story_chapter",
            fontName=SANS_FONT_BOLD, fontSize=ch_size, leading=ch_size * 1.25,
            textColor=TEXT, alignment=TA_LEFT,
            spaceBefore=ch_size * 0.5, spaceAfter=4,
        )
        ST_CHAPTER_LABEL = ParagraphStyle("story_chapter_label",
            fontName=SANS_FONT_BOLD, fontSize=8, leading=10,
            textColor=GOLD, alignment=TA_LEFT,
            spaceBefore=0, spaceAfter=4,
        )
        ST_CALLOUT = ParagraphStyle("story_callout",
            fontName=BODY_FONT_ITALIC, fontSize=13, leading=20,
            textColor=HexColor("#3d2e1f"), alignment=TA_LEFT,
            leftIndent=0, rightIndent=0,  # inset задаётся на уровне Table
            spaceBefore=0, spaceAfter=0,
        )
        ST_CALLOUT_ATTR = ParagraphStyle("story_callout_attr",
            fontName=BODY_FONT_ITALIC, fontSize=8, leading=10,
            textColor=HexColor("#3d2e1f"), alignment=TA_RIGHT,
            rightIndent=0,
        )
        ST_HIST = ParagraphStyle("story_hist",
            fontName=BODY_FONT_ITALIC, fontSize=hist_size, leading=hist_size * 1.6,
            textColor=HexColor("#5a4a38"),  # всегда тёмно-коричневый, независимо от конфига
            alignment=TA_JUSTIFY,
            leftIndent=8, rightIndent=8,
            spaceBefore=8, spaceAfter=8,
        )
        ST_HIST_LABEL = ParagraphStyle("story_hist_label",
            fontName=SANS_FONT_BOLD, fontSize=6.5, leading=8,
            textColor=GOLD, spaceBefore=0, spaceAfter=3,
        )
        HIST_BG = HexColor("#f0ebe0")

        def _para_text(raw: str) -> str:
            raw = _re.sub(r"\*{1,3}(.+?)\*{1,3}", r"\1", raw)
            raw = raw.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            return raw

        def _hist_note_block(content_text: str, title_text: str = "") -> list:
            """Рендерит исторический блок: фон #f0ebe0, золотая черта слева 2pt, лейбл.
            Весь блок завёрнут в KeepTogether — не разрывается между страницами."""
            from reportlab.platypus import Table as _Table, TableStyle as _TS
            rows = [PlatPara("ИСТОРИЧЕСКАЯ СПРАВКА", ST_HIST_LABEL)]
            if title_text:
                rows.append(PlatPara(_para_text(title_text), ST_HIST))
            if content_text:
                rows.append(PlatPara(_para_text(content_text), ST_HIST))
            tbl = _Table([[r] for r in rows], colWidths=[self.TW])
            tbl.setStyle(_TS([
                ("BACKGROUND",    (0, 0), (-1, -1), HIST_BG),
                ("TOPPADDING",    (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING",   (0, 0), (-1, -1), 10),
                ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
                ("LINEBEFORE",    (0, 0), (0, -1),  2, GOLD),
            ]))
            return [Spacer(1, 6), KeepTogether([tbl]), Spacer(1, 6)]

        story: list = []
        first_page = True

        for page in self.pages:
            ptype = (page.get("type") or "").strip()
            chapter_id = page.get("chapter_id", "")

            # ── chapter_start: принудительный разрыв страницы ──
            if ptype == "chapter_start":
                if not first_page:
                    story.append(PageBreak())
                first_page = False
                ch_title  = page.get("chapter_title") or page.get("title", "")
                ch_num    = page.get("chapter_number", "")
                # Если нет chapter_number — берём порядковый номер из chapter_id (ch_02 → 2)
                if not ch_num and chapter_id:
                    import re as _re2
                    m = _re2.search(r"(\d+)", chapter_id)
                    if m:
                        ch_num = str(int(m.group(1)))
                # Метка «Глава 02» — PT Sans Bold 8pt золотой
                if ch_num and chapter_id not in ("epilogue", "ch_01"):
                    story.append(PlatPara(f"Глава {ch_num.zfill(2)}", ST_CHAPTER_LABEL))
                if ch_title:
                    story.append(PlatPara(ch_title, ST_CHAPTER))
                    story.append(HRFlowable(width="100%", thickness=1,
                                            color=ACCENT, spaceAfter=8))
                # Плейсхолдер фото на chapter_start (для всех глав кроме ch_01)
                if self.options.no_photos and chapter_id not in ("ch_01",):
                    from reportlab.platypus import Table as _Table, TableStyle as _TS
                    from reportlab.lib.enums import TA_CENTER as _TA_C
                    _ph_h = 55 * mm
                    _ph_lbl = PlatPara(
                        "[ФОТО — начало главы]",
                        ParagraphStyle("ph_lbl", fontName=SANS_FONT_BOLD, fontSize=8,
                            textColor=HexColor("#9b9080"), alignment=_TA_C))
                    _ph_tbl = _Table([[_ph_lbl]], colWidths=[self.TW], rowHeights=[_ph_h])
                    _ph_tbl.setStyle(_TS([
                        ("BACKGROUND",     (0, 0), (-1, -1), HexColor("#e8e4dc")),
                        ("VALIGN",         (0, 0), (-1, -1), "MIDDLE"),
                        ("TOPPADDING",     (0, 0), (-1, -1), 0),
                        ("BOTTOMPADDING",  (0, 0), (-1, -1), 0),
                        ("LEFTPADDING",    (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING",   (0, 0), (-1, -1), 0),
                    ]))
                    story.append(Spacer(1, 8))
                    story.append(_ph_tbl)
                # Абзацы на chapter_start (если есть — например ch_01 bio)
                for elem in page.get("elements", []):
                    etype = (elem.get("type") or "").strip()
                    if etype == "paragraph":
                        # ch_01: если рендерим bio_data — content-абзацы пропускаем
                        # (они дублируют "Личные данные" из bio_data таблицы)
                        if chapter_id == "ch_01" and self.options.with_bio_block:
                            continue
                        text = self._elem_para_text(elem)
                        if text:
                            story.append(PlatPara(_para_text(text), ST_BODY))

                # ch_01 bio block: инжектируем из book_index при --with-bio-block
                if chapter_id == "ch_01" and self.options.with_bio_block and self.book_index:
                    bio_data = self.book_index.chapter_bio_data("ch_01")
                    if bio_data:
                        # Конвертируем bio_data {personal:[{label,value}], education:[], ...}
                        # → sections формат для _story_bio_data_block
                        _SEC_LABELS = {
                            "personal":  "Личные данные",
                            "education": "Образование",
                            "military":  "Военная служба",
                            "awards":    "Награды",
                            "family":    "Семья",
                        }
                        sections = []
                        for key in ("personal", "education", "military", "awards", "family"):
                            items = bio_data.get(key)
                            if not items or not isinstance(items, list):
                                continue
                            sections.append({
                                "title": _SEC_LABELS.get(key, key.capitalize()),
                                "items": [
                                    {"label": it.get("label", ""), "value": it.get("value", "")}
                                    for it in items if isinstance(it, dict)
                                ],
                            })
                        # timeline — из bio_data.timeline или ch_01.timeline
                        timeline = bio_data.get("timeline") or []
                        if not timeline:
                            # Попробуем из book_index напрямую (если хранится отдельно)
                            raw_ch = next(
                                (c for c in (self.book_index._raw_chapters or [])
                                 if c.get("id") == "ch_01"), None
                            ) if hasattr(self.book_index, "_raw_chapters") else None
                            if raw_ch:
                                timeline = raw_ch.get("timeline") or []
                        if sections or timeline:
                            story += self._story_bio_data_block(
                                {"sections": sections, "timeline": timeline}, ST_BODY, GOLD)
                # Принудительный разрыв страницы после chapter_start:
                # chapter_start занимает ровно одну PDF-страницу, следующий layout-page
                # должен начинаться с новой страницы, иначе его элементы вытекают на chapter_start.
                story.append(PageBreak())
                continue

            # ── cover / toc / blank — пропускаем в story mode ──
            if ptype in ("cover", "toc", "blank"):
                continue

            # ── текстовые страницы ──
            if first_page:
                first_page = False

            for elem in page.get("elements", []):
                etype = (elem.get("type") or "").strip()

                if etype == "paragraph":
                    text = self._elem_para_text(elem)
                    if not text:
                        continue
                    if text.strip().startswith("## "):
                        story.append(CondPageBreak(28 * mm))
                        _p = PlatPara(_para_text(text.strip()[3:].strip()), ST_SECTION)
                        _p.keepWithNext = True
                        story.append(_p)
                    elif _re.match(r"^\*{3}(.+?)\*{3}$", text.strip(), _re.DOTALL):
                        # Triple-asterisk = историческая вставка (Историк → Писатель)
                        # Рендерим как historical note block, а НЕ как section header
                        inner = _re.sub(r"^\*{3}(.+?)\*{3}$", r"\1", text.strip(), flags=_re.DOTALL).strip()
                        story += _hist_note_block(inner)
                    elif _re.match(r"^\*{1,2}(.+?)\*{1,2}$", text.strip()):
                        inner = _re.sub(r"\*{1,2}", "", text).strip()
                        story.append(CondPageBreak(28 * mm))
                        _p = PlatPara(_para_text(inner), ST_SECTION)
                        _p.keepWithNext = True
                        story.append(_p)
                    else:
                        story.append(PlatPara(_para_text(text), ST_BODY))

                elif etype == "section_header":
                    htext = elem.get("text", "")
                    if htext:
                        story.append(CondPageBreak(28 * mm))
                        _p = PlatPara(_para_text(htext), ST_SECTION)
                        _p.keepWithNext = True
                        story.append(_p)

                elif etype == "subheading":
                    # Subheading из book_FINAL (via subheading_ref lookup или inline text).
                    # В canvas-режиме обрабатывается _render_subheading; здесь — story mode.
                    sh_ref = elem.get("subheading_ref") or elem.get("paragraph_ref") or ""
                    sh_ch  = elem.get("chapter_id", "")
                    sh_text = ""
                    if sh_ch and sh_ref and self.book_index:
                        sh_text = self.book_index.get(sh_ch, sh_ref) or ""
                        if sh_text:
                            self._ref_resolved += 1
                        else:
                            self._ref_missing += 1
                    if not sh_text:
                        sh_text = elem.get("text", "")
                    if sh_text:
                        sh_text = sh_text.lstrip("# ").strip()
                    if sh_text:
                        story.append(CondPageBreak(28 * mm))
                        _p = PlatPara(_para_text(sh_text), ST_SECTION)
                        _p.keepWithNext = True
                        story.append(_p)

                elif etype == "bio_data_block" and self.options.with_bio_block:
                    story += self._story_bio_data_block(elem, ST_BODY, GOLD)

                elif etype == "callout" and not self.options.text_only:
                    co_content = self._elem_callout_text(elem)
                    co_title   = elem.get("title", "")
                    if co_content or co_title:
                        from reportlab.platypus import Table as _Table, TableStyle as _TS
                        _CO_INSET = 10 * mm          # 10мм отступ слева и справа
                        _co_w = self.TW - 2 * _CO_INSET
                        rows = []
                        if co_title:
                            rows.append(PlatPara(_para_text(co_title), ST_CALLOUT))
                        if co_content:
                            rows.append(PlatPara(_para_text(co_content), ST_CALLOUT))
                        rows.append(PlatPara("— из воспоминаний семьи", ST_CALLOUT_ATTR))
                        tbl = _Table([[r] for r in rows], colWidths=[_co_w], hAlign="CENTER")
                        tbl.setStyle(_TS([
                            ("TOPPADDING",    (0, 0), (-1, -1), 4),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                            ("LEFTPADDING",   (0, 0), (-1, -1), 0),
                            ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
                            # Золотые линии с тем же inset, что и текст
                            ("LINEABOVE", (0, 0),  (-1, 0),  0.75, HexColor("#c4a070")),
                            ("LINEBELOW", (0, -1), (-1, -1), 0.75, HexColor("#c4a070")),
                        ]))
                        story.append(Spacer(1, 10))
                        story.append(tbl)
                        story.append(Spacer(1, 10))

                elif etype == "historical_note" and not self.options.text_only:
                    hn_content = self._elem_historical_note_text(elem)
                    hn_title   = elem.get("title", "")
                    if hn_content or hn_title:
                        story += _hist_note_block(hn_content, hn_title)

        # ── Фотораздел: плейсхолдеры в конце книги (gate 2c, no_photos=True) ──
        if self.options.no_photos and not self.options.text_only:
            photo_items = sorted(self.photos._map.items()) if self.photos and self.photos._map else []
            if photo_items:
                from reportlab.platypus import Table as _Table, TableStyle as _TS
                from reportlab.lib.enums import TA_CENTER as _TA_C

                # Определяем ориентацию по реальным размерам файла
                def _photo_orient(path):
                    try:
                        from PIL import Image as _PILImage
                        with _PILImage.open(path) as _img:
                            _w, _h = _img.size
                        if _w > _h:
                            return "horizontal"
                        elif _h > _w:
                            return "vertical"
                        else:
                            return "square"
                    except Exception:
                        return "unknown"

                # Стили подписей
                _ST_LBL = ParagraphStyle("ph_lbl", fontName=SANS_FONT_BOLD, fontSize=9,
                    textColor=HexColor("#9b9080"), alignment=_TA_C, leading=11)
                _ST_CAP = ParagraphStyle("ph_cap", fontName=BODY_FONT, fontSize=7,
                    textColor=HexColor("#7a6e60"), alignment=_TA_C, leading=9)

                # Вспомогательная функция: серый прямоугольник для 1 фото
                import re as _re_ph
                def _single_placeholder(n, path, width, height):
                    stem    = Path(path).stem
                    caption = _re_ph.sub(r"^\d+_\d+_?", "", stem).strip() or stem
                    caption = caption[:40]
                    return _Table(
                        [[PlatPara(f"ФОТО {n}", _ST_LBL)],
                         [PlatPara(caption, _ST_CAP) if caption else Spacer(1, 1)]],
                        colWidths=[width],
                        rowHeights=[height, None],
                    )

                def _ph_style(tbl):
                    tbl.setStyle(_TS([
                        ("BACKGROUND",    (0, 0), (0, 0), HexColor("#e8e4dc")),
                        ("VALIGN",        (0, 0), (0, 0), "MIDDLE"),
                        ("TOPPADDING",    (0, 0), (-1, -1), 2),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                        ("LEFTPADDING",   (0, 0), (-1, -1), 4),
                        ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
                    ]))
                    return tbl

                # A5 text-area heights (консервативный подход)
                _V_H = self.TW * 4 / 3     # vertical: full-width, 3:4 пропорция → высота
                _L_H = self.TW * 3 / 4     # horizontal: full-width, 4:3 пропорция → высота

                # Собираем «страницы» фотораздела по правилам Арт-директора v1.8
                # vertical → 1 на страницу full-width
                # 2 horizontal подряд → pair_stack (стопкой) на одной странице
                # 1 horizontal или unknown → 1 на страницу
                _enriched = [(key, path, _photo_orient(path)) for key, path in photo_items]
                _photo_pages: list = []   # list of list[(n, path, orient)]
                _j = 0
                while _j < len(_enriched):
                    _key, _path, _orient = _enriched[_j]
                    _n = int(_key.replace("photo_", ""))
                    if _orient == "horizontal":
                        # Попробуем взять следующее горизонтальное для пары
                        if (_j + 1 < len(_enriched) and
                                _enriched[_j + 1][2] == "horizontal"):
                            _k2, _p2, _ = _enriched[_j + 1]
                            _n2 = int(_k2.replace("photo_", ""))
                            _photo_pages.append([(_n, _path, "horizontal"),
                                                 (_n2, _p2, "horizontal")])
                            _j += 2
                            continue
                    # vertical / square / unknown / одиночный horizontal → 1 на страницу
                    _photo_pages.append([(_n, _path, _orient)])
                    _j += 1

                # Секция-заголовок
                story.append(PageBreak())
                story.append(PlatPara("ФОТОГРАФИИ", ParagraphStyle(
                    "ph_title", fontName=SANS_FONT_BOLD, fontSize=17,
                    textColor=HexColor("#3d2e1f"), leading=21, spaceAfter=4)))
                story.append(HRFlowable(width="100%", thickness=1,
                                        color=HexColor("#c4a070"), spaceAfter=12))

                # Рендерим каждую «страницу» фотораздела
                for _page_photos in _photo_pages:
                    if len(_page_photos) == 2:
                        # Два горизонтальных стопкой
                        _n1, _p1, _ = _page_photos[0]
                        _n2, _p2, _ = _page_photos[1]
                        _t1 = _ph_style(_single_placeholder(_n1, _p1, self.TW, _L_H))
                        _t2 = _ph_style(_single_placeholder(_n2, _p2, self.TW, _L_H))
                        story.append(_t1)
                        story.append(Spacer(1, 6))
                        story.append(_t2)
                        story.append(PageBreak())
                    else:
                        # Одно фото (vertical / unknown): full-width
                        _n1, _p1, _or = _page_photos[0]
                        _h = _V_H if _or == "vertical" else _L_H
                        _t1 = _ph_style(_single_placeholder(_n1, _p1, self.TW, _h))
                        story.append(_t1)
                        story.append(PageBreak())

        # ── Пост-обработка: KeepTogether для section_header + следующий абзац ──
        # Более надёжно, чем keepWithNext=True на уровне атрибута
        processed_story: list = []
        i = 0
        while i < len(story):
            item = story[i]
            if (getattr(item, "keepWithNext", False) and
                    i + 1 < len(story) and
                    not isinstance(story[i + 1], PageBreak)):
                # Собираем header + до 3 следующих не-PageBreak элементов
                group = [item]
                j = i + 1
                while j < len(story) and len(group) <= 3 and not isinstance(story[j], (PageBreak,)):
                    group.append(story[j])
                    j += 1
                processed_story.append(KeepTogether(group))
                i = j
            else:
                processed_story.append(item)
                i += 1

        # ── Сборка документа ──
        class _PageNumCanvas(rl_canvas.Canvas):
            """Добавляет номер страницы внизу по центру."""
            def __init__(self_, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self_._saved_page_states = []

            def showPage(self_):
                self_._saved_page_states.append(dict(self_.__dict__))
                self_._startPage()

            def save(self_):
                num_pages = len(self_._saved_page_states)
                for state in self_._saved_page_states:
                    self_.__dict__.update(state)
                    self_._draw_page_number(num_pages)
                    super().showPage()
                super().save()

            def _draw_page_number(self_, count):
                self_.setFont(SANS_FONT, 8)
                self_.setFillColor(HexColor("#888888"))
                self_.drawCentredString(A5[0] / 2, 12 * mm, str(self_._pageNumber))

        def _make_bg_canvas(*args, **kwargs):
            canvas_obj = _PageNumCanvas(*args, **kwargs)
            return canvas_obj

        doc = SimpleDocTemplate(
            str(self.output),
            pagesize=A5,
            leftMargin=self.ML,
            rightMargin=self.MR,
            topMargin=self.MT,
            bottomMargin=self.MB + 8 * mm,  # extra space for page numbers
        )

        # Фоновый цвет страницы через onPage callback
        def _on_page(c, doc):
            c.saveState()
            c.setFillColor(BG)
            c.rect(0, 0, A5[0], A5[1], fill=1, stroke=0)
            c.restoreState()

        from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame
        frame = Frame(self.ML, self.MB + 8 * mm, self.TW, self.TH, id="main")
        tmpl  = PageTemplate(id="main", frames=[frame], onPage=_on_page)
        doc2  = BaseDocTemplate(
            str(self.output),
            pagesize=A5,
            leftMargin=self.ML,
            rightMargin=self.MR,
            topMargin=self.MT,
            bottomMargin=self.MB + 8 * mm,
        )
        doc2.addPageTemplates([tmpl])
        doc2.build(processed_story, canvasmaker=_PageNumCanvas)

        kb = self.output.stat().st_size // 1024
        n_story = len(story)
        print(f"[RENDERER] ✅  PDF (story): {self.output.name} ({kb} KB, {n_story} элементов)")
        return self.output

    # ── Utilities ────────────────────────────────────────────────────────────

    def _fill_bg(self, c, color_hex: str | None = None):
        c.setFillColor(HexColor(color_hex or self.c_bg))
        c.rect(0, 0, self.W, self.H, fill=1, stroke=0)

    def _draw_footer(self, c, page_num: int | None = None, text: str | None = None):
        y = self.MB * 0.45
        c.setFont(SANS_FONT, 7)
        c.setFillColor(HexColor(self.c_secondary))
        label = str(page_num) if page_num else (text or "")
        if label:
            c.drawCentredString(self.W / 2, y, label)

    def _visible_page_num(self, page: dict) -> int | None:
        """User-visible numbering: cover hidden, TOC starts at 1."""
        ptype = (page.get("type") or "").strip().lower()
        pnum = page.get("page_number")
        if not isinstance(pnum, int):
            return None
        if ptype == "cover":
            return None
        # physical 2 (TOC) -> visible 1, physical 3 -> visible 2, ...
        return max(1, pnum - 1)

    def _toc_visible_target(self, raw_page: object) -> str:
        """Normalize TOC target pages to visible numbering."""
        if isinstance(raw_page, int):
            return str(max(1, raw_page - 1)) if raw_page >= 2 else str(raw_page)
        if isinstance(raw_page, str):
            s = raw_page.strip()
            if s.isdigit():
                n = int(s)
                return str(max(1, n - 1)) if n >= 2 else str(n)
            return s
        return ""

    def _filter_pages_for_mode(self, pages: list[dict]) -> list[dict]:
        filtered: list[dict] = []
        for page in pages:
            ptype = (page.get("type") or "").strip()
            if ptype == "cover" and not self.options.with_cover:
                continue
            if self.options.text_only and ptype in ("photo_section", "photo_section_start", "full_page_photo"):
                continue
            if self.options.no_photos and ptype in ("photo_section", "photo_section_start", "full_page_photo"):
                continue
            page_copy = copy.deepcopy(page)
            page_copy["elements"] = self._filter_elements_for_mode(page_copy)
            filtered.append(page_copy)
        return filtered

    def _filter_elements_for_mode(self, page: dict) -> list[dict]:
        ptype = (page.get("type") or "").strip()
        chapter_id = (page.get("chapter_id") or "").strip()
        out: list[dict] = []
        for elem in page.get("elements", []):
            etype = (elem.get("type") or "").strip()

            if self.options.text_only:
                if etype == "bio_data_block":
                    if self.options.with_bio_block and chapter_id == "ch_01":
                        out.append(elem)
                    continue
                if etype in ("callout", "historical_note", "photo", "photo_pair", "photo_single", "cover_portrait"):
                    continue
                if etype in ("background_rect", "decorative_line", "cover_logo", "cover_surname", "cover_first_name",
                             "cover_title", "cover_subtitle", "cover_years", "cover_description"):
                    continue
                out.append(elem)
                continue

            if self.options.no_photos and etype in ("photo", "photo_pair", "photo_single"):
                # Для ворот 2c оставляем плейсхолдер фото только на chapter_start.
                if ptype == "chapter_start":
                    out.append({
                        "type": "photo_placeholder",
                        "label": "[ФОТО — начало главы]",
                        "layout": elem.get("layout", "full_width"),
                    })
                continue

            out.append(elem)
        return out

    def _is_text_page(self, page: dict) -> bool:
        return page.get("type", "") in (
            "text", "text_only", "text_with_photo", "text_with_photos",
            "text_with_callouts", "text_with_callout", "text_with_bio", "text_with_sidebar",
        )

    def _elem_para_text(self, elem: dict) -> str:
        """Возвращает текст абзаца (новый ref-формат, legacy paragraph_id, или legacy text)."""
        ch_id = elem.get("chapter_id", "")
        # v3.20+: paragraph_ref — новый канонический формат
        par_ref = elem.get("paragraph_ref", "")
        # v3.19 legacy: paragraph_id — обратная совместимость
        par_id = elem.get("paragraph_id", "") or par_ref
        if ch_id and par_id:
            text = self.book_index.get(ch_id, par_id)
            if text is not None:
                self._ref_resolved += 1
                return text
            # ref не найден в book_index
            self._ref_missing += 1
            if self.options.strict_refs and not self.options.allow_missing_refs:
                raise ValueError(f"[RENDERER] strict_refs: paragraph_ref '{ch_id}/{par_id}' not found in book_FINAL")
        # Legacy fallback: inline text (deprecated)
        legacy_text = elem.get("text", "")
        if legacy_text and (ch_id or par_id):
            print(f"[RENDERER] ⚠️  legacy text fallback: {ch_id}/{par_id} — используется inline text")
        return legacy_text

    def _elem_callout_text(self, elem: dict) -> str:
        """Возвращает текст выноски: ref → book.callouts; иначе legacy inline text/content.

        v3.21+:    {type: callout, chapter_id, callout_ref: "callout_01"}
        Legacy:    {type: callout, callout_id: "callout_01", text: "..."}
        Inline:    {type: callout, text/content: "..."} — старые сохранённые layout'ы
        """
        # v3.21+: callout_ref — новый канонический формат
        co_ref = elem.get("callout_ref", "")
        # Legacy: callout_id — присутствует в текущих сохранённых layout'ах
        co_id = elem.get("callout_id", "") or co_ref
        if co_id:
            text = self.book_index.get_callout(co_id)
            if text is not None:
                return text
            if self.options.strict_refs and not self.options.allow_missing_refs:
                raise ValueError(f"[RENDERER] strict_refs: callout_ref '{co_id}' not found in book_FINAL.callouts")
        # Legacy fallback: inline text/content (deprecated)
        legacy_text = elem.get("content") or elem.get("text", "")
        if legacy_text and co_id:
            print(f"[RENDERER] ⚠️  legacy callout text fallback: '{co_id}' — используется inline text")
        return legacy_text

    def _elem_historical_note_text(self, elem: dict) -> str:
        """Возвращает текст исторической справки: ref → book.historical_notes; иначе legacy inline.

        v3.21+:    {type: historical_note, chapter_id, historical_note_ref: "hist_01"}
        Inline:    {type: historical_note, text/content: "..."} — все сохранённые layout'ы до v3.21
        """
        # v3.21+: historical_note_ref — новый канонический формат
        hn_ref = elem.get("historical_note_ref", "") or elem.get("note_ref", "")
        # Legacy id field (на случай если LD когда-либо ставил его)
        hn_id = elem.get("note_id", "") or hn_ref
        if hn_id:
            text = self.book_index.get_historical_note(hn_id)
            if text is not None:
                return text
            if self.options.strict_refs and not self.options.allow_missing_refs:
                raise ValueError(f"[RENDERER] strict_refs: historical_note_ref '{hn_id}' not found in book_FINAL.historical_notes")
        # Legacy fallback: inline text/content (deprecated)
        legacy_text = elem.get("content") or elem.get("text", "")
        if legacy_text and hn_id:
            print(f"[RENDERER] ⚠️  legacy historical_note text fallback: '{hn_id}' — используется inline text")
        return legacy_text

    def _paragraph_count(self, page: dict) -> int:
        return sum(
            1 for e in page.get("elements", [])
            if e.get("type") == "paragraph" and self._elem_para_text(e).strip()
        )

    def _is_last_page_of_chapter(self, idx: int) -> bool:
        if idx >= len(self.pages) - 1:
            return True
        cur = self.pages[idx]
        nxt = self.pages[idx + 1]
        cur_ch = cur.get("chapter_id")
        nxt_ch = nxt.get("chapter_id")
        if cur_ch and nxt_ch and cur_ch != nxt_ch:
            return True
        if nxt.get("type") in ("chapter_start", "photo_section_start", "photo_section", "cover", "toc"):
            return True
        return False

    def _pop_leading_transfer_chunk(self, elements: list[dict]) -> list[dict]:
        """Забирает безопасный переносимый блок из начала следующей страницы.

        - paragraph -> переносим 1 абзац
        - section_header + следующий paragraph -> переносим вместе (keepWithNext)
        """
        if not elements:
            return []
        first = elements[0]
        if first.get("type") == "paragraph" and self._elem_para_text(first).strip():
            return [elements.pop(0)]
        if first.get("type") == "section_header":
            chunk = [elements.pop(0)]
            if elements and elements[0].get("type") == "paragraph":
                chunk.append(elements.pop(0))
            return chunk
        return []

    # Оценочное количество символов на 85% заполненной A5-страницы
    # (A5 текстовое поле ~384pt × 482pt, 10pt шрифт, 16pt leading → ~30 строк × ~55 симв.)
    _CHARS_85PCT_PAGE = 1350

    def _page_para_chars(self, page: dict) -> int:
        """Суммарная длина текстов всех параграфов страницы (без пробелов по краям)."""
        return sum(
            len(self._elem_para_text(e).strip())
            for e in page.get("elements", [])
            if e.get("type") == "paragraph"
        )

    def _rebalance_text_pages(self):
        """Подтягивает абзацы со следующей страницы до достижения ≥85% заполнения.

        Алгоритм (char-based):
        - пропускаем последнюю страницу главы;
        - если суммарный объём символов на текущей странице < _CHARS_85PCT_PAGE
          и на следующей странице останется ≥2 абзаца после переноса — переносим.
        """
        for i in range(len(self.pages) - 1):
            cur = self.pages[i]
            nxt = self.pages[i + 1]
            if not self._is_text_page(cur) or not self._is_text_page(nxt):
                continue
            if self._is_last_page_of_chapter(i):
                continue
            if cur.get("chapter_id") and nxt.get("chapter_id") and cur.get("chapter_id") != nxt.get("chapter_id"):
                continue

            moved_any = False
            while self._page_para_chars(cur) < self._CHARS_85PCT_PAGE and self._paragraph_count(nxt) > 2:
                chunk = self._pop_leading_transfer_chunk(nxt.get("elements", []))
                if not chunk:
                    break
                cur.setdefault("elements", []).extend(chunk)
                moved_any = True

            if moved_any:
                print(f"[RENDERER] ℹ️  Уплотнение: стр.{cur.get('page_number','?')} "
                      f"({self._page_para_chars(cur)} симв.) ← стр.{nxt.get('page_number','?')}")

    def _photo_orientation(self, photo_id: str) -> str | None:
        path = self.photos.get(photo_id)
        if not path or not path.exists():
            return None
        try:
            from PIL import Image as PILImage
            with PILImage.open(path) as img:
                iw, ih = img.size
            if iw > ih:
                return "horizontal"
            if ih > iw:
                return "vertical"
            return "square"
        except Exception:
            return None

    def _draw_image(self, c, path: Path, x: float, y_top: float,
                    max_w: float, max_h: float, anchor: str = "nw") -> float:
        """Рисует изображение с сохранением пропорций. Возвращает фактическую высоту."""
        try:
            from PIL import Image as PILImage
            with PILImage.open(path) as img:
                iw, ih = img.size
            aspect = iw / ih
            w = min(max_w, max_h * aspect)
            h = w / aspect
            if anchor == "center":
                cx = x + (max_w - w) / 2
            else:
                cx = x
            c.drawImage(str(path), cx, y_top - h, width=w, height=h,
                        preserveAspectRatio=True, mask="auto")
            return h
        except Exception as e:
            print(f"[RENDERER] ⚠️  drawImage error {path.name}: {e}")
            return 0.0

    def _draw_portrait_no_bg(self, c, path: Path, x: float, y_top: float,
                             max_w: float, max_h: float,
                             tint_hex: str | None = None,
                             opacity: float = 1.0) -> float:
        """Рисует портрет-скетч с удалённым белым фоном.

        Убирает пиксели близкие к белому → делает их прозрачными в alpha-канале,
        затем вставляет PNG с mask="auto". Именно так работает remove_white_bg
        из Cover Designer v2.2 spec.
        """
        import io
        import tempfile
        from PIL import Image as PILImage

        try:
            with PILImage.open(path) as img:
                img = img.convert("RGBA")
                data = img.load()
                iw, ih = img.size

                # Порог: пиксели светлее 215/255 по всем каналам → прозрачные
                # 215 убирает near-white артефакты ink-sketch портретов (было 240)
                threshold = 215
                for py in range(ih):
                    for px in range(iw):
                        r, g, b, a = data[px, py]
                        if r >= threshold and g >= threshold and b >= threshold:
                            data[px, py] = (r, g, b, 0)

                # Опциональный тинт (тональное окрашивание)
                if tint_hex:
                    try:
                        tr = int(tint_hex[1:3], 16)
                        tg = int(tint_hex[3:5], 16)
                        tb = int(tint_hex[5:7], 16)
                        tinted = PILImage.new("RGBA", (iw, ih), (tr, tg, tb, 0))
                        tinted_data = tinted.load()
                        for py in range(ih):
                            for px in range(iw):
                                r, g, b, a = data[px, py]
                                if a > 0:
                                    nr = int(r * (1 - 0.3) + tr * 0.3)
                                    ng = int(g * (1 - 0.3) + tg * 0.3)
                                    nb = int(b * (1 - 0.3) + tb * 0.3)
                                    data[px, py] = (nr, ng, nb, a)
                    except Exception:
                        pass

                aspect = iw / ih
                w = min(max_w, max_h * aspect)
                h = w / aspect
                cx = x + (max_w - w) / 2  # центрируем

                # Сохраняем во временный PNG с прозрачностью
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    tmp_path = tmp.name
                img.save(tmp_path, format="PNG")

            c.saveState()
            if opacity < 1.0:
                c.setFillAlpha(opacity)
            c.drawImage(tmp_path, cx, y_top - h, width=w, height=h,
                        preserveAspectRatio=True, mask="auto")
            c.restoreState()

            # Убираем временный файл
            try:
                import os
                os.unlink(tmp_path)
            except Exception:
                pass

            return h

        except Exception as e:
            print(f"[RENDERER] ⚠️  _draw_portrait_no_bg error: {e}")
            return self._draw_image(c, path, x, y_top, max_w, max_h, "center")

    # ── Cover ─────────────────────────────────────────────────────────────────

    def _render_cover_line(self, c, elem: dict, y: float):
        """Рисует декоративную горизонтальную линию."""
        W = self.W
        w_mm   = elem.get("width_mm", 108)
        h_pt   = float(elem.get("height_pt", 0.5))
        color  = elem.get("color", self.c_accent)
        opacity = float(elem.get("opacity", 1.0))
        line_w  = w_mm * mm
        x_start = (W - line_w) / 2

        c.saveState()
        c.setStrokeColor(HexColor(color))
        if opacity < 1.0:
            c.setStrokeAlpha(opacity)
        c.setLineWidth(h_pt)
        c.line(x_start, y, x_start + line_w, y)
        c.restoreState()

    def _render_cover(self, c, page: dict):
        """Рендерит обложку data-driven из elements[].

        Поддерживает трёхзонную вёрстку (Cover Designer v2.2):
          • Зона A (top, 0–25%): surname + first_name + верхние декор.линии
          • Зона B (center, 25–80%): портрет
          • Зона C (bottom, 80–100%): years + subtitle + нижние декор.линии
        Совместимость с v1 (cover_surname/cover_first_name).
        """
        W, H = self.W, self.H
        elements = page.get("elements", [])

        # ── 1. Фон ────────────────────────────────────────────────────────────
        bg_color = self.c_bg
        for e in elements:
            if e.get("type") == "background_rect":
                bg_color = e.get("color", bg_color)
        self._fill_bg(c, bg_color)

        # ── 2. Границы зон (Cover Designer v2.2: A=0-25%, B=25-80%, C=80-100%)
        # ReportLab: y=0 снизу, y=H сверху
        zone_a_top = H                   # 100%
        zone_a_bot = H * 0.75            # 75% (= 25% сверху = 52.5mm)
        zone_b_top = zone_a_bot
        zone_b_bot = H * 0.20            # 20% (= 80% сверху = 168mm)
        zone_c_top = zone_b_bot
        zone_c_bot = 0.0

        # ── 3. Портрет (Зона B) ───────────────────────────────────────────────
        portrait: Path | None = self.portrait_path
        if portrait is None or not portrait.exists():
            portrait_elem = next((e for e in elements if e.get("type") == "cover_portrait"), {})
            portrait_file = portrait_elem.get("file", "")
            if portrait_file:
                for candidate in (ROOT / portrait_file, Path(portrait_file)):
                    if candidate.exists():
                        portrait = candidate
                        break

        if portrait and portrait.exists():
            zone_b_h = zone_b_top - zone_b_bot
            zone_b_w = W * 0.80
            pad_x = (W - zone_b_w) / 2

            # Читаем post_processing из JSON страницы (Cover Designer v2.2 spec)
            pp = page.get("post_processing", {})
            remove_bg  = pp.get("remove_background", True)   # по умолчанию всегда убираем
            tint_hex   = pp.get("tint_color", None)           # напр. "#5a4a38"
            pp_opacity = pp.get("target_opacity", 1.0)

            if remove_bg:
                self._draw_portrait_no_bg(
                    c, portrait, pad_x, zone_b_top,
                    zone_b_w, zone_b_h,
                    tint_hex=tint_hex,
                    opacity=pp_opacity,
                )
            else:
                self._draw_image(c, portrait, pad_x, zone_b_top, zone_b_w, zone_b_h, "center")

        # ── 4. Зона A (сверху) — декоративные линии и текст ──────────────────
        # Декоративные линии с position="top" или zone="top"
        for e in elements:
            if e.get("type") != "decorative_line":
                continue
            pos = e.get("position", e.get("zone", ""))
            if pos == "top":
                y_off = e.get("y_offset_mm", 8)
                self._render_cover_line(c, e, H - y_off * mm)

        # Текстовые элементы зоны A — позиционируем относительно зоны
        # Собираем их в порядке: surname → first_name
        top_text_order = [
            ("cover_surname",    "cover_title"),
            ("cover_first_name", "cover_subtitle"),
        ]
        # y_cursor: начинаем ниже декоративной линии (~12% от верха → 88% H)
        y_cur = H * 0.88
        margin_extra = 0.0

        for keys in top_text_order:
            elem = next(
                (e for e in elements if e.get("type") in keys),
                None,
            )
            if not elem:
                continue
            text = elem.get("text", "")
            if not text:
                continue

            font, fsize = _elem_font(elem, BODY_BOLD_FONT if "surname" in elem.get("type","") or "title" in elem.get("type","") else BODY_ITALIC_FONT)
            ls = float(elem.get("letter_spacing") or elem.get("letter_spacing_px") or 0)
            color = elem.get("color", "#3d2e1f")
            mt = float(elem.get("margin_top") or elem.get("margin_top_pt") or 0)

            y_cur -= mt + margin_extra
            c.setFont(font, fsize)
            c.setFillColor(HexColor(color))
            _draw_spaced_string(c, text, W / 2, y_cur - fsize, ls, align="center")
            y_cur -= fsize * 1.3
            margin_extra = 4.0  # небольшой дополнительный зазор между строками

        # ── 5. Зона C (снизу) ─────────────────────────────────────────────────
        # Текстовые элементы зоны C (cover_years, cover_subtitle для зоны bottom)
        bottom_text_elems = [
            e for e in elements
            if e.get("type") in ("cover_years", "cover_description")
            or (e.get("type") == "cover_subtitle" and e.get("zone") == "bottom")
        ]
        y_bot = zone_c_top - 6 * mm  # начинаем чуть ниже границы зоны C
        for e in bottom_text_elems:
            text = e.get("text", "")
            if not text:
                continue
            font, fsize = _elem_font(e, SANS_FONT)
            ls = float(e.get("letter_spacing") or e.get("letter_spacing_px") or 0)
            color = e.get("color", self.c_accent)
            mt = float(e.get("margin_top") or e.get("margin_top_pt") or 0)

            y_bot -= mt
            c.setFont(font, fsize)
            c.setFillColor(HexColor(color))
            _draw_spaced_string(c, text, W / 2, y_bot - fsize, ls, align="center")
            y_bot -= fsize * 1.5

        # Декоративные линии зоны C
        for e in elements:
            if e.get("type") != "decorative_line":
                continue
            pos = e.get("position", e.get("zone", ""))
            if pos == "bottom":
                y_off = e.get("y_offset_mm", 4)
                # y_offset_mm — от верхней границы зоны C (168mm от верха → H*0.20)
                self._render_cover_line(c, e, zone_c_top - y_off * mm)

        # ── 6. Лого / подпись издателя ────────────────────────────────────────
        lg_e = next((e for e in elements if e.get("type") == "cover_logo"), {})
        logo_text = lg_e.get("text", "")
        if logo_text:
            font, fsize = _elem_font(lg_e, SANS_BOLD_FONT, 9.0)
            c.setFont(font, fsize)
            c.setFillColor(HexColor(lg_e.get("color", self.c_accent)))
            c.drawCentredString(W / 2, H * 0.05, logo_text)

    # ── Blank ─────────────────────────────────────────────────────────────────

    def _render_blank(self, c, page: dict):
        self._fill_bg(c)
        # Тонкий орнамент по центру — маркирует страницу, не перегружая её
        c.saveState()
        c.setStrokeColor(HexColor(self.c_accent))
        c.setStrokeAlpha(0.35)
        c.setLineWidth(0.4)
        orn_y = self.H / 2
        c.line(self.W * 0.38, orn_y, self.W * 0.62, orn_y)
        c.restoreState()
        for e in page.get("elements", []):
            if e.get("type") == "footer_text":
                self._draw_footer(c, text=e.get("text", ""))

    # ── TOC ───────────────────────────────────────────────────────────────────

    def _render_toc(self, c, page: dict):
        self._fill_bg(c)
        y = self.TY

        c.setFillColor(HexColor(self.heading_color))
        c.setFont(SANS_BOLD_FONT, self.chapter_size)
        c.drawString(self.TX, y - self.chapter_size, "Содержание")
        y -= self.chapter_size + 14

        c.setStrokeColor(HexColor(self.c_divider))
        c.setLineWidth(0.5)
        c.line(self.TX, y, self.TX + self.TW, y)
        y -= 14

        for item in page.get("items", []):
            title = item.get("title", "")
            pg = self._toc_visible_target(item.get("page", ""))
            if not title or y < self.MB + 6:
                break
            c.setFillColor(HexColor(self.c_text))
            c.setFont(BODY_FONT, self.body_size + 1)
            c.drawString(self.TX, y, title)
            c.setFillColor(HexColor(self.c_secondary))
            c.drawRightString(self.TX + self.TW, y, str(pg))
            y -= (self.body_size + 1) * 1.9

        self._draw_footer(c, page_num=self._visible_page_num(page))

    # ── Full-page photo ───────────────────────────────────────────────────────

    def _render_full_page_photo(self, c, page: dict):
        self._fill_bg(c, "#111111")
        photo_id   = page.get("photo_id", "")
        photo_path = self.photos.get(photo_id)
        caption    = page.get("caption") or self.photo_captions.get(photo_id, "")

        if photo_path and photo_path.exists():
            cap_reserve = 18 if caption else 0
            pad = 6 * mm
            h = self._draw_image(
                c, photo_path, pad, self.H - pad - cap_reserve,
                self.W - pad * 2, self.H - pad * 2 - cap_reserve, "center",
            )
        else:
            print(f"[RENDERER] ⚠️  Фото не найдено: {photo_id}")

        if caption:
            c.setFillColor(HexColor(self.caption_color))
            c.setFont(SANS_FONT, self.caption_size)
            c.drawCentredString(self.W / 2, 10, caption)

    # ── Chapter start ─────────────────────────────────────────────────────────

    def _render_chapter_start(self, c, page: dict):
        self._fill_bg(c)
        ch_num   = page.get("chapter_number", "")
        ch_title = page.get("chapter_title", "")
        y = self.TY - 6

        if ch_num:
            c.setFillColor(HexColor(self.c_accent))
            c.setFont(SANS_FONT, 8)
            c.drawString(self.TX, y, f"Глава {ch_num}")
            y -= 13

        # Заголовок главы
        c.setFillColor(HexColor(self.heading_color))
        c.setFont(SANS_BOLD_FONT, self.chapter_size)
        para = make_para(ch_title, SANS_BOLD_FONT, self.chapter_size,
                         self.heading_color, self.chapter_size * 1.2, TA_LEFT)
        ph = draw_para(c, para, self.TX, y, self.TW, self.TH)
        y -= ph + 10

        # Декоративная линия
        c.setStrokeColor(HexColor(self.c_accent))
        c.setLineWidth(1.5)
        c.line(self.TX, y, self.TX + 28 * mm, y)
        y -= 20

        # Элементы главы: bio_data_block рендерим отдельно, остальное через _render_elements
        for elem in page.get("elements", []):
            if elem.get("type") == "bio_data_block":
                y = self._render_bio_data_block(c, elem, y)
            elif elem.get("type") == "photo" and elem.get("layout") in ("wrap_right", "wrap_left"):
                # wrap-фото на chapter_start — строим двухколонный блок из оставшихся параграфов
                other_elems = [e for e in page.get("elements", [])
                               if e is not elem and e.get("type") == "paragraph"]
                y = self._render_wrap_table(c, elem, other_elems, y)
                break
            else:
                y = self._render_elements(c, [elem], y)

        self._draw_footer(c, page_num=self._visible_page_num(page))

    # ── Text pages ────────────────────────────────────────────────────────────

    def _render_text_page(self, c, page: dict):
        self._fill_bg(c)
        elements = page.get("elements", [])

        # Найти wrap-фото
        wrap_photo = None
        wrap_idx   = -1
        for i, e in enumerate(elements):
            if e.get("type") == "photo" and e.get("layout") in ("wrap_right", "wrap_left"):
                # Правило Art Director v1.7: wrap только для вертикальных фото.
                # Если фото горизонтальное — принудительно full_width.
                pid  = e.get("photo_id", "")
                path = self.photos.get(pid)
                is_horizontal = False
                if path and path.exists():
                    try:
                        from PIL import Image as PILImage
                        with PILImage.open(path) as img:
                            iw, ih = img.size
                        is_horizontal = iw > ih
                    except Exception:
                        pass
                if is_horizontal:
                    e = dict(e, layout="full_width")  # не мутируем оригинал
                    elements = list(elements)
                    elements[i] = e
                    print(f"[RENDERER] ℹ️  {pid} горизонтальное → принудительно full_width (wrap запрещён)")
                else:
                    wrap_photo = e
                    wrap_idx   = i
                break

        y = self.TY

        if wrap_photo is not None:
            before      = elements[:wrap_idx]
            after       = elements[wrap_idx + 1:]

            # Элементы ДО фото (не-параграфы) — на полную ширину
            y = self._render_elements(c, [e for e in before if e.get("type") != "paragraph"], y)
            # Параграфы до фото — идут в колонку
            paras_before = [e for e in before if e.get("type") == "paragraph"]

            # Если photo-элемент содержит явный split (новый формат Даши):
            beside_texts = wrap_photo.get("text_beside_photo", [])
            after_texts  = wrap_photo.get("text_after_photo",  [])

            if beside_texts:
                # Новый формат: тексты прямо в photo-элементе
                beside_paras = [{"type": "paragraph", "text": t} for t in beside_texts if t]
                after_paras  = [{"type": "paragraph", "text": t} for t in after_texts  if t]
                other_after  = [e for e in after if e.get("type") not in ("paragraph",)]
            else:
                # Старый формат: все параграфы страницы — разбиваем эвристикой
                # Первые 2–3 параграфа → в колонку рядом с фото; остальные → полная ширина
                all_paras = paras_before + [e for e in after if e.get("type") == "paragraph"]
                split_at  = min(3, max(1, len(all_paras) - 1)) if len(all_paras) > 2 else len(all_paras)
                beside_paras = all_paras[:split_at]
                after_paras  = all_paras[split_at:]
                other_after  = [e for e in after if e.get("type") not in ("paragraph",)]

            # Двухколонный блок
            y = self._render_wrap_table(c, wrap_photo, beside_paras, y)

            # Параграфы на полную ширину после фото
            for p in after_paras:
                y = self._render_paragraph(c, p, y)

            # Callouts, historical_notes и прочее на полную ширину
            y = self._render_elements(c, other_after, y)

        else:
            # Нет wrap-фото — всё рендерим обычно
            y = self._render_elements(c, elements, y)

        self._draw_footer(c, page_num=self._visible_page_num(page))

    # ── Two-column photo table ────────────────────────────────────────────────

    def _render_wrap_table(self, c, photo_elem: dict, para_elems: list, y: float) -> float:
        """Рисует фото и параграфы в две колонки (как wrap_right/wrap_left)."""
        from reportlab.platypus import Table, TableStyle

        photo_id = photo_elem.get("photo_id", "")
        layout   = photo_elem.get("layout", "wrap_right")
        caption  = photo_elem.get("caption") or self.photo_captions.get(photo_id, "")

        gap       = 14          # visual gap between text column and photo column
        photo_w   = self.TW * 0.42
        text_w    = self.TW - photo_w  # full width; gap applied via cell padding below
        avail_h   = y - self.MB - 10

        # ── Фото-ячейка
        photo_path = self.photos.get(photo_id)
        photo_cell_items: list = []
        if photo_path and photo_path.exists():
            try:
                from PIL import Image as PILImage
                with PILImage.open(photo_path) as img:
                    iw, ih = img.size
                aspect = iw / ih
                ph = min(photo_w / aspect, avail_h * 0.85)
                pw = ph * aspect
                photo_cell_items.append(
                    RLImage(str(photo_path), width=pw, height=ph)
                )
            except Exception:
                photo_cell_items.append(
                    make_para(f"[{photo_id}]", SANS_FONT, 8, "#999999")
                )
        else:
            print(f"[RENDERER] ⚠️  Фото не найдено: {photo_id}")
            photo_cell_items.append(make_para(f"[{photo_id}]", SANS_FONT, 8, "#999999"))

        if caption:
            photo_cell_items.append(Spacer(1, 4))
            photo_cell_items.append(
                make_para(caption, SANS_FONT, self.caption_size,
                          self.caption_color, self.caption_size * 1.3, TA_CENTER)
            )

        # ── Текстовая ячейка
        text_cell_items: list = []
        for pe in para_elems:
            txt = self._elem_para_text(pe)
            if not txt:
                continue
            text_cell_items.append(
                make_para(txt, BODY_FONT, self.body_size, self.body_color,
                          self.body_lead, TA_JUSTIFY)
            )
            text_cell_items.append(Spacer(1, self.para_space))

        if not text_cell_items:
            text_cell_items = [Spacer(1, 1)]
        if not photo_cell_items:
            photo_cell_items = [Spacer(1, 1)]

        # ── Сборка таблицы
        if layout == "wrap_right":
            data       = [[text_cell_items, photo_cell_items]]
            col_widths = [text_w, photo_w]
        else:  # wrap_left
            data       = [[photo_cell_items, text_cell_items]]
            col_widths = [photo_w, text_w]

        tbl = Table(data, colWidths=col_widths)
        # Inter-column gap via cell padding: text column gets padding on the side facing the photo
        if layout == "wrap_right":
            gap_style = ("RIGHTPADDING", (0, 0), (0, -1), gap)   # text=col0, photo=col1
        else:
            gap_style = ("LEFTPADDING",  (1, 0), (1, -1), gap)   # photo=col0, text=col1
        tbl.setStyle(TableStyle([
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING",    (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ("LEFTPADDING",   (0, 0), (-1, -1), 0),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
            gap_style,
        ]))

        # Top spacer before the wrap block
        y -= 4 * mm

        tw, th = tbl.wrap(self.TW, avail_h)
        if th > avail_h:
            th = avail_h  # обрезаем если не влезает
        tbl.drawOn(c, self.TX, y - th)
        return y - th - 6 * mm  # bottom spacer after wrap block

    # ── Elements renderer ─────────────────────────────────────────────────────

    def _render_elements(self, c, elements: list, y: float) -> float:
        for elem in elements:
            if y < self.MB + 15:
                break
            etype = elem.get("type", "")
            if etype == "paragraph":
                y = self._render_paragraph(c, elem, y)
            elif etype in ("subheading", "section_header"):
                y = self._render_subheading(c, elem, y)
            elif etype == "photo":
                y = self._render_photo_elem(c, elem, y)
            elif etype == "photo_pair":
                y = self._render_photo_pair(c, elem, y)
            elif etype == "callout":
                y = self._render_callout(c, elem, y)
            elif etype == "historical_note":
                y = self._render_historical(c, elem, y)
            elif etype == "decorative_line":
                y = self._render_inline_line(c, elem, y)
            elif etype == "photo_placeholder":
                y = self._render_photo_placeholder(c, elem, y)
            elif etype == "background_rect":
                pass  # фон уже установлен в _fill_bg, здесь пропускаем
        return y

    def _render_photo_placeholder(self, c, elem: dict, y: float) -> float:
        """Плейсхолдер под фото для ворот 2c (--no-photos)."""
        avail_h = y - self.MB - 20
        max_h = min(avail_h * 0.55, self.TW * 0.65)
        h = max(40 * mm, max_h)
        h = min(h, avail_h)
        if h <= 0:
            return y
        x = self.TX
        w = self.TW
        y_bottom = y - h
        c.saveState()
        c.setFillColor(HexColor("#f1f1f1"))
        c.rect(x, y_bottom, w, h, fill=1, stroke=0)
        c.setStrokeColor(HexColor("#9a9a9a"))
        c.setLineWidth(1.0)
        c.rect(x, y_bottom, w, h, fill=0, stroke=1)
        c.line(x, y_bottom, x + w, y)
        c.line(x, y, x + w, y_bottom)
        c.setFillColor(HexColor("#666666"))
        c.setFont(SANS_FONT, 9)
        label = elem.get("label") or "[ФОТО — начало главы]"
        c.drawCentredString(x + w / 2, y_bottom + h / 2 - 4, label)
        c.restoreState()
        return y_bottom - self.photo_margin

    def _render_paragraph(self, c, elem: dict, y: float) -> float:
        import re as _re
        # v3.20+: paragraph_ref — новый канонический формат
        # v3.19 legacy: paragraph_id — обратная совместимость
        ch_id   = elem.get("chapter_id", "")
        par_ref = elem.get("paragraph_ref", "")
        par_id  = elem.get("paragraph_id", "") or par_ref
        if ch_id and par_id:
            text = self.book_index.get(ch_id, par_id)
            if text is None:
                if self.options.strict_refs and not self.options.allow_missing_refs:
                    raise ValueError(
                        f"[RENDERER] strict_refs: paragraph_ref '{ch_id}/{par_id}' not found in book_FINAL"
                    )
                self._ref_missing += 1
                print(f"[RENDERER] ⚠️  paragraph не найден: {ch_id}/{par_id} — пропускаем")
                return y
            # Если элемент хранится как subheading в book_index — рендерим как подзаголовок
            elem_type = self.book_index.get_type(ch_id, par_id)
            if elem_type == "subheading":
                self._ref_resolved += 1
                return self._render_subheading(c, {"text": text}, y)
            self._ref_resolved += 1
        else:
            # Legacy-формат: текст прямо в элементе
            text = elem.get("text", "")
            if text:
                print(f"[RENDERER] ⚠️  legacy text fallback на странице без chapter/para ref")
        if not text:
            return y
        # ## / ### Подзаголовок — legacy handling для книг без prepare_book_for_layout
        if text.strip().startswith("## ") or text.strip().startswith("### "):
            prefix_len = 3 if text.strip().startswith("## ") else 4
            return self._render_subheading(c, {"text": text.strip()[prefix_len:].strip()}, y)
        # Если весь текст — это markdown-заголовок (**Текст**) — рендерим как subheading
        m = _re.match(r'^\*{1,3}(.+?)\*{1,3}$', text.strip())
        if m:
            return self._render_subheading(c, {"text": m.group(1).strip()}, y)
        # Стриппинг inline **bold** и *italic* маркеров
        text = _re.sub(r'\*{1,3}(.+?)\*{1,3}', r'\1', text)
        para = make_para(text, BODY_FONT, self.body_size, self.body_color,
                         self.body_lead, TA_JUSTIFY)
        h = draw_para(c, para, self.TX, y, self.TW, y - self.MB)
        return y - h - self.para_space

    def _render_photo_elem(self, c, elem: dict, y: float) -> float:
        photo_id   = elem.get("photo_id", "")
        layout     = elem.get("layout", "full_width")
        caption    = elem.get("caption") or self.photo_captions.get(photo_id, "")
        photo_path = self.photos.get(photo_id)
        avail_h    = y - self.MB - 20
        cap_h      = (self.caption_size + 6) if caption else 0

        if layout == "full_page":
            max_h = min(avail_h * 0.85, self.TH * 0.82)
            max_w = self.TW
        elif layout in ("wrap_right", "wrap_left"):
            # Уже обработано через _render_wrap_table; здесь fallback как full_width
            max_h = min(avail_h * 0.55, self.TW * 0.65)
            max_w = self.TW
        else:  # full_width
            max_h = min(avail_h * 0.55, self.TW * 0.65)
            max_w = self.TW

        if photo_path and photo_path.exists():
            h = self._draw_image(c, photo_path, self.TX, y, max_w, max_h, "center")
        else:
            print(f"[RENDERER] ⚠️  Фото не найдено: {photo_id}")
            h = 0.0

        if caption and h > 0:
            c.setFont(SANS_FONT, self.caption_size)
            c.setFillColor(HexColor(self.caption_color))
            c.drawCentredString(self.TX + self.TW / 2, y - h - 10, caption)
            return y - h - cap_h - self.photo_margin

        return y - h - self.photo_margin

    def _render_photo_pair(self, c, elem: dict, y: float) -> float:
        photos   = elem.get("photos", [])
        captions = elem.get("captions", [])
        avail_h  = y - self.MB - 20
        pair_h   = min(self.TW * 0.55, avail_h * 0.5)
        ph_w     = (self.TW - self.photo_margin) / 2

        for i, pid in enumerate(photos[:2]):
            path = self.photos.get(pid)
            px   = self.TX + i * (ph_w + self.photo_margin)
            if path and path.exists():
                self._draw_image(c, path, px, y, ph_w, pair_h, "nw")
            cap = captions[i] if i < len(captions) else self.photo_captions.get(pid, "")
            if cap:
                c.setFont(SANS_FONT, self.caption_size)
                c.setFillColor(HexColor(self.caption_color))
                c.drawCentredString(px + ph_w / 2, y - pair_h - 10, cap[:60])

        cap_h = self.caption_size + 10 if any(captions) else 0
        return y - pair_h - cap_h - self.photo_margin

    def _render_subheading(self, c, elem: dict, y: float) -> float:
        """Рендерит структурный подзаголовок (subheading) — PT Sans Bold, кегль между body и chapter_title.

        Поддерживает два источника текста:
        1. subheading_ref + chapter_id → lookup через book_index (новая ссылочная архитектура)
        2. paragraph_ref / paragraph_id + chapter_id → тот же lookup
        3. inline text → legacy fallback
        """
        ch_id = elem.get("chapter_id", "")
        # Приоритет: subheading_ref > paragraph_ref > paragraph_id > text
        ref = (
            elem.get("subheading_ref", "")
            or elem.get("paragraph_ref", "")
            or elem.get("paragraph_id", "")
        )
        if ch_id and ref:
            text = self.book_index.get(ch_id, ref)
            if text is None:
                self._ref_missing += 1
                print(f"[RENDERER] ⚠️  subheading не найден: {ch_id}/{ref} — пропускаем")
                return y
            self._ref_resolved += 1
        else:
            text = elem.get("text", "")
        if not text:
            return y
        font, fsize = _elem_font(elem, SANS_BOLD_FONT, self.section_size)
        color = elem.get("color", self.heading_color)
        para = make_para(text, font, fsize, color, fsize * 1.3, TA_LEFT)
        y -= self.para_space * 0.5
        h = draw_para(c, para, self.TX, y, self.TW, y - self.MB)
        return y - h - self.para_space

    def _render_section_header(self, c, elem: dict, y: float) -> float:
        """Рендерит подзаголовок раздела (section_header) — PT Sans, кегль 13–14."""
        text = elem.get("text", "")
        if not text:
            return y
        font, fsize = _elem_font(elem, SANS_BOLD_FONT, self.section_size)
        color = elem.get("color", self.heading_color)
        para = make_para(text, font, fsize, color, fsize * 1.3, TA_LEFT)
        y -= self.para_space * 0.5
        h = draw_para(c, para, self.TX, y, self.TW, y - self.MB)
        return y - h - self.para_space

    def _render_inline_line(self, c, elem: dict, y: float) -> float:
        """Рендерит горизонтальную декоративную линию внутри потока текста."""
        w_mm  = elem.get("width_mm", self.TW / mm)
        line_w = min(w_mm * mm, self.TW)
        x_start = self.TX + (self.TW - line_w) / 2
        h_pt  = float(elem.get("height_pt", 0.5))
        color = elem.get("color", self.c_divider)
        opacity = float(elem.get("opacity", 1.0))

        y -= self.para_space * 0.5
        c.saveState()
        c.setStrokeColor(HexColor(color))
        if opacity < 1.0:
            c.setStrokeAlpha(opacity)
        c.setLineWidth(h_pt)
        c.line(x_start, y, x_start + line_w, y)
        c.restoreState()
        return y - self.para_space

    def _render_callout(self, c, elem: dict, y: float) -> float:
        """Pull-quote: PT Serif Italic 13pt, линии сверху/снизу, подпись справа."""
        text = self._elem_callout_text(elem)
        if not text:
            return y
        pad     = self.callout_pad
        indent  = self.TW * 0.08          # боковые отступы для визуального сужения
        text_w  = self.TW - indent * 2

        # Обрамляем в кавычки если не начинается с «
        if not text.startswith(("\u00ab", "\u201c", "\u2014")):
            text = f"\u00ab{text}\u00bb"

        quote_size = 13.0
        quote_leading = quote_size * 1.65
        quote_para = make_para(
            text,
            BODY_ITALIC_FONT,
            quote_size,
            "#333333",
            quote_leading,
            TA_CENTER,
        )
        attr_para = make_para(
            "\u2014 из воспоминаний семьи",
            BODY_ITALIC_FONT,
            8.0,
            "#7a6a57",
            10.5,
            TA_RIGHT,
        )
        _, qh = quote_para.wrap(text_w, 9999)
        _, ah = attr_para.wrap(text_w, 9999)
        block_h = qh + ah + pad * 1.35

        if y - block_h < self.MB:
            return y

        line_color = HexColor(self.c_accent)

        # Верхняя линия
        c.setStrokeColor(line_color)
        c.setLineWidth(1.0)
        c.line(self.TX + indent, y, self.TX + self.TW - indent, y)

        # Текст + подпись
        text_top = y - pad * 0.55
        quote_para.drawOn(c, self.TX + indent, text_top - qh)
        attr_para.drawOn(c, self.TX + indent, text_top - qh - ah - 1.5)

        # Нижняя линия
        bot_y = y - block_h
        c.line(self.TX + indent, bot_y, self.TX + self.TW - indent, bot_y)

        return bot_y - self.para_space * 1.5

    def _render_historical(self, c, elem: dict, y: float) -> float:
        text = self._elem_historical_note_text(elem)
        if not text:
            return y
        top_bot_pad = 10.0
        side_pad = 14.0
        border_w = 2.0
        inner_x = self.TX + border_w + side_pad
        inner_w = self.TW - border_w - side_pad * 2

        label = make_para(
            "ИСТОРИЧЕСКАЯ СПРАВКА",
            SANS_BOLD_FONT,
            6.5,
            "#c4a070",
            8.6,
            TA_LEFT,
        )
        para = make_para(
            text,
            BODY_ITALIC_FONT,
            9.0,
            "#5a4a38",
            14.0,
            TA_LEFT,
        )
        _, lh = label.wrap(inner_w, 9999)
        _, th = para.wrap(inner_w, 9999)
        box_h = top_bot_pad + lh + 3 + th + top_bot_pad

        if y - box_h < self.MB:
            return y

        # Full-width within printable area + тёплый бежевый фон
        c.setFillColor(HexColor(self.c_hist_bg))
        c.rect(self.TX, y - box_h, self.TW, box_h, fill=1, stroke=0)
        # Левая золотая черта 2pt
        c.setFillColor(HexColor("#c4a070"))
        c.rect(self.TX, y - box_h, border_w, box_h, fill=1, stroke=0)

        text_top = y - top_bot_pad
        label.drawOn(c, inner_x, text_top - lh)
        para.drawOn(c, inner_x, text_top - lh - 3 - th)
        return y - box_h - self.para_space * 1.5

    def _render_bio_data_block(self, c, elem: dict, y: float) -> float:
        """Рендерит справочный блок гл. 01 (bio_data_block).

        Поддерживает два формата:
        - Новый (структурированный): sections[] с полями label/value
        - Старый (content str):  markdown-подобный текст — парсим в строки
        """
        sections = elem.get("sections", [])
        content = elem.get("content", "")

        # Layout JSON sometimes nests bio payload inside content dict.
        if isinstance(content, dict):
            if not sections and isinstance(content.get("sections"), list):
                sections = content.get("sections", [])
            content = content.get("content", "")
        if content is None:
            content = ""
        if not isinstance(content, str):
            content = json.dumps(content, ensure_ascii=False)

        label_font = SANS_FONT
        label_size = 7
        label_color = "#aaaaaa"
        val_font   = BODY_FONT
        val_size   = 8.5
        val_color  = "#222222"
        sec_font   = SANS_FONT
        sec_size   = 5.5
        sec_color  = self.c_accent
        row_gap    = 3

        col_label = self.TW * 0.36
        col_val   = self.TW * 0.64

        def _draw_row(yy, label_text, value_text):
            if yy < self.MB + 10:
                return yy
            lp = make_para(label_text.upper(), label_font, label_size, label_color,
                           label_size * 1.3, TA_LEFT)
            vp = make_para(value_text, val_font, val_size, val_color,
                           val_size * 1.4, TA_LEFT)
            _, lh = lp.wrap(col_label - 4, 9999)
            _, vh = vp.wrap(col_val - 4, 9999)
            row_h = max(lh, vh) + row_gap
            lp.drawOn(c, self.TX, yy - lh)
            vp.drawOn(c, self.TX + col_label, yy - vh)
            return yy - row_h

        def _draw_section_header(yy, title):
            if yy < self.MB + 10:
                return yy
            # Линия-разделитель над заголовком (кроме первой секции)
            c.setStrokeColor(HexColor("#ede6da"))
            c.setLineWidth(0.5)
            c.line(self.TX, yy, self.TX + self.TW, yy)
            yy -= 7
            sp = make_para(title.upper(), sec_font, sec_size, sec_color,
                           sec_size * 1.4, TA_LEFT)
            _, sh = sp.wrap(self.TW, 9999)
            sp.drawOn(c, self.TX, yy - sh)
            return yy - sh - 5

        if sections:
            # Структурированный формат
            first_section = True
            for sec in sections:
                sec_title = sec.get("title", "")
                if sec_title:
                    if not first_section:
                        y = _draw_section_header(y, sec_title)
                    else:
                        sp = make_para(sec_title.upper(), sec_font, sec_size, sec_color,
                                       sec_size * 1.4, TA_LEFT)
                        _, sh = sp.wrap(self.TW, 9999)
                        sp.drawOn(c, self.TX, y - sh)
                        y -= sh + 5
                    first_section = False
                for row in sec.get("rows", []):
                    y = _draw_row(y, row.get("label", ""), row.get("value", ""))
        else:
            # Старый формат: парсим content как markdown-подобный текст
            lines = content.split("\n")
            first_section = True
            for line in lines:
                line = line.strip()
                if not line:
                    y -= row_gap
                    continue
                # **Секция** или **Секция:** → заголовок раздела
                import re as _re2
                is_section_header = (
                    line.startswith("**") and line.endswith("**")
                )
                if is_section_header:
                    title = _re2.sub(r'\*+', '', line).rstrip(":").strip()
                    if not first_section:
                        y = _draw_section_header(y, title)
                    else:
                        sp = make_para(title.upper(), sec_font, sec_size, sec_color,
                                       sec_size * 1.4, TA_LEFT)
                        _, sh = sp.wrap(self.TW, 9999)
                        sp.drawOn(c, self.TX, y - sh)
                        y -= sh + 5
                    first_section = False
                elif ":" in line:
                    # «Метка: Значение»
                    idx = line.index(":")
                    lbl = line[:idx].strip("* —–").strip()
                    val = line[idx+1:].strip()
                    if lbl and val:
                        y = _draw_row(y, lbl, val)
                    elif lbl:
                        # Строка без значения — просто значение предыдущей метки
                        y = _draw_row(y, "", lbl)
                elif line.startswith("—") or line.startswith("-"):
                    # Пункт списка → одна строка значения
                    val = line.lstrip("—- ").strip()
                    if val:
                        p = make_para("— " + val, val_font, val_size, val_color,
                                      val_size * 1.4, TA_LEFT)
                        _, ph = p.wrap(self.TW - 8, 9999)
                        p.drawOn(c, self.TX + 8, y - ph)
                        y -= ph + row_gap
                else:
                    # Свободный текст
                    p = make_para(line, val_font, val_size, val_color,
                                  val_size * 1.4, TA_LEFT)
                    _, ph = p.wrap(self.TW, 9999)
                    p.drawOn(c, self.TX, y - ph)
                    y -= ph + row_gap

        return y - self.para_space

    def _render_bio_timeline(self, c, page: dict):
        """Рендерит страницу хронологии (bio_timeline).

        Поддерживает два формата elements[]:
        - Новый: elements=[{type:"timeline_item", period:..., title:..., text:...}]
        - Старый: elements=[{type:"timeline_block", content:"...markdown..."}]
        """
        self._fill_bg(c)
        y = self.TY

        # Заголовок «Хронология жизни»
        c.setFillColor(HexColor(self.c_accent))
        c.setFont(SANS_FONT, 5.5)
        c.drawString(self.TX, y, "ХРОНОЛОГИЯ ЖИЗНИ")
        y -= 12

        period_color = self.c_accent
        title_font   = BODY_BOLD_FONT
        title_size   = 8
        text_font    = BODY_FONT
        text_size    = 7.5
        text_color   = "#555555"
        dot_r        = 3.5
        line_x       = self.TX + 6
        text_x       = self.TX + 18
        text_w       = self.TW - 18

        elements = page.get("elements", [])

        # Нормализуем в список timeline_item
        items: list[dict] = []
        for elem in elements:
            if elem.get("type") == "timeline_item":
                items.append(elem)
            elif elem.get("type") == "timeline_block":
                # Парсим markdown content в items
                content = elem.get("content", "")
                cur: dict = {}
                for line in content.split("\n"):
                    line = line.strip()
                    if not line:
                        continue
                    # **Период** → новый item
                    if line.startswith("**") and line.endswith("**"):
                        if cur:
                            items.append(cur)
                        raw = line.strip("*").strip()
                        # Попытка разделить «Период (1920–1938)» → period + title
                        import re as _re
                        m = _re.match(r"(.+?)\s*[\(\[]?([\d]{4}[^\)\]]*[\d]{4})[\)\]]?", raw)
                        if m:
                            cur = {"period": m.group(2).strip(), "title": m.group(1).strip(), "text": ""}
                        else:
                            cur = {"period": "", "title": raw, "text": ""}
                    else:
                        if cur:
                            sep = "\n" if cur.get("text") else ""
                            cur["text"] = cur.get("text", "") + sep + line
                if cur:
                    items.append(cur)

        if not items:
            # Fallback: рендерим элементы через стандартный поток (с поддержкой markdown-стриппинга)
            for elem in elements:
                if elem.get("type") in ("paragraph", "text", ""):
                    y = self._render_paragraph(c, elem, y)
                elif elem.get("content") or elem.get("text"):
                    y = self._render_paragraph(c, {"text": elem.get("content", elem.get("text", ""))}, y)
            self._draw_footer(c, page_num=self._visible_page_num(page))
            return

        for idx, item in enumerate(items):
            if y < self.MB + 30:
                break
            period = item.get("period", "")
            title  = item.get("title", "")
            text   = item.get("text", "")

            # Измеряем высоту контента
            content_parts = []
            if period:
                pp = make_para(period, SANS_FONT, 6, period_color, 8, TA_LEFT)
                _, ph = pp.wrap(text_w, 9999)
                content_parts.append((pp, ph))
            if title:
                tp = make_para(title, title_font, title_size, self.heading_color,
                               title_size * 1.3, TA_LEFT)
                _, th = tp.wrap(text_w, 9999)
                content_parts.append((tp, th))
            if text:
                txp = make_para(text, text_font, text_size, text_color,
                                text_size * 1.4, TA_LEFT)
                _, txh = txp.wrap(text_w, 9999)
                content_parts.append((txp, txh))

            total_h = sum(h for _, h in content_parts) + 4
            dot_y   = y - dot_r - 2

            # Вертикальная линия до следующего элемента
            if idx < len(items) - 1:
                next_y = y - total_h - 6
                c.setStrokeColor(HexColor("#e0d8cc"))
                c.setLineWidth(1.5)
                c.line(line_x, dot_y - dot_r, line_x, next_y + dot_r)

            # Точка
            c.setFillColor(HexColor(self.c_bg))
            c.setStrokeColor(HexColor(self.c_accent))
            c.setLineWidth(1.5)
            c.circle(line_x, dot_y, dot_r, fill=1, stroke=1)

            # Контент
            cy = y
            for para, ph in content_parts:
                para.drawOn(c, text_x, cy - ph)
                cy -= ph + 2

            y -= total_h + 6

        self._draw_footer(c, page_num=self._visible_page_num(page))

    def _render_photo_section(self, c, page: dict):
        """Рендерит страницы фотораздела (photo_section / photo_section_start)."""
        self._fill_bg(c)
        y = self.TY
        elements = page.get("elements", [])

        # Заголовок раздела (photo_section_start)
        if page.get("type") == "photo_section_start":
            for elem in elements:
                if elem.get("type") == "section_header":
                    title = elem.get("title", elem.get("text", "Фотографии"))
                    c.setFillColor(HexColor(self.heading_color))
                    c.setFont(SANS_BOLD_FONT, 18)
                    c.drawString(self.TX, y, title)
                    y -= 28
                    c.setStrokeColor(HexColor(self.c_accent))
                    c.setLineWidth(1.5)
                    c.line(self.TX, y, self.TX + 28 * mm, y)
                    y -= 20
            # Если после заголовка есть свободное место и есть photo_pair — рендерим их здесь
            for elem in elements:
                if elem.get("type") in ("photo_pair", "photo_single", "photo"):
                    etype = elem.get("type", "")
                    if etype == "photo_pair":
                        layout = elem.get("layout", "pair_side")
                        photos = elem.get("photos", [])
                        if layout == "pair_side" and len(photos) >= 2:
                            y = self._render_pair_side(c, photos, y)
                        elif layout == "pair_stack" and len(photos) >= 2:
                            y = self._render_pair_stack(c, photos, y)
                    else:
                        y = self._render_photo_elem(c, elem, y)
            self._draw_footer(c, page_num=self._visible_page_num(page))
            return

        for elem in elements:
            etype = elem.get("type", "")
            if etype == "photo_pair":
                layout = elem.get("layout", "pair_side")
                photos = elem.get("photos", [])
                if layout == "pair_side" and len(photos) >= 2:
                    # pair_side запрещён для вертикальных фото: переключаем на pair_stack.
                    first_pid = photos[0].get("photo_id", "") if isinstance(photos[0], dict) else photos[0]
                    second_pid = photos[1].get("photo_id", "") if isinstance(photos[1], dict) else photos[1]
                    o1 = self._photo_orientation(first_pid)
                    o2 = self._photo_orientation(second_pid)
                    if o1 == "vertical" or o2 == "vertical":
                        print(f"[RENDERER] ℹ️  pair_side→pair_stack: вертикальные фото {first_pid}, {second_pid}")
                        y = self._render_pair_stack(c, photos, y)
                    else:
                        y = self._render_pair_side(c, photos, y)
                elif layout == "pair_stack" and len(photos) >= 2:
                    y = self._render_pair_stack(c, photos, y)
                elif photos:
                    # Одно фото — как full_width
                    y = self._render_photo_elem(
                        c, {"photo_id": photos[0].get("photo_id", ""),
                            "layout": "full_width",
                            "caption": photos[0].get("caption", "")}, y)
            elif etype == "photo_single":
                y = self._render_photo_elem(c, elem, y)
            elif etype == "photo":
                y = self._render_photo_elem(c, elem, y)

        self._draw_footer(c, page_num=self._visible_page_num(page))

    def _render_pair_side(self, c, photos: list, y: float) -> float:
        """Два фото рядом (pair_side). Высота определяется реальными пропорциями фото."""
        from PIL import Image as PILImage
        gap     = self.photo_margin
        pw      = (self.TW - gap) / 2
        avail_h = y - self.MB - 24

        # Вычисляем «естественные» высоты каждого фото при ширине pw
        natural: list[float] = []
        for photo_info in photos[:2]:
            pid  = photo_info.get("photo_id", "") if isinstance(photo_info, dict) else photo_info
            path = self.photos.get(pid)
            if path and path.exists():
                try:
                    with PILImage.open(path) as img:
                        iw, ih = img.size
                    natural.append(pw * ih / iw)
                except Exception:
                    natural.append(pw * 1.3)
            else:
                natural.append(pw * 1.3)

        # Высота блока — по самому высокому фото, но не больше 90% страницы
        ph = min(max(natural), avail_h * 0.90)

        actual_heights: list[float] = []
        for i, photo_info in enumerate(photos[:2]):
            pid  = photo_info.get("photo_id", "") if isinstance(photo_info, dict) else photo_info
            cap  = (photo_info.get("caption", "") if isinstance(photo_info, dict) else "") or \
                   self.photo_captions.get(pid, "")
            path = self.photos.get(pid)
            px   = self.TX + i * (pw + gap)
            actual_h = 0.0
            if path and path.exists():
                actual_h = self._draw_image(c, path, px, y, pw, ph, "nw")
            actual_heights.append(actual_h)
            if cap:
                c.setFont(SANS_FONT, self.caption_size)
                c.setFillColor(HexColor(self.caption_color))
                cap_y = y - (actual_h if actual_h > 0 else ph) - 6
                c.drawCentredString(px + pw / 2, cap_y, cap[:50])

        used_h = max(actual_heights) if any(h > 0 for h in actual_heights) else ph
        cap_h  = self.caption_size + 10
        return y - used_h - cap_h - self.photo_margin

    def _render_pair_stack(self, c, photos: list, y: float) -> float:
        """Два фото стопкой (pair_stack). Высота каждого — по реальным пропорциям."""
        from PIL import Image as PILImage
        pw      = self.TW * 0.72
        px      = self.TX + (self.TW - pw) / 2
        avail_h = y - self.MB - 24

        for photo_info in photos[:2]:
            pid  = photo_info.get("photo_id", "") if isinstance(photo_info, dict) else photo_info
            cap  = (photo_info.get("caption", "") if isinstance(photo_info, dict) else "") or \
                   self.photo_captions.get(pid, "")
            path = self.photos.get(pid)

            # Высота по реальным пропорциям, но не больше 44% страницы
            ph_each = avail_h * 0.44
            if path and path.exists():
                try:
                    with PILImage.open(path) as img:
                        iw, ih = img.size
                    ph_each = min(pw * ih / iw, avail_h * 0.44)
                except Exception:
                    pass

            if y - ph_each < self.MB + 20:
                break
            actual_h = 0.0
            if path and path.exists():
                actual_h = self._draw_image(c, path, px, y, pw, ph_each, "nw")
            if cap:
                c.setFont(SANS_FONT, self.caption_size)
                c.setFillColor(HexColor(self.caption_color))
                cap_y = y - (actual_h if actual_h > 0 else ph_each) - 6
                c.drawCentredString(px + pw / 2, cap_y, cap[:50])
            y -= (actual_h if actual_h > 0 else ph_each) + self.caption_size + 16

        return y

    def _render_unknown(self, c, page: dict):
        """Fallback для незнакомых типов страниц: рендерим как текстовую страницу.

        Если Layout Designer вернул новый тип (например text_with_bio_sidebar),
        мы не теряем текст — абзацы всё равно рендерятся.
        """
        ptype = page.get("type", "?")
        print(f"[RENDERER] ⚠️  Неизвестный тип страницы: {ptype!r} — рендерим как text_page")
        self._render_text_page(c, page)


# ── CLI ────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="PDF Renderer: pages[] → PDF")
    parser.add_argument("--layout", required=True,
                        help="Путь к layout_result.json")
    parser.add_argument("--book", default=None,
                        help="Путь к book_FINAL.json (book_index для lookup paragraph_id)")
    parser.add_argument("--photos-dir", default=None,
                        help="Директория с фото (manifest.json внутри)")
    parser.add_argument("--portrait", default=None,
                        help="Путь к портрету обложки (.webp/.png)")
    parser.add_argument("--output", default=None,
                        help="Выходной PDF (по умолчанию exports/rendered_<ts>.pdf)")
    parser.add_argument("--text-only", action="store_true",
                        help="Рендерить только текстовые слои (без фото/callout/ист.справок/обложки)")
    parser.add_argument("--with-bio-block", action="store_true",
                        help="В режиме --text-only включить bio_data блок главы ch_01")
    parser.add_argument("--no-photos", action="store_true",
                        help="Скрыть реальные фото, оставить текст/callout/ист.справки и плейсхолдеры chapter_start")
    parser.add_argument("--with-cover", action="store_true",
                        help="Включить страницу обложки")
    parser.add_argument("--strict-refs", action="store_true",
                        help="Ошибка если paragraph_ref не найден в book_FINAL (production mode)")
    parser.add_argument("--allow-missing-refs", action="store_true",
                        help="Разрешить пропуск ненайденных refs (отменяет --strict-refs для данного запуска)")
    args = parser.parse_args()

    layout_path = Path(args.layout)
    if not layout_path.exists():
        print(f"[ERROR] Файл не найден: {layout_path}")
        sys.exit(1)

    layout = json.loads(layout_path.read_text(encoding="utf-8"))
    if not layout.get("pages"):
        print("[ERROR] В layout нет поля pages[]")
        sys.exit(1)

    book_index: BookIndex | None = None
    if args.book:
        book_path = Path(args.book)
        if book_path.exists():
            book_data = json.loads(book_path.read_text(encoding="utf-8"))
            # Unwrap checkpoint wrapper: { "book_final": {...} } → {...}
            # test_stage4 передаёт proofreader_checkpoint напрямую; в нём book под ключом "book_final"
            if "book_final" in book_data and isinstance(book_data["book_final"], dict):
                book_data = book_data["book_final"]
                print("[RENDERER] book_final unwrapped из checkpoint")
            # Нормализуем paragraph IDs через ту же функцию, что получил Layout Designer.
            # Это гарантирует совпадение ID: p1, p2, ... из content.split("\n\n")
            try:
                sys.path.insert(0, str(ROOT))
                from pipeline_utils import prepare_book_for_layout as _prep
                book_data = _prep(book_data)
            except Exception as _e:
                print(f"[RENDERER] ⚠️  prepare_book_for_layout недоступен: {_e} — используем raw paragraphs")
            book_index = BookIndex(book_data)
            total_paras = sum(len(list(book_index.chapter_paragraphs(ch_id)))
                              for ch_id in (book_index._index or {}))
            print(f"[RENDERER] BookIndex: {len(book_index._index)} глав, ~{total_paras} абзацев")
        else:
            print(f"[RENDERER] ⚠️  book не найден: {book_path} — будет использован legacy text")

    photos_dir = Path(args.photos_dir) if args.photos_dir else None
    portrait   = Path(args.portrait)   if args.portrait   else None
    ts         = datetime.now().strftime("%Y%m%d_%H%M%S")
    output     = Path(args.output) if args.output else ROOT / "exports" / f"karakulina_rendered_{ts}.pdf"

    print(f"[RENDERER] Layout:   {layout_path.name} ({len(layout['pages'])} стр.)")
    print(f"[RENDERER] Book:     {args.book or 'нет (legacy mode)'}")
    print(f"[RENDERER] Фото:     {photos_dir or 'нет'}")
    print(f"[RENDERER] Портрет:  {portrait.name if portrait else 'нет'}")
    print(f"[RENDERER] Флаги:    text_only={args.text_only} with_bio_block={args.with_bio_block} "
          f"no_photos={args.no_photos} with_cover={args.with_cover} strict_refs={getattr(args,'strict_refs',False)}")
    print(f"[RENDERER] Выход:    {output}")

    photos   = PhotoManager(photos_dir)
    options = RenderOptions(
        text_only=args.text_only,
        with_bio_block=args.with_bio_block,
        no_photos=args.no_photos,
        with_cover=args.with_cover,
        strict_refs=getattr(args, "strict_refs", False),
        allow_missing_refs=getattr(args, "allow_missing_refs", False),
    )
    renderer = PdfRenderer(layout, photos, portrait, output, book_index, options)
    renderer.render()


if __name__ == "__main__":
    main()
