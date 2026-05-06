#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit-тесты для scripts/validate_layout_fidelity.py — текущее поведение.

Safety net перед рефакторингом (задача волны 1.1):
параметризация validate_fidelity по типу ref (paragraph / callout / historical_note).
Эти тесты ловят поведение для paragraph_ref ДО рефакторинга.
После рефакторинга все тесты ниже ОБЯЗАНЫ пройти без изменений —
это и есть критерий «поведение сохранено».

Покрытие:
  1. Happy path: layout соответствует book → PASS
  2. Completeness: layout пропустил абзац → FAIL [COMPLETENESS]
  3. Completeness: layout ссылается на несуществующий ref → FAIL [COMPLETENESS]
  4. Order: layout правильные ref-ы, неправильный порядок → FAIL [ORDER]
  5. Uniqueness: layout содержит дубль одного ref → FAIL [UNIQUENESS]
  6. Multi-chapter: независимые главы, всё корректно → PASS
  7. Legacy: layout использует paragraph_id вместо paragraph_ref → работает
  8. Page-level chapter_id fallback: element без chapter_id → берётся со страницы
  9. allow_mismatch=True: возвращает (True, errors) даже при ошибках
 10. Book с content без paragraphs[]: _collect_book_refs парсит по \\n\\n

После расширения (волна 1.1, шаг 3) — добавлены проверки для callout и
historical_note. Они валидируются по тем же трём правилам (completeness /
order / uniqueness), но ref берётся из book.callouts / book.historical_notes
(top-level), сгруппированных по chapter_id каждого item.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from validate_layout_fidelity import validate_fidelity


# ──────────────────────────────────────────────────────────────────
# Вспомогательные фабрики
# ──────────────────────────────────────────────────────────────────

def _ch(ch_id: str, paragraph_ids: list[str]) -> dict:
    """Глава с явным списком paragraphs[]."""
    return {
        "id": ch_id,
        "title": ch_id,
        "paragraphs": [{"id": pid, "text": f"Текст {ch_id}/{pid}"} for pid in paragraph_ids],
    }


def _book(chapters: list[dict]) -> dict:
    return {"chapters": chapters}


def _para_elem(chapter_id: str, ref: str, *, use_legacy_field: bool = False) -> dict:
    """Layout-элемент типа paragraph. По умолчанию использует paragraph_ref (v3.20+)."""
    elem = {"type": "paragraph", "chapter_id": chapter_id}
    if use_legacy_field:
        elem["paragraph_id"] = ref
    else:
        elem["paragraph_ref"] = ref
    return elem


def _page(page_num: int, chapter_id: str, refs: list[str], *, use_legacy: bool = False,
          omit_elem_chapter: bool = False) -> dict:
    """Страница с указанным chapter_id и списком paragraph-элементов."""
    elements = []
    for ref in refs:
        elem = _para_elem(chapter_id, ref, use_legacy_field=use_legacy)
        if omit_elem_chapter:
            elem.pop("chapter_id", None)
        elements.append(elem)
    return {"page_number": page_num, "chapter_id": chapter_id, "elements": elements}


def _layout(pages: list[dict]) -> dict:
    return {"pages": pages}


# ──────────────────────────────────────────────────────────────────
# Тест 1: Happy path — layout полностью соответствует book
# ──────────────────────────────────────────────────────────────────

def test_happy_path_paragraphs_match():
    book = _book([_ch("ch_01", ["p1", "p2", "p3"])])
    layout = _layout([_page(1, "ch_01", ["p1", "p2", "p3"])])

    passed, errors = validate_fidelity(layout, book)

    assert passed is True
    assert errors == []


# ──────────────────────────────────────────────────────────────────
# Тест 2: Completeness — пропущенный абзац
# ──────────────────────────────────────────────────────────────────

def test_completeness_missing_paragraph():
    book = _book([_ch("ch_01", ["p1", "p2", "p3"])])
    layout = _layout([_page(1, "ch_01", ["p1", "p3"])])  # p2 пропущен

    passed, errors = validate_fidelity(layout, book)

    assert passed is False
    completeness_errors = [e for e in errors if "[COMPLETENESS]" in e]
    assert any("ch_01/p2" in e and "отсутствует" in e for e in completeness_errors), \
        f"Ожидалась ошибка про пропущенный ch_01/p2, получено: {errors}"


# ──────────────────────────────────────────────────────────────────
# Тест 3: Completeness — лишний ref в layout (нет в book)
# ──────────────────────────────────────────────────────────────────

def test_completeness_extra_ref_not_in_book():
    book = _book([_ch("ch_01", ["p1", "p2"])])
    layout = _layout([_page(1, "ch_01", ["p1", "p2", "p99"])])  # p99 не существует

    passed, errors = validate_fidelity(layout, book)

    assert passed is False
    extra_errors = [e for e in errors if "[COMPLETENESS]" in e and "p99" in e]
    assert extra_errors, f"Ожидалась ошибка про лишний p99, получено: {errors}"
    assert any("лишний" in e for e in extra_errors)


# ──────────────────────────────────────────────────────────────────
# Тест 4: Order — все refs на месте, но порядок неверный
# ──────────────────────────────────────────────────────────────────

def test_order_violation_within_chapter():
    book = _book([_ch("ch_01", ["p1", "p2", "p3"])])
    layout = _layout([_page(1, "ch_01", ["p1", "p3", "p2"])])  # p3 раньше p2

    passed, errors = validate_fidelity(layout, book)

    assert passed is False
    order_errors = [e for e in errors if "[ORDER]" in e and "ch_01" in e]
    assert order_errors, f"Ожидалась ошибка ORDER для ch_01, получено: {errors}"


# ──────────────────────────────────────────────────────────────────
# Тест 5: Uniqueness — один ref встречается дважды
# ──────────────────────────────────────────────────────────────────

def test_uniqueness_duplicate_ref():
    book = _book([_ch("ch_01", ["p1", "p2"])])
    layout = _layout([_page(1, "ch_01", ["p1", "p1", "p2"])])  # p1 дважды

    passed, errors = validate_fidelity(layout, book)

    assert passed is False
    uniq_errors = [e for e in errors if "[UNIQUENESS]" in e and "ch_01/p1" in e]
    assert uniq_errors, f"Ожидалась ошибка UNIQUENESS для ch_01/p1, получено: {errors}"


# ──────────────────────────────────────────────────────────────────
# Тест 6: Multi-chapter — две главы с независимыми paragraph-id
#   В каждой главе свои p1, p2 — это норма, не дубль
# ──────────────────────────────────────────────────────────────────

def test_multi_chapter_independent_ids_pass():
    book = _book([
        _ch("ch_01", ["p1", "p2"]),
        _ch("ch_02", ["p1", "p2", "p3"]),  # свои p1, p2 — это другая глава
    ])
    layout = _layout([
        _page(1, "ch_01", ["p1", "p2"]),
        _page(2, "ch_02", ["p1", "p2", "p3"]),
    ])

    passed, errors = validate_fidelity(layout, book)

    assert passed is True, f"Ожидался PASS, получены ошибки: {errors}"
    assert errors == []


# ──────────────────────────────────────────────────────────────────
# Тест 7: Legacy — layout использует paragraph_id вместо paragraph_ref
#   Validator должен поддерживать оба формата (v3.19 legacy)
# ──────────────────────────────────────────────────────────────────

def test_legacy_paragraph_id_field_accepted():
    book = _book([_ch("ch_01", ["p1", "p2"])])
    layout = _layout([_page(1, "ch_01", ["p1", "p2"], use_legacy=True)])  # paragraph_id

    passed, errors = validate_fidelity(layout, book)

    assert passed is True, f"Ожидался PASS для legacy paragraph_id, получено: {errors}"


# ──────────────────────────────────────────────────────────────────
# Тест 8: Element без chapter_id — fallback на chapter_id страницы
# ──────────────────────────────────────────────────────────────────

def test_chapter_id_falls_back_to_page():
    book = _book([_ch("ch_01", ["p1", "p2"])])
    # Элементы без своего chapter_id — должен браться со страницы
    layout = _layout([_page(1, "ch_01", ["p1", "p2"], omit_elem_chapter=True)])

    passed, errors = validate_fidelity(layout, book)

    assert passed is True, f"Ожидался PASS при page-level chapter_id, получено: {errors}"


# ──────────────────────────────────────────────────────────────────
# Тест 9: allow_mismatch=True возвращает (True, errors)
#   API-контракт: ошибки всё равно собираются, но passed=True
# ──────────────────────────────────────────────────────────────────

def test_allow_mismatch_returns_true_with_errors_collected():
    book = _book([_ch("ch_01", ["p1", "p2", "p3"])])
    layout = _layout([_page(1, "ch_01", ["p1", "p3"])])  # p2 пропущен

    passed, errors = validate_fidelity(layout, book, allow_mismatch=True)

    assert passed is True, "allow_mismatch=True всегда возвращает passed=True"
    assert errors, "Ошибки всё равно должны быть собраны для отчёта"
    assert any("p2" in e for e in errors)


# ──────────────────────────────────────────────────────────────────
# Тест 10: Book с content без paragraphs[] — парсинг из content
#   _collect_book_refs должен разбить content по \n\n и сгенерить p1, p2...
# ──────────────────────────────────────────────────────────────────

def test_book_content_parsed_into_paragraphs():
    book = {
        "chapters": [
            {
                "id": "ch_01",
                "title": "Глава 1",
                "content": "Первый абзац.\n\nВторой абзац.\n\nТретий абзац.",
                # paragraphs[] не задан — должен быть выведен из content
            }
        ]
    }
    layout = _layout([_page(1, "ch_01", ["p1", "p2", "p3"])])

    passed, errors = validate_fidelity(layout, book)

    assert passed is True, f"Ожидался PASS, ошибки: {errors}"


# ──────────────────────────────────────────────────────────────────
# Тест 11: Pages из layout_instructions (альтернативное расположение)
#   _collect_layout_refs ищет pages либо в layout["pages"],
#   либо в layout["layout_instructions"]["pages"]
# ──────────────────────────────────────────────────────────────────

def test_pages_under_layout_instructions():
    book = _book([_ch("ch_01", ["p1", "p2"])])
    layout = {
        "layout_instructions": {
            "pages": [_page(1, "ch_01", ["p1", "p2"])]
        }
    }

    passed, errors = validate_fidelity(layout, book)

    assert passed is True, f"Ожидался PASS, ошибки: {errors}"


# ──────────────────────────────────────────────────────────────────
# Тест 12: Не-валидируемые типы элементов (photo, etc.) игнорируются
#   После шага 3: callouts и historical_notes теперь валидируются,
#   но photo / bio_data_block / cover_* и т.д. — должны игнорироваться.
# ──────────────────────────────────────────────────────────────────

def test_unknown_element_types_ignored():
    book = _book([_ch("ch_01", ["p1", "p2"])])
    layout = {
        "pages": [
            {
                "page_number": 1,
                "chapter_id": "ch_01",
                "elements": [
                    {"type": "paragraph", "chapter_id": "ch_01", "paragraph_ref": "p1"},
                    {"type": "photo", "photo_id": "ph1"},                     # игнор
                    {"type": "bio_data_block", "content": {}},                # игнор
                    {"type": "cover_title", "text": "Заглавие"},              # игнор
                    {"type": "paragraph", "chapter_id": "ch_01", "paragraph_ref": "p2"},
                ],
            }
        ]
    }

    passed, errors = validate_fidelity(layout, book)

    assert passed is True, f"photo/bio_data/cover_* должны игнорироваться, ошибки: {errors}"


# ──────────────────────────────────────────────────────────────────
# Helpers для callout / historical_note
# ──────────────────────────────────────────────────────────────────

def _book_with_collections(
    chapters: list[dict],
    callouts: list[dict] | None = None,
    historical_notes: list[dict] | None = None,
) -> dict:
    b: dict = {"chapters": chapters}
    if callouts is not None:
        b["callouts"] = callouts
    if historical_notes is not None:
        b["historical_notes"] = historical_notes
    return b


def _co(co_id: str, chapter_id: str, text: str = "цитата") -> dict:
    return {"id": co_id, "chapter_id": chapter_id, "text": text}


def _hn(hn_id: str, chapter_id: str, text: str = "справка") -> dict:
    return {"id": hn_id, "chapter_id": chapter_id, "text": text}


def _co_elem(chapter_id: str, ref: str, *, use_legacy: bool = False) -> dict:
    elem = {"type": "callout", "chapter_id": chapter_id}
    if use_legacy:
        elem["callout_id"] = ref
    else:
        elem["callout_ref"] = ref
    return elem


def _hn_elem(chapter_id: str, ref: str) -> dict:
    return {"type": "historical_note", "chapter_id": chapter_id, "historical_note_ref": ref}


# ──────────────────────────────────────────────────────────────────
# Тест 13: Happy path — callouts корректно совпадают с book
# ──────────────────────────────────────────────────────────────────

def test_callouts_happy_path():
    book = _book_with_collections(
        [_ch("ch_02", ["p1"])],
        callouts=[_co("c01", "ch_02"), _co("c02", "ch_02")],
    )
    layout = _layout([
        {
            "page_number": 1,
            "chapter_id": "ch_02",
            "elements": [
                _para_elem("ch_02", "p1"),
                _co_elem("ch_02", "c01"),
                _co_elem("ch_02", "c02"),
            ],
        }
    ])

    passed, errors = validate_fidelity(layout, book)

    assert passed is True, f"Ожидался PASS, ошибки: {errors}"


# ──────────────────────────────────────────────────────────────────
# Тест 14: Callout пропущен в layout — completeness fail
#   (Конкретно случай регрессии v43 #1: 6 callouts в book, не все в PDF)
# ──────────────────────────────────────────────────────────────────

def test_callout_missing_in_layout():
    book = _book_with_collections(
        [_ch("ch_02", ["p1"])],
        callouts=[_co("c01", "ch_02"), _co("c02", "ch_02"), _co("c03", "ch_02")],
    )
    layout = _layout([
        {
            "page_number": 1, "chapter_id": "ch_02",
            "elements": [_para_elem("ch_02", "p1"), _co_elem("ch_02", "c01"), _co_elem("ch_02", "c03")],
            # c02 пропущен
        }
    ])

    passed, errors = validate_fidelity(layout, book)

    assert passed is False
    assert any("[COMPLETENESS][callout]" in e and "c02" in e for e in errors), \
        f"Ожидалась completeness-ошибка для callout c02, получено: {errors}"


# ──────────────────────────────────────────────────────────────────
# Тест 15: Callout продублирован в layout (между главами)
#   (Конкретно случай регрессии v43 #2: callouts повторены в чужих главах)
# ──────────────────────────────────────────────────────────────────

def test_callout_duplicated_across_chapters():
    book = _book_with_collections(
        [_ch("ch_02", ["p1"]), _ch("ch_03", ["p1"])],
        callouts=[_co("c01", "ch_02"), _co("c02", "ch_03")],
    )
    # LD ошибочно положил c01 и в ch_02, и в ch_03
    layout = _layout([
        {"page_number": 1, "chapter_id": "ch_02",
         "elements": [_para_elem("ch_02", "p1"), _co_elem("ch_02", "c01")]},
        {"page_number": 2, "chapter_id": "ch_03",
         "elements": [_para_elem("ch_03", "p1"), _co_elem("ch_03", "c01"), _co_elem("ch_03", "c02")]},
        # c01 во второй главе — это лишний ref для ch_03
    ])

    passed, errors = validate_fidelity(layout, book)

    assert passed is False
    callout_errors = [e for e in errors if "[callout]" in e]
    # Сначала должно быть «лишний ref» — c01 не принадлежит ch_03
    assert any("c01" in e and "лишний" in e for e in callout_errors), \
        f"Ожидалась ошибка про лишний c01 в ch_03, получено: {callout_errors}"


# ──────────────────────────────────────────────────────────────────
# Тест 16: Legacy field callout_id (текущие layouts до v3.20+) — работает
# ──────────────────────────────────────────────────────────────────

def test_callout_legacy_callout_id_field():
    book = _book_with_collections(
        [_ch("ch_02", ["p1"])],
        callouts=[_co("c01", "ch_02")],
    )
    layout = _layout([
        {"page_number": 1, "chapter_id": "ch_02",
         "elements": [_para_elem("ch_02", "p1"), _co_elem("ch_02", "c01", use_legacy=True)]},
    ])

    passed, errors = validate_fidelity(layout, book)

    assert passed is True, f"Legacy callout_id должен поддерживаться, ошибки: {errors}"


# ──────────────────────────────────────────────────────────────────
# Тест 17: Order callouts внутри одной главы — soft warning, не fail
#   order_strict=False для callouts (LD-вёрстка): перестановка → WARN, passed=True
# ──────────────────────────────────────────────────────────────────

def test_callout_order_violation_is_soft_warning(capsys):
    book = _book_with_collections(
        [_ch("ch_02", ["p1"])],
        callouts=[_co("c01", "ch_02"), _co("c02", "ch_02"), _co("c03", "ch_02")],
    )
    # В layout порядок переставлен: c01, c03, c02
    layout = _layout([
        {"page_number": 1, "chapter_id": "ch_02",
         "elements": [
             _para_elem("ch_02", "p1"),
             _co_elem("ch_02", "c01"),
             _co_elem("ch_02", "c03"),
             _co_elem("ch_02", "c02"),
         ]},
    ])

    passed, errors = validate_fidelity(layout, book)

    # passed остаётся True — ORDER для callouts не блокирует (order_strict=False)
    assert passed is True, f"Ожидался PASS (soft warning), но получили FAIL: {errors}"
    # И в errors не должно быть [ORDER][callout] — это soft warning, не error
    assert not any("[ORDER][callout]" in e for e in errors), \
        f"ORDER для callout не должен быть в errors, получили: {errors}"
    # При этом warning должен быть напечатан в stdout с префиксом [WARN][ORDER][callout]
    captured = capsys.readouterr()
    assert "[WARN]" in captured.out and "[ORDER][callout]" in captured.out, \
        f"Ожидался [WARN][ORDER][callout] в stdout, получили: {captured.out!r}"


# ──────────────────────────────────────────────────────────────────
# Тест 17b: Order historical_notes — тоже soft warning (симметрично callouts)
# ──────────────────────────────────────────────────────────────────

def test_historical_note_order_is_soft_warning(capsys):
    book = _book_with_collections(
        [_ch("ch_02", ["p1"])],
        historical_notes=[_hn("hist_01", "ch_02"), _hn("hist_02", "ch_02"), _hn("hist_03", "ch_02")],
    )
    # В layout порядок переставлен: hist_01, hist_03, hist_02
    layout = _layout([
        {"page_number": 1, "chapter_id": "ch_02",
         "elements": [
             _para_elem("ch_02", "p1"),
             _hn_elem("ch_02", "hist_01"),
             _hn_elem("ch_02", "hist_03"),
             _hn_elem("ch_02", "hist_02"),
         ]},
    ])

    passed, errors = validate_fidelity(layout, book)

    assert passed is True, f"Ожидался PASS, получили FAIL: {errors}"
    assert not any("[ORDER][historical_note]" in e for e in errors)
    captured = capsys.readouterr()
    assert "[WARN]" in captured.out and "[ORDER][historical_note]" in captured.out


# ──────────────────────────────────────────────────────────────────
# Тест 17c: COMPLETENESS для callout остаётся блокирующим
#   (только ORDER стал soft — не вся валидация callout стала мягкой)
# ──────────────────────────────────────────────────────────────────

def test_callout_completeness_still_blocking():
    book = _book_with_collections(
        [_ch("ch_02", ["p1"])],
        callouts=[_co("c01", "ch_02"), _co("c02", "ch_02")],
    )
    layout = _layout([
        {"page_number": 1, "chapter_id": "ch_02",
         "elements": [_para_elem("ch_02", "p1"), _co_elem("ch_02", "c01")]},
        # c02 пропущен — это всё ещё блокирующая ошибка
    ])

    passed, errors = validate_fidelity(layout, book)

    assert passed is False, "COMPLETENESS для callout должно быть блокирующим"
    assert any("[COMPLETENESS][callout]" in e and "c02" in e for e in errors)


# ──────────────────────────────────────────────────────────────────
# Тест 17d: ORDER для paragraph остаётся блокирующим (order_strict=True)
#   Симметрия: для paragraph order критичен (последовательность текста).
# ──────────────────────────────────────────────────────────────────

def test_paragraph_order_remains_blocking():
    """Sanity: order_strict=True для paragraph — ORDER violation = FAIL."""
    book = _book([_ch("ch_01", ["p1", "p2", "p3"])])
    layout = _layout([_page(1, "ch_01", ["p1", "p3", "p2"])])  # порядок переставлен

    passed, errors = validate_fidelity(layout, book)

    assert passed is False, "ORDER для paragraph должно блокировать (order_strict=True)"
    assert any("[ORDER]" in e for e in errors)


# ──────────────────────────────────────────────────────────────────
# Тест 18: Happy path — historical_notes
# ──────────────────────────────────────────────────────────────────

def test_historical_notes_happy_path():
    book = _book_with_collections(
        [_ch("ch_02", ["p1"])],
        historical_notes=[_hn("hist_01", "ch_02"), _hn("hist_02", "ch_02")],
    )
    layout = _layout([
        {"page_number": 1, "chapter_id": "ch_02",
         "elements": [
             _para_elem("ch_02", "p1"),
             _hn_elem("ch_02", "hist_01"),
             _hn_elem("ch_02", "hist_02"),
         ]},
    ])

    passed, errors = validate_fidelity(layout, book)

    assert passed is True, f"Ожидался PASS, ошибки: {errors}"


# ──────────────────────────────────────────────────────────────────
# Тест 19: Historical_note без id в layout (текущее legacy-поведение LD)
#   В layout элемент {type: historical_note, text: ...} без historical_note_ref —
#   validator должен зафейлить «отсутствует в layout» для каждого hist_NN из book.
#   Это ровно сигнал «LD не использует ссылочную архитектуру для hist_notes».
# ──────────────────────────────────────────────────────────────────

def test_historical_note_without_ref_treated_as_missing():
    book = _book_with_collections(
        [_ch("ch_02", ["p1"])],
        historical_notes=[_hn("hist_01", "ch_02")],
    )
    layout = _layout([
        {"page_number": 1, "chapter_id": "ch_02",
         "elements": [
             _para_elem("ch_02", "p1"),
             # Старый LD-формат: только text, без id
             {"type": "historical_note", "text": "Какая-то справка"},
         ]},
    ])

    passed, errors = validate_fidelity(layout, book)

    assert passed is False
    assert any("[COMPLETENESS][historical_note]" in e and "hist_01" in e for e in errors), \
        f"Ожидалось что hist_01 будет помечен как отсутствующий, получено: {errors}"


# ──────────────────────────────────────────────────────────────────
# Тест 20: Three types together — все три типа корректно валидируются параллельно
# ──────────────────────────────────────────────────────────────────

def test_three_types_together_pass():
    book = _book_with_collections(
        [_ch("ch_02", ["p1", "p2"]), _ch("ch_03", ["p1"])],
        callouts=[_co("c01", "ch_02"), _co("c02", "ch_03")],
        historical_notes=[_hn("hist_01", "ch_02")],
    )
    layout = _layout([
        {"page_number": 1, "chapter_id": "ch_02",
         "elements": [
             _para_elem("ch_02", "p1"),
             _co_elem("ch_02", "c01"),
             _hn_elem("ch_02", "hist_01"),
             _para_elem("ch_02", "p2"),
         ]},
        {"page_number": 2, "chapter_id": "ch_03",
         "elements": [
             _para_elem("ch_03", "p1"),
             _co_elem("ch_03", "c02"),
         ]},
    ])

    passed, errors = validate_fidelity(layout, book)

    assert passed is True, f"Все три типа должны пройти, ошибки: {errors}"


# ──────────────────────────────────────────────────────────────────
# Тест 21: Ошибки в разных типах копятся вместе (не «первая остановила»)
# ──────────────────────────────────────────────────────────────────

def test_errors_accumulate_across_ref_types():
    book = _book_with_collections(
        [_ch("ch_02", ["p1", "p2"])],
        callouts=[_co("c01", "ch_02")],
        historical_notes=[_hn("hist_01", "ch_02")],
    )
    # paragraph отсутствует, callout отсутствует, hist_note отсутствует
    layout = _layout([
        {"page_number": 1, "chapter_id": "ch_02",
         "elements": [_para_elem("ch_02", "p1")]},  # p2, c01, hist_01 — все пропущены
    ])

    passed, errors = validate_fidelity(layout, book)

    assert passed is False
    # Все три типа должны дать свою completeness-ошибку
    assert any("[COMPLETENESS]" in e and "p2" in e for e in errors)
    assert any("[COMPLETENESS][callout]" in e and "c01" in e for e in errors)
    assert any("[COMPLETENESS][historical_note]" in e and "hist_01" in e for e in errors)
