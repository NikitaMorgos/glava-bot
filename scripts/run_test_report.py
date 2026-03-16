# -*- coding: utf-8 -*-
"""
Прогон автотестов бота и формирование отчёта (MD + PDF).
Запуск из корня проекта: python scripts/run_test_report.py

Требуется: reportlab (есть в requirements.txt).
Опционально: pytest, pytest-asyncio — для запуска автотестов.
Результат: docs/test-runs/test-run_YYYY-MM-DD_HHmm.pdf (и .md)
"""

import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEST_RUNS_DIR = ROOT / "docs" / "test-runs"
TESTS_MODULE = "tests.test_bot_flows"

# Соответствие имён автотестов тест-кейсам TC-01..TC-27 (один тест — один TC)
TEST_TO_TC = {
    "test_cmd_start_sends_intro": "TC-01",
    "test_callback_intro_example": "TC-02",
    "test_callback_intro_main": "TC-03",
    "test_callback_intro_start_creates_draft": "TC-04",
    "test_prepay_character_name_then_relation": "TC-05",
    "test_prepay_relation_then_show_buttons": "TC-06",
    "test_prepay_add_second_character": "TC-07",
    "test_prepay_delete_one_character": "TC-08",
    "test_prepay_delete_last_character_shows_add_only": "TC-09",
    "test_prepay_continue_without_characters_forbidden": "TC-10",
    "test_prepay_continue_shows_email_request": "TC-11",
    "test_prepay_email_invalid_reply": "TC-12",
    "test_prepay_valid_email_shows_summary": "TC-13",
    "test_callback_order_pay_calls_create_payment": "TC-14",
    "test_callback_intro_start_payment_pending": "TC-15",
    "test_callback_payment_check_not_paid": "TC-16",
    "test_callback_payment_check_paid": "TC-17",
    "test_voice_without_paid_blocked": "TC-18",
    "test_photo_without_paid_blocked": "TC-19",
    "test_audio_without_paid_blocked": "TC-20",
    "test_text_unknown_no_prepay_reply": "TC-21",
    "test_callback_intro_start_draft_empty_characters": "TC-22",
    "test_callback_intro_start_draft_with_characters_no_email": "TC-23",
    "test_callback_intro_start_draft_with_email_shows_summary": "TC-24",
    "test_list_empty": "TC-25",
    "test_cabinet_sets_awaiting_password": "TC-26",
    "test_cabinet_short_password_error": "TC-27",
}

# Все кейсы для отчёта: ID -> краткое название
TC_NAMES = {
    "TC-01": "/start → главное меню",
    "TC-02": "Пример → Назад",
    "TC-03": "Стоимость → Назад",
    "TC-04": "Начать → запрос имени (без кнопок)",
    "TC-05": "Ввод имени → запрос родства",
    "TC-06": "Ввод родства → кнопки Добавить/Продолжить",
    "TC-07": "Добавить ещё → 2 персонажа",
    "TC-08": "Удалить одного персонажа",
    "TC-09": "Удалить последнего → запрос имени без кнопок",
    "TC-10": "Продолжить без персонажей запрещено",
    "TC-11": "Продолжить → запрос email",
    "TC-12": "Неверный email → ошибка и повтор",
    "TC-13": "Валидный email → экран Итого",
    "TC-14": "Перейти к оплате → payment session",
    "TC-15": "/start при payment_pending → ожидание оплаты",
    "TC-16": "Проверить оплату при not paid",
    "TC-17": "Проверить оплату при paid",
    "TC-18": "Голосовое до оплаты блокируется",
    "TC-19": "Фото до оплаты блокируется",
    "TC-20": "Аудио/документ до оплаты блокируется",
    "TC-21": "Произвольный текст → «Используйте кнопки»",
    "TC-22": "/start при draft без персонажей → запрос имени",
    "TC-23": "/start при draft с персонажами → email",
    "TC-24": "/start при draft с email → Итого",
    "TC-25": "/list до оплаты (пусто)",
    "TC-26": "/cabinet пароль OK",
    "TC-27": "/cabinet пароль короткий",
}


def run_pytest():
    """Запуск pytest, возвращает dict: test_name -> 'passed' | 'failed'."""
    result = {}
    try:
        import pytest
    except ImportError:
        return result

    class CollectResults:
        def __init__(self):
            self.results = {}

        def pytest_runtest_logreport(self, report):
            if report.when != "call":
                return
            name = report.nodeid.split("::")[-1] if "::" in report.nodeid else report.nodeid
            if name.startswith("test_"):
                self.results[name] = "passed" if report.passed else "failed"

    collector = CollectResults()
    cwd = os.getcwd()
    try:
        os.chdir(ROOT)
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        pytest.main(
            ["tests/test_bot_flows.py", "-v", "--tb=no"],
            plugins=[collector],
        )
        return collector.results
    finally:
        os.chdir(cwd)


def build_report(pytest_results):
    """Формирует данные отчёта: список (tc_id, name, status, note). status: pass, fail, n/a."""
    tc_order = [f"TC-{i:02d}" for i in range(1, 28)]
    # Обратное отображение: TC -> test name
    tc_to_test = {v: k for k, v in TEST_TO_TC.items()}
    rows = []
    for tc_id in tc_order:
        name = TC_NAMES.get(tc_id, "")
        test_name = tc_to_test.get(tc_id)
        if test_name and test_name in pytest_results:
            res = pytest_results[test_name]
            status = "pass" if res == "passed" else "fail"
            note = "Автотест" if res == "passed" else "Падение автотеста"
        else:
            status = "n/a"
            note = "Ручной прогон" if not test_name else "Не запускался"
        rows.append((tc_id, name, status, note))
    return rows


def write_md_report(rows, run_ts, pytest_ok, md_path):
    """Пишет отчёт в Markdown."""
    lines = [
        "# Отчёт о прогоне тест-кейсов",
        "",
        f"**Дата и время:** {run_ts}",
        "**Ветка / коммит:** —",
        "**Окружение:** автотесты (моки), часть кейсов — ручной прогон",
        "**Исполнитель:** скрипт run_test_report.py",
        "",
        "**Автотесты:** " + ("запущены (pytest)" if pytest_ok else "не запущены (pytest не установлен или ошибка)"),
        "",
        "---",
        "",
        "## Результаты по кейсам",
        "",
        "| ID | Название | Результат | Примечание |",
        "|----|----------|-----------|------------|",
    ]
    pass_count = fail_count = 0
    for tc_id, name, status, note in rows:
        if status == "pass":
            res = "✅ Pass"
            pass_count += 1
        elif status == "fail":
            res = "❌ Fail"
            fail_count += 1
        else:
            res = "—"
        lines.append(f"| {tc_id} | {name} | {res} | {note} |")
    lines.extend([
        "",
        "---",
        "",
        "## Итог",
        "",
        f"- **Всего:** {pass_count + fail_count} автотестов из 27 кейсов (остальные — ручной прогон)",
        f"- **Pass (авто):** {pass_count}",
        f"- **Fail (авто):** {fail_count}",
        "- **Критичные падения:** см. таблицу выше",
        "",
        "---",
        "",
        "**Релиз разрешён:** по результатам ручного прогона и автотестов (см. docs/TESTING.md).",
    ])
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("\n".join(lines), encoding="utf-8")


def find_font_for_cyrillic():
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        for name, path in [
            ("Arial", "C:\\Windows\\Fonts\\arial.ttf"),
            ("Arial", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        ]:
            if Path(path).exists():
                pdfmetrics.registerFont(TTFont("CyrillicFont", path))
                return "CyrillicFont"
    except Exception:
        pass
    return "Helvetica"


def build_pdf(md_path, pdf_path, rows, run_ts, pytest_ok):
    """Генерирует PDF из данных отчёта."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    font_name = find_font_for_cyrillic()
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="CyrillicTitle", fontName=font_name, fontSize=16, spaceAfter=10))
    styles.add(ParagraphStyle(name="CyrillicBody", fontName=font_name, fontSize=9, spaceAfter=4))

    story = []
    story.append(Paragraph("Отчёт о прогоне тест-кейсов бота GLAVA", styles["CyrillicTitle"]))
    story.append(Paragraph(f"Дата и время: {run_ts}", styles["CyrillicBody"]))
    story.append(Paragraph("Окружение: автотесты (моки) + ручной прогон", styles["CyrillicBody"]))
    story.append(Paragraph("Автотесты: " + ("запущены" if pytest_ok else "не запущены"), styles["CyrillicBody"]))
    story.append(Spacer(1, 0.5 * cm))

    table_data = [["ID", "Название", "Результат", "Примечание"]]
    for tc_id, name, status, note in rows:
        res = "Pass" if status == "pass" else ("Fail" if status == "fail" else "—")
        table_data.append([tc_id, name[:50] + ("…" if len(name) > 50 else ""), res, note[:30] + ("…" if len(note) > 30 else "")])
    total_w = doc.pagesize[0] - doc.leftMargin - doc.rightMargin
    col_widths = [total_w * 0.08, total_w * 0.42, total_w * 0.15, total_w * 0.35]
    t = Table(table_data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(t)
    pass_count = sum(1 for r in rows if r[2] == "pass")
    fail_count = sum(1 for r in rows if r[2] == "fail")
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(f"Итог: Pass (авто) {pass_count}, Fail (авто) {fail_count}, остальные — ручной прогон.", styles["CyrillicBody"]))
    doc.build(story)


def main():
    run_ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    md_path = TEST_RUNS_DIR / f"test-run_{stamp}.md"
    pdf_path = TEST_RUNS_DIR / f"test-run_{stamp}.pdf"

    pytest_results = run_pytest()
    pytest_ok = len(pytest_results) > 0
    rows = build_report(pytest_results)
    write_md_report(rows, run_ts, pytest_ok, md_path)

    try:
        build_pdf(md_path, pdf_path, rows, run_ts, pytest_ok)
        print(f"Отчёт (MD): {md_path}")
        print(f"Отчёт (PDF): {pdf_path}")
    except Exception as e:
        print(f"PDF не создан: {e}", file=sys.stderr)
        print(f"Markdown-отчёт: {md_path}")


if __name__ == "__main__":
    main()
