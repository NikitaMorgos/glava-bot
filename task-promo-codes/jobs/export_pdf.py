# -*- coding: utf-8 -*-
"""
Генерация PDF по задаче Промо-коды.
Объединяет plan.md, docs/PROMO_LENA.md, docs/PROMO_USER.md в один PDF.
Запуск из корня проекта:
  python task-promo-codes/jobs/export_pdf.py
Результат: task-promo-codes/docs/PROMO_CODES.pdf
"""
import re
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Preformatted, PageBreak, HRFlowable,
)

ROOT = Path(__file__).resolve().parent.parent.parent
TASK = ROOT / "task-promo-codes"
OUT_PATH = TASK / "docs" / "PROMO_CODES.pdf"

SECTIONS = [
    ("Технический план", TASK / "plan.md"),
    ("Инструкция для маркетолога (Лены)", TASK / "docs" / "PROMO_LENA.md"),
    ("Инструкция для пользователя бота", TASK / "docs" / "PROMO_USER.md"),
]


def find_cyrillic_font():
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        candidates = [
            ("C:\\Windows\\Fonts\\arial.ttf"),
            ("C:\\Windows\\Fonts\\calibri.ttf"),
            ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
        ]
        for path in candidates:
            if Path(path).exists():
                pdfmetrics.registerFont(TTFont("CyrFont", path))
                return "CyrFont"
    except Exception:
        pass
    return "Helvetica"


def build_story(sections, font, styles):
    story = []

    # Обложка
    story.append(Spacer(1, 2 * cm))
    story.append(Paragraph("GLAVA", ParagraphStyle(
        "Cover1", fontName=font, fontSize=32, spaceAfter=8, textColor=colors.HexColor("#111111"),
    )))
    story.append(Paragraph("Система промо-кодов", ParagraphStyle(
        "Cover2", fontName=font, fontSize=20, spaceAfter=4, textColor=colors.HexColor("#444444"),
    )))
    story.append(Paragraph("Документация по задаче · 2026-03-24", ParagraphStyle(
        "Cover3", fontName=font, fontSize=11, textColor=colors.HexColor("#888888"),
    )))
    story.append(Spacer(1, 1 * cm))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#dddddd")))
    story.append(Spacer(1, 0.5 * cm))

    # Оглавление
    story.append(Paragraph("Содержание", ParagraphStyle(
        "TOCHead", fontName=font, fontSize=13, spaceBefore=8, spaceAfter=6, textColor=colors.HexColor("#333333"),
    )))
    for i, (title, _) in enumerate(sections, 1):
        story.append(Paragraph(f"{i}. {title}", ParagraphStyle(
            "TOCItem", fontName=font, fontSize=10, spaceAfter=3, leftIndent=12, textColor=colors.HexColor("#555555"),
        )))
    story.append(PageBreak())

    for section_title, md_path in sections:
        story.append(Paragraph(section_title, ParagraphStyle(
            "SecTitle", fontName=font, fontSize=16, spaceBefore=4, spaceAfter=12,
            textColor=colors.HexColor("#111111"),
        )))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cccccc")))
        story.append(Spacer(1, 0.3 * cm))

        text = md_path.read_text(encoding="utf-8")
        _parse_md(text, story, font, styles)
        story.append(PageBreak())

    return story


def _parse_md(text, story, font, styles):
    in_code = False
    code_lines = []
    in_table = False
    table_rows = []
    doc_width = A4[0] - 3 * cm  # приближение

    def flush_code():
        if code_lines:
            story.append(Preformatted(
                "\n".join(code_lines),
                ParagraphStyle("Code", fontName="Courier", fontSize=8, leftIndent=12,
                               rightIndent=12, spaceBefore=4, spaceAfter=4,
                               backColor=colors.HexColor("#f5f5f5")),
            ))
            story.append(Spacer(1, 0.2 * cm))
            code_lines.clear()

    def flush_table():
        if table_rows:
            ncol = len(table_rows[0])
            col_w = [doc_width / ncol] * ncol
            t = Table(table_rows, colWidths=col_w, repeatRows=1)
            t.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (-1, -1), font),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("FONTNAME", (0, 0), (-1, 0), font),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(t)
            story.append(Spacer(1, 0.3 * cm))
            table_rows.clear()

    for line in text.splitlines():
        stripped = line.strip()

        # Код-блоки
        if stripped.startswith("```"):
            if in_code:
                flush_code()
                in_code = False
            else:
                flush_table()
                in_code = True
            continue
        if in_code:
            code_lines.append(line)
            continue

        # Таблицы
        if stripped.startswith("|") and "|" in stripped[1:]:
            flush_code()
            cells = [c.strip() for c in stripped.split("|")[1:-1]]
            if not cells:
                continue
            if all(re.match(r"^[-:\s]+$", c) for c in cells):
                continue
            in_table = True
            table_rows.append(cells)
            continue
        else:
            if in_table:
                flush_table()
                in_table = False

        if not stripped:
            story.append(Spacer(1, 0.15 * cm))
            continue
        if stripped == "---":
            story.append(HRFlowable(width="100%", thickness=0.4, color=colors.HexColor("#dddddd"),
                                    spaceBefore=6, spaceAfter=6))
            continue

        def safe(s):
            s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
            s = re.sub(r"\*(.+?)\*", r"<i>\1</i>", s)
            s = re.sub(r"`(.+?)`", r"<font name='Courier'>\1</font>", s)
            return s

        if line.startswith("# "):
            flush_table(); flush_code()
            story.append(Paragraph(safe(stripped[2:]), ParagraphStyle(
                "H1", fontName=font, fontSize=15, spaceBefore=10, spaceAfter=6,
                textColor=colors.HexColor("#111111"),
            )))
        elif line.startswith("## "):
            flush_table(); flush_code()
            story.append(Paragraph(safe(stripped[3:]), ParagraphStyle(
                "H2", fontName=font, fontSize=12, spaceBefore=10, spaceAfter=5,
                textColor=colors.HexColor("#222222"),
            )))
        elif line.startswith("### "):
            flush_table(); flush_code()
            story.append(Paragraph(safe(stripped[4:]), ParagraphStyle(
                "H3", fontName=font, fontSize=10, spaceBefore=8, spaceAfter=4,
                textColor=colors.HexColor("#333333"),
            )))
        elif stripped.startswith("- [x] ") or stripped.startswith("- [ ] "):
            mark = "✓" if stripped.startswith("- [x]") else "○"
            text_part = safe(stripped[6:])
            story.append(Paragraph(
                f"{mark} {text_part}",
                ParagraphStyle("Checklist", fontName=font, fontSize=9,
                               spaceAfter=2, leftIndent=16),
            ))
        elif stripped.startswith("- "):
            story.append(Paragraph(
                "• " + safe(stripped[2:]),
                ParagraphStyle("Bullet", fontName=font, fontSize=9,
                               spaceAfter=3, leftIndent=16),
            ))
        else:
            story.append(Paragraph(safe(stripped), ParagraphStyle(
                "Body", fontName=font, fontSize=9, spaceAfter=4,
            )))

    flush_code()
    flush_table()


def main():
    font = find_cyrillic_font()
    styles = getSampleStyleSheet()

    doc = SimpleDocTemplate(
        str(OUT_PATH),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title="GLAVA — Промо-коды",
        author="GLAVA Team",
    )

    story = build_story(SECTIONS, font, styles)
    doc.build(story)
    print(f"PDF готов: {OUT_PATH}")


if __name__ == "__main__":
    main()
