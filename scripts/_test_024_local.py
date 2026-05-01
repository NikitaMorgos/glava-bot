#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Local verification tests for task 024: chapter_start enforcement."""
import sys
import os
import copy

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from test_stage4_karakulina import enforce_chapter_start_purity


def _make_layout(pages):
    return {"_layout_format": "pages_json", "pages": pages}


def test_024_clean_page_untouched():
    """chapter_start with only allowed elements is not modified."""
    layout = _make_layout([
        {
            "page_number": 1,
            "type": "chapter_start",
            "chapter_id": "ch_01",
            "elements": [
                {"type": "chapter_title"},
                {"type": "photo_placeholder"},
            ],
        }
    ])
    result = enforce_chapter_start_purity(layout)
    page = result["pages"][0]
    assert len(page["elements"]) == 2
    print("[PASS] test_024_clean_page_untouched")


def test_024_auto_clean_moves_text():
    """Illegal elements on chapter_start are moved to next page."""
    layout = _make_layout([
        {
            "page_number": 3,
            "type": "chapter_start",
            "chapter_id": "ch_02",
            "elements": [
                {"type": "chapter_title"},
                {"type": "photo_placeholder"},
                {"type": "paragraph", "paragraph_ref": "p1", "chapter_id": "ch_02"},
                {"type": "paragraph", "paragraph_ref": "p2", "chapter_id": "ch_02"},
            ],
        },
        {
            "page_number": 4,
            "type": "chapter_body",
            "chapter_id": "ch_02",
            "elements": [
                {"type": "paragraph", "paragraph_ref": "p3", "chapter_id": "ch_02"},
            ],
        },
    ])
    result = enforce_chapter_start_purity(layout)
    pages = result["pages"]

    assert len(pages) == 2, "No new page should be created when next page already exists"
    chapter_start = pages[0]
    next_page = pages[1]

    # chapter_start should only have allowed elements
    illegal_in_cs = [e for e in chapter_start["elements"] if e.get("type") in ("paragraph", "callout", "subheading")]
    assert len(illegal_in_cs) == 0, f"Illegal elements remain: {illegal_in_cs}"

    # Next page should have the moved elements at the front
    assert next_page["elements"][0]["paragraph_ref"] == "p1"
    assert next_page["elements"][1]["paragraph_ref"] == "p2"
    assert next_page["elements"][2]["paragraph_ref"] == "p3"
    print("[PASS] test_024_auto_clean_moves_text")


def test_024_creates_new_page_when_needed():
    """New page is created when chapter_start is last page for the chapter."""
    layout = _make_layout([
        {
            "page_number": 9,
            "type": "chapter_start",
            "chapter_id": "ch_03",
            "elements": [
                {"type": "chapter_title"},
                {"type": "subheading", "subheading_ref": "p1", "chapter_id": "ch_03"},
                {"type": "paragraph", "paragraph_ref": "p2", "chapter_id": "ch_03"},
            ],
        },
        {
            "page_number": 10,
            "type": "chapter_start",
            "chapter_id": "ch_04",
            "elements": [],
        },
    ])
    result = enforce_chapter_start_purity(layout)
    pages = result["pages"]

    assert len(pages) == 3, f"New page should have been created, got {len(pages)} pages"
    assert pages[0]["page_number"] == 9
    assert pages[1]["page_number"] == 10  # new page for ch_03
    assert pages[1]["chapter_id"] == "ch_03"
    assert pages[1]["type"] == "chapter_body"
    assert pages[2]["page_number"] == 11  # ch_04 chapter_start renumbered
    print("[PASS] test_024_creates_new_page_when_needed")


def test_024_strict_mode_exits():
    """--strict-chapter-start causes sys.exit(1)."""
    import pytest
    layout = _make_layout([
        {
            "page_number": 3,
            "type": "chapter_start",
            "chapter_id": "ch_02",
            "elements": [
                {"type": "paragraph", "paragraph_ref": "p1", "chapter_id": "ch_02"},
            ],
        },
    ])
    try:
        enforce_chapter_start_purity(layout, strict=True)
        print("[FAIL] Expected sys.exit but didn't get it")
        sys.exit(1)
    except SystemExit as e:
        assert e.code == 1
        print("[PASS] test_024_strict_mode_exits")


def test_024_allow_mode_skips():
    """--allow-chapter-start-text disables enforcement entirely."""
    layout = _make_layout([
        {
            "page_number": 3,
            "type": "chapter_start",
            "chapter_id": "ch_02",
            "elements": [
                {"type": "paragraph", "paragraph_ref": "p1", "chapter_id": "ch_02"},
            ],
        },
    ])
    result = enforce_chapter_start_purity(layout, allow_chapter_start_text=True)
    # Should not move anything
    assert len(result["pages"][0]["elements"]) == 1
    print("[PASS] test_024_allow_mode_skips")


if __name__ == "__main__":
    test_024_clean_page_untouched()
    test_024_auto_clean_moves_text()
    test_024_creates_new_page_when_needed()
    test_024_strict_mode_exits()
    test_024_allow_mode_skips()
    print("\n✅ Все локальные тесты 024 прошли")
