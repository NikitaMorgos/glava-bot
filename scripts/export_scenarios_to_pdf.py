# -*- coding: utf-8 -*-
"""
Экспорт docs/USER_SCENARIOS.md в PDF.
Запуск из корня проекта:
  python scripts/export_scenarios_to_pdf.py
  или (если есть venv): venv\\Scripts\\python scripts\\export_scenarios_to_pdf.py
Требуется: reportlab (есть в requirements.txt).
Результат: docs/USER_SCENARIOS.pdf
"""

import re
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Preformatted, PageBreak

# Корень проекта = родитель каталога scripts
ROOT = Path(__file__).resolve().parent.parent
MD_PATH = ROOT / "docs" / "USER_SCENARIOS.md"
OUT_PATH = ROOT / "docs" / "USER_SCENARIOS.pdf"


def find_font_for_cyrillic():
    """Пробуем найти шрифт с кириллицей."""
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        # Windows
        for name, path in [
            ("Arial", "C:\\Windows\\Fonts\\arial.ttf"),
            ("Arial", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            ("Arial", "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
        ]:
            if Path(path).exists():
                pdfmetrics.registerFont(TTFont("CyrillicFont", path))
                return "CyrillicFont"
    except Exception:
        pass
    return "Helvetica"  # fallback (кириллица не отобразится)


def main():
    font_name = find_font_for_cyrillic()
    doc = SimpleDocTemplate(
        str(OUT_PATH),
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="CyrillicTitle",
        fontName=font_name,
        fontSize=18,
        spaceAfter=12,
    ))
    styles.add(ParagraphStyle(
        name="CyrillicHeading",
        fontName=font_name,
        fontSize=14,
        spaceBefore=14,
        spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        name="CyrillicBody",
        fontName=font_name,
        fontSize=10,
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="CyrillicCode",
        fontName="Courier",
        fontSize=8,
        spaceBefore=6,
        spaceAfter=6,
        leftIndent=12,
        rightIndent=12,
    ))

    if not MD_PATH.exists():
        print(f"Файл не найден: {MD_PATH}", file=sys.stderr)
        sys.exit(1)

    text = MD_PATH.read_text(encoding="utf-8")
    story = []
    in_code = False
    code_lines = []
    in_table = False
    table_rows = []

    def flush_code():
        nonlocal code_lines
        if code_lines:
            block = Preformatted("\n".join(code_lines), styles["CyrillicCode"])
            story.append(block)
            story.append(Spacer(1, 0.3 * cm))
            code_lines = []

    def flush_table():
        nonlocal table_rows
        if table_rows:
            ncol = len(table_rows[0])
            total_w = doc.pagesize[0] - doc.leftMargin - doc.rightMargin
            col_widths = [total_w / ncol] * ncol
            t = Table(table_rows, colWidths=col_widths, repeatRows=1)
            t.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("FONTNAME", (0, 0), (-1, 0), font_name),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]))
            story.append(t)
            story.append(Spacer(1, 0.4 * cm))
            table_rows = []

    for line in text.splitlines():
        if line.strip() == "```":
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

        if line.strip().startswith("|") and "|" in line[1:]:
            flush_code()
            cells = [c.strip() for c in line.split("|")[1:-1]]
            if not cells:
                continue
            # Строка вида |---|---| — разделитель, пропускаем
            if all(re.match(r"^[-:\s]+$", c) for c in cells):
                continue
            if not in_table:
                in_table = True
            table_rows.append(cells)
            continue
        else:
            if in_table:
                flush_table()
                in_table = False

        stripped = line.strip()
        if not stripped:
            story.append(Spacer(1, 0.2 * cm))
            continue
        if stripped == "---":
            story.append(Spacer(1, 0.5 * cm))
            continue
        if line.startswith("# "):
            flush_code()
            flush_table()
            p = Paragraph(stripped[2:].replace("&", "&amp;").replace("<", "&lt;"), styles["CyrillicTitle"])
            story.append(p)
            continue
        if line.startswith("## "):
            flush_code()
            flush_table()
            p = Paragraph(stripped[3:].replace("&", "&amp;").replace("<", "&lt;"), styles["CyrillicHeading"])
            story.append(p)
            continue
        if line.startswith("### "):
            flush_code()
            flush_table()
            p = Paragraph(stripped[4:].replace("&", "&amp;").replace("<", "&lt;"), styles["CyrillicHeading"])
            story.append(p)
            continue
        # Обычный абзац: экранировать для XML
        safe = stripped.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        # **текст** -> жирный
        safe = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", safe)
        p = Paragraph(safe, styles["CyrillicBody"])
        story.append(p)

    flush_code()
    flush_table()

    doc.build(story)
    print(f"Готово: {OUT_PATH}")


if __name__ == "__main__":
    main()
