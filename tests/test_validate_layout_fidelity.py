"""Тесты для validate_layout_fidelity.py (safety net для рефакторинга задачи 025+).

12 тестов: completeness, order, uniqueness, happy-path, allow_mismatch, legacy fallback.
"""

import pytest
from scripts.validate_layout_fidelity import validate_fidelity


# ─── helpers ──────────────────────────────────────────────────────────────────

def _book(chapters):
    return {"chapters": chapters}


def _chapter(ch_id, paragraphs=None, content=None):
    ch = {"id": ch_id}
    if paragraphs is not None:
        ch["paragraphs"] = [{"id": p} for p in paragraphs]
    elif content is not None:
        ch["content"] = content
    return ch


def _layout(pages):
    return {"pages": pages}


def _page(page_number, elements, chapter_id=""):
    return {"page_number": page_number, "chapter_id": chapter_id, "elements": elements}


def _para_elem(ref, chapter_id="", use_legacy=False):
    elem = {"type": "paragraph"}
    if use_legacy:
        elem["paragraph_id"] = ref
    else:
        elem["paragraph_ref"] = ref
    if chapter_id:
        elem["chapter_id"] = chapter_id
    return elem


# ─── happy path ───────────────────────────────────────────────────────────────

def test_happy_path_all_ok():
    book = _book([_chapter("ch1", paragraphs=["p1", "p2", "p3"])])
    layout = _layout([
        _page(1, [
            _para_elem("p1", "ch1"),
            _para_elem("p2", "ch1"),
            _para_elem("p3", "ch1"),
        ]),
    ])
    passed, errors = validate_fidelity(layout, book)
    assert passed is True
    assert errors == []


def test_happy_path_two_chapters():
    book = _book([
        _chapter("ch1", paragraphs=["p1", "p2"]),
        _chapter("ch2", paragraphs=["p3", "p4"]),
    ])
    layout = _layout([
        _page(1, [_para_elem("p1", "ch1"), _para_elem("p2", "ch1")]),
        _page(2, [_para_elem("p3", "ch2"), _para_elem("p4", "ch2")]),
    ])
    passed, errors = validate_fidelity(layout, book)
    assert passed is True
    assert errors == []


# ─── completeness ─────────────────────────────────────────────────────────────

def test_completeness_missing_in_layout():
    book = _book([_chapter("ch1", paragraphs=["p1", "p2"])])
    layout = _layout([
        _page(1, [_para_elem("p1", "ch1")]),  # p2 отсутствует
    ])
    passed, errors = validate_fidelity(layout, book)
    assert passed is False
    assert any("[COMPLETENESS]" in e and "p2" in e for e in errors)


def test_completeness_extra_in_layout():
    book = _book([_chapter("ch1", paragraphs=["p1"])])
    layout = _layout([
        _page(1, [_para_elem("p1", "ch1"), _para_elem("p99", "ch1")]),  # p99 лишний
    ])
    passed, errors = validate_fidelity(layout, book)
    assert passed is False
    assert any("[COMPLETENESS]" in e and "p99" in e for e in errors)


# ─── order ────────────────────────────────────────────────────────────────────

def test_order_wrong():
    book = _book([_chapter("ch1", paragraphs=["p1", "p2", "p3"])])
    layout = _layout([
        _page(1, [
            _para_elem("p1", "ch1"),
            _para_elem("p3", "ch1"),
            _para_elem("p2", "ch1"),
        ]),
    ])
    passed, errors = validate_fidelity(layout, book)
    assert passed is False
    assert any("[ORDER]" in e for e in errors)


def test_order_correct():
    book = _book([_chapter("ch1", paragraphs=["p1", "p2", "p3"])])
    layout = _layout([
        _page(1, [
            _para_elem("p1", "ch1"),
            _para_elem("p2", "ch1"),
            _para_elem("p3", "ch1"),
        ]),
    ])
    passed, errors = validate_fidelity(layout, book)
    assert passed is True
    assert not any("[ORDER]" in e for e in errors)


# ─── uniqueness ───────────────────────────────────────────────────────────────

def test_uniqueness_duplicate():
    book = _book([_chapter("ch1", paragraphs=["p1", "p2"])])
    layout = _layout([
        _page(1, [
            _para_elem("p1", "ch1"),
            _para_elem("p1", "ch1"),  # дубль
            _para_elem("p2", "ch1"),
        ]),
    ])
    passed, errors = validate_fidelity(layout, book)
    assert passed is False
    assert any("[UNIQUENESS]" in e and "p1" in e for e in errors)


def test_uniqueness_no_duplicates():
    book = _book([_chapter("ch1", paragraphs=["p1", "p2"])])
    layout = _layout([
        _page(1, [_para_elem("p1", "ch1"), _para_elem("p2", "ch1")]),
    ])
    passed, errors = validate_fidelity(layout, book)
    assert passed is True
    assert not any("[UNIQUENESS]" in e for e in errors)


# ─── allow_mismatch ───────────────────────────────────────────────────────────

def test_allow_mismatch_returns_true_despite_errors():
    book = _book([_chapter("ch1", paragraphs=["p1", "p2"])])
    layout = _layout([
        _page(1, [_para_elem("p1", "ch1")]),  # p2 отсутствует
    ])
    passed, errors = validate_fidelity(layout, book, allow_mismatch=True)
    assert passed is True
    assert len(errors) > 0


# ─── legacy fallback (paragraph_id) ──────────────────────────────────────────

def test_legacy_paragraph_id_fallback():
    """paragraph_id в layout-элементе должен работать как paragraph_ref."""
    book = _book([_chapter("ch1", paragraphs=["p1", "p2"])])
    layout = _layout([
        _page(1, [
            _para_elem("p1", "ch1", use_legacy=True),
            _para_elem("p2", "ch1", use_legacy=True),
        ]),
    ])
    passed, errors = validate_fidelity(layout, book)
    assert passed is True
    assert errors == []


# ─── content fallback (book без paragraphs) ──────────────────────────────────

def test_book_content_fallback():
    """Если в главе нет paragraphs[], refs берутся из content по \\n\\n."""
    content = "Абзац первый.\n\nАбзац второй.\n\nАбзац третий."
    book = _book([_chapter("ch1", content=content)])
    # refs будут p1, p2, p3
    layout = _layout([
        _page(1, [
            _para_elem("p1", "ch1"),
            _para_elem("p2", "ch1"),
            _para_elem("p3", "ch1"),
        ]),
    ])
    passed, errors = validate_fidelity(layout, book)
    assert passed is True
    assert errors == []


# ─── page-level chapter_id fallback ──────────────────────────────────────────

def test_page_level_chapter_id_fallback():
    """chapter_id на уровне страницы должен применяться к элементам без chapter_id."""
    book = _book([_chapter("ch1", paragraphs=["p1", "p2"])])
    layout = _layout([
        _page(1, [
            _para_elem("p1"),   # нет chapter_id — берём со страницы
            _para_elem("p2"),
        ], chapter_id="ch1"),
    ])
    passed, errors = validate_fidelity(layout, book)
    assert passed is True
    assert errors == []
