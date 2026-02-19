#!/usr/bin/env python3
"""
Добавляет минималистичную шапку на one-pager PDF (как на лендинге glava.family).

Вместо синего логотипа: строка «Glava — glava.family» вверху слева,
тонкий серый текст, без плашек. Между шапкой и контентом — отступ 12–16 px.

Использование: python add_logo_to_pdf.py <input.pdf> [output.pdf]
"""
import sys
from pathlib import Path

# Стили как на лендинге glava.family
HEADER_TEXT = "Glava - glava.family"
HEADER_COLOR = (0.42, 0.36, 0.30)  # #6b5d4d muted
HEADER_FONTSIZE = 10
HEADER_LEFT = 12   # pt от левого края
HEADER_TOP = 14    # pt от верхней кромки (вплотную)
HEADER_HEIGHT = 20  # высота блока шапки (отступ до основного контента ~14pt)


def remove_logo_image(page) -> None:
    """Удаляет синий логотип в правом верхнем углу, если он был добавлен ранее."""
    try:
        import pymupdf
    except ImportError:
        return
    rect = page.rect
    # Область, где мы добавляли логотип (правый верхний угол)
    logo_zone_right = rect.width - 10
    logo_zone_top = 50
    for item in page.get_images():
        xref = item[0]
        try:
            bbox = page.get_image_bbox(xref)
            if bbox and bbox.x1 >= rect.width - 120 and bbox.y0 < logo_zone_top:
                page.delete_image(xref)
                break
        except Exception:
            continue


def add_header_to_pdf(input_path: str, output_path: str) -> None:
    """Добавляет минималистичную шапку в верх каждой страницы PDF."""
    try:
        import pymupdf
    except ImportError:
        raise SystemExit("Нужен PyMuPDF: pip install pymupdf")

    doc = pymupdf.open(input_path)
    for page_num in range(len(doc)):
        page = doc[page_num]
        rect = page.rect

        remove_logo_image(page)

        # Текстовый блок шапки: левый верхний угол, серый текст
        text_rect = pymupdf.Rect(
            HEADER_LEFT,
            HEADER_TOP,
            rect.width - HEADER_LEFT,
            HEADER_TOP + HEADER_HEIGHT,
        )
        page.insert_textbox(
            text_rect,
            HEADER_TEXT,
            fontsize=HEADER_FONTSIZE,
            fontname="helv",
            color=HEADER_COLOR,
            align=pymupdf.TEXT_ALIGN_LEFT,
        )

    doc.save(output_path, garbage=4, deflate=True)
    doc.close()
    print(f"Сохранено: {output_path}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    input_pdf = sys.argv[1]
    output_pdf = sys.argv[2] if len(sys.argv) > 2 else input_pdf.replace(".pdf", "_header.pdf")

    if not Path(input_pdf).exists():
        print(f"Файл не найден: {input_pdf}")
        sys.exit(1)

    add_header_to_pdf(input_pdf, output_pdf)


if __name__ == "__main__":
    main()
