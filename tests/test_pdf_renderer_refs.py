#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit-тесты для ref-резолва в pdf_renderer.py (волна 1.1, шаг 5).

Покрывают:
  BookIndex
    1. get_callout — резолв text по callout_id
    2. get_callout — None для несуществующего id
    3. get_historical_note — резолв text по note_id
    4. get_historical_note — None для несуществующего id
    5. BookIndex(None) — пустые getters не падают

  PdfRenderer._elem_callout_text
    6. callout_ref резолвится из book.callouts[]
    7. legacy callout_id (текущие сохранённые layout'ы) — тоже резолвится
    8. inline text/content (нет id) — fallback (legacy совместимость)
    9. strict_refs=True + ref не найден → ValueError
   10. strict_refs=True + allow_missing_refs=True → fallback на inline / пустую строку

  PdfRenderer._elem_historical_note_text
   11. historical_note_ref резолвится из book.historical_notes[]
   12. inline text fallback (старые layout'ы без id)
   13. strict_refs=True + ref не найден → ValueError

  Sanity: _elem_para_text не сломан рефакторингом
   14. paragraph_ref продолжает работать как раньше
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from pdf_renderer import BookIndex, PdfRenderer, RenderOptions


# ──────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────

def _make_book() -> dict:
    return {
        "chapters": [
            {
                "id": "ch_02",
                "paragraphs": [
                    {"id": "p1", "text": "Текст абзаца 1."},
                    {"id": "p2", "text": "Текст абзаца 2."},
                ],
            }
        ],
        "callouts": [
            {"id": "callout_01", "chapter_id": "ch_02", "text": "Текст выноски 1"},
            {"id": "callout_02", "chapter_id": "ch_02", "text": "Текст выноски 2"},
        ],
        "historical_notes": [
            {"id": "hist_01", "chapter_id": "ch_02", "text": "В 1933 году..."},
            {"id": "hist_02", "chapter_id": "ch_02", "text": "23 июня 1941..."},
        ],
    }


def _make_renderer(book: dict | None, *, strict_refs: bool = False,
                   allow_missing_refs: bool = False) -> PdfRenderer:
    """
    Создаёт «минимальный» инстанс PdfRenderer для тестирования helper-методов
    без запуска тяжёлой инициализации (шрифты, geometry).

    Инициализирует только атрибуты, которые читают помощники (_elem_*_text):
    book_index, options, и счётчики _ref_resolved / _ref_missing
    (добавлены Курсором в полную инициализацию для post-render аудита).
    """
    r = PdfRenderer.__new__(PdfRenderer)
    r.book_index = BookIndex(book)
    r.options = RenderOptions(
        strict_refs=strict_refs,
        allow_missing_refs=allow_missing_refs,
    )
    r._ref_resolved = 0
    r._ref_missing = 0
    return r


# ──────────────────────────────────────────────────────────────────
# BookIndex tests
# ──────────────────────────────────────────────────────────────────

def test_book_index_get_callout_resolves():
    idx = BookIndex(_make_book())
    assert idx.get_callout("callout_01") == "Текст выноски 1"
    assert idx.get_callout("callout_02") == "Текст выноски 2"


def test_book_index_get_callout_unknown_returns_none():
    idx = BookIndex(_make_book())
    assert idx.get_callout("callout_99") is None


def test_book_index_get_historical_note_resolves():
    idx = BookIndex(_make_book())
    assert idx.get_historical_note("hist_01") == "В 1933 году..."
    assert idx.get_historical_note("hist_02") == "23 июня 1941..."


def test_book_index_get_historical_note_unknown_returns_none():
    idx = BookIndex(_make_book())
    assert idx.get_historical_note("hist_99") is None


def test_book_index_none_book_safe():
    """BookIndex(None) — пустые getters не падают."""
    idx = BookIndex(None)
    assert idx.get_callout("callout_01") is None
    assert idx.get_historical_note("hist_01") is None
    assert idx.get("ch_02", "p1") is None


# ──────────────────────────────────────────────────────────────────
# _elem_callout_text
# ──────────────────────────────────────────────────────────────────

def test_callout_ref_resolves():
    """v3.21+: callout_ref → book.callouts[].text."""
    r = _make_renderer(_make_book())
    elem = {"type": "callout", "chapter_id": "ch_02", "callout_ref": "callout_01"}
    assert r._elem_callout_text(elem) == "Текст выноски 1"


def test_callout_legacy_callout_id_resolves():
    """Текущие сохранённые layout'ы используют callout_id — тоже должен резолвиться."""
    r = _make_renderer(_make_book())
    elem = {"type": "callout", "callout_id": "callout_02", "text": "stale inline"}
    # ref резолвится в приоритет, inline text игнорируется
    assert r._elem_callout_text(elem) == "Текст выноски 2"


def test_callout_inline_fallback_when_no_id():
    """Если нет ни callout_ref ни callout_id — берём inline text/content (legacy)."""
    r = _make_renderer(_make_book())
    elem = {"type": "callout", "text": "Inline-текст без ID"}
    assert r._elem_callout_text(elem) == "Inline-текст без ID"
    # content имеет приоритет над text если оба заданы
    elem2 = {"type": "callout", "content": "из content", "text": "из text"}
    assert r._elem_callout_text(elem2) == "из content"


def test_callout_strict_refs_raises_on_missing():
    """strict_refs + ref на несуществующий id → ValueError."""
    r = _make_renderer(_make_book(), strict_refs=True)
    elem = {"type": "callout", "callout_ref": "callout_99"}
    with pytest.raises(ValueError, match="callout_99"):
        r._elem_callout_text(elem)


def test_callout_strict_refs_with_allow_missing_falls_back():
    """strict_refs + allow_missing_refs → не падает, fallback на inline."""
    r = _make_renderer(_make_book(), strict_refs=True, allow_missing_refs=True)
    elem = {"type": "callout", "callout_ref": "callout_99", "text": "fallback inline"}
    # ValueError не поднимается, возвращается inline text
    assert r._elem_callout_text(elem) == "fallback inline"


def test_callout_no_book_inline_works():
    """Если book_index пустой (BookIndex(None)) — inline text работает."""
    r = _make_renderer(None)
    elem = {"type": "callout", "text": "только inline"}
    assert r._elem_callout_text(elem) == "только inline"


# ──────────────────────────────────────────────────────────────────
# _elem_historical_note_text
# ──────────────────────────────────────────────────────────────────

def test_historical_note_ref_resolves():
    """v3.21+: historical_note_ref → book.historical_notes[].text."""
    r = _make_renderer(_make_book())
    elem = {"type": "historical_note", "chapter_id": "ch_02", "historical_note_ref": "hist_01"}
    assert r._elem_historical_note_text(elem) == "В 1933 году..."


def test_historical_note_inline_fallback():
    """Все сохранённые до v3.21 layout'ы имеют historical_note без id, только text."""
    r = _make_renderer(_make_book())
    elem = {"type": "historical_note", "text": "Старый inline текст справки"}
    assert r._elem_historical_note_text(elem) == "Старый inline текст справки"


def test_historical_note_strict_refs_raises():
    r = _make_renderer(_make_book(), strict_refs=True)
    elem = {"type": "historical_note", "historical_note_ref": "hist_99"}
    with pytest.raises(ValueError, match="hist_99"):
        r._elem_historical_note_text(elem)


def test_historical_note_alt_ref_field_note_ref():
    """Поддержка альтернативного поля note_ref (legacy variant)."""
    r = _make_renderer(_make_book())
    elem = {"type": "historical_note", "note_ref": "hist_02"}
    assert r._elem_historical_note_text(elem) == "23 июня 1941..."


# ──────────────────────────────────────────────────────────────────
# Sanity: paragraph behavior unchanged
# ──────────────────────────────────────────────────────────────────

def test_paragraph_ref_still_works():
    """После рефакторинга _elem_para_text продолжает работать как раньше."""
    r = _make_renderer(_make_book())
    elem = {"type": "paragraph", "chapter_id": "ch_02", "paragraph_ref": "p1"}
    assert r._elem_para_text(elem) == "Текст абзаца 1."


def test_paragraph_legacy_paragraph_id_still_works():
    """Legacy paragraph_id (v3.19) совместимость сохранена."""
    r = _make_renderer(_make_book())
    elem = {"type": "paragraph", "chapter_id": "ch_02", "paragraph_id": "p2"}
    assert r._elem_para_text(elem) == "Текст абзаца 2."
