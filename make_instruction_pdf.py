"""
Создаёт PDF-инструкцию для Даши из markdown.
Запуск: python make_instruction_pdf.py
"""
import os
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Preformatted

# Шрифт с поддержкой кириллицы (Windows)
FONT_PATHS = [
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]
FONT_NAME = "InstructionFont"


def register_font():
    for path in FONT_PATHS:
        if os.path.exists(path):
            pdfmetrics.registerFont(TTFont(FONT_NAME, path))
            return True
    return False


def main():
    output_path = Path(__file__).parent / "ИНСТРУКЦИЯ_ДАША.pdf"

    if not register_font():
        print("Не найден шрифт с кириллицей. Установи DejaVu или используй Windows.")
        return

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontName=FONT_NAME,
        fontSize=16,
        spaceAfter=12,
    )
    heading_style = ParagraphStyle(
        "CustomHeading",
        parent=styles["Heading2"],
        fontName=FONT_NAME,
        fontSize=14,
        spaceAfter=8,
    )
    body_style = ParagraphStyle(
        "CustomBody",
        parent=styles["Normal"],
        fontName=FONT_NAME,
        fontSize=11,
        spaceAfter=6,
    )
    code_style = ParagraphStyle(
        "CustomCode",
        parent=styles["Code"],
        fontName="Courier",
        fontSize=10,
        backColor="#f5f5f5",
        borderPadding=8,
        spaceAfter=8,
    )

    def para(text, style=body_style):
        return Paragraph(text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"), style)

    story = [
        para("Инструкция для Даши — экспорт данных клиента", title_style),
        Spacer(1, 12),
        para("Что это", heading_style),
        para(
            "Скрипт собирает все данные одного клиента (голосовые + фото с подписями) "
            "в одну папку. Готово для верстки книги."
        ),
        Spacer(1, 12),
        para("Шаг 1. Открыть проект", heading_style),
        para("Перейди в папку проекта GLAVA и открой терминал (PowerShell)."),
        Spacer(1, 12),
        para("Шаг 2. Посмотреть список клиентов", heading_style),
        Preformatted(
            ".\\venv\\Scripts\\python.exe export_client.py",
            code_style,
        ),
        para("Появится список с telegram_id, количеством голосовых и фото. Запомни telegram_id нужного клиента."),
        Spacer(1, 12),
        para("Шаг 3. Экспортировать клиента", heading_style),
        Preformatted(
            ".\\venv\\Scripts\\python.exe export_client.py 123456789",
            code_style,
        ),
        para("(подставь свой telegram_id вместо 123456789)"),
        Spacer(1, 12),
        para("Шаг 4. Где искать результат", heading_style),
        para("Папка создаётся в: GLAVA/exports/client_123456789_username/"),
        para("Внутри:"),
        para("• voice/ — голосовые (001.ogg, 002.ogg...)"),
        para("• photos/ — фото (001.jpg, 002.jpg...)"),
        para("• captions.txt — подписи к фото"),
        para("• manifest.txt — полное описание содержимого"),
        Spacer(1, 12),
        para("Итого", heading_style),
        para("1. .\\venv\\Scripts\\python.exe export_client.py — список клиентов"),
        para("2. .\\venv\\Scripts\\python.exe export_client.py TELEGRAM_ID — экспорт"),
        para("3. Папка в exports/ — всё для верстки"),
    ]

    doc.build(story)
    print(f"Готово: {output_path}")


if __name__ == "__main__":
    main()
