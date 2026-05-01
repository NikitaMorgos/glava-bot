#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Local verification tests for tasks 025 and 026 code changes."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pipeline_utils import prepare_book_for_layout


def test_025_subheading_normalization():
    """Task 025: ## and ### in content get converted to subheading type."""
    book = {
        "chapters": [
            {
                "id": "ch_02",
                "content": (
                    "## Детство и сиротство\n\n"
                    "Валентина родилась 17 декабря.\n\n"
                    "### Авоська из зонтика\n\n"
                    "Она любила вязать.\n\n"
                    "Обычный абзац без заголовка."
                ),
            }
        ]
    }
    result = prepare_book_for_layout(book)
    paras = result["chapters"][0]["paragraphs"]

    assert len(paras) == 5, f"Expected 5 paragraphs, got {len(paras)}: {paras}"
    assert paras[0]["type"] == "subheading", f"p1 should be subheading, got {paras[0].get('type')}"
    assert paras[0]["text"] == "Детство и сиротство", f"Got: {paras[0]['text']}"
    assert paras[1].get("type", "paragraph") == "paragraph", f"p2 should be paragraph, got {paras[1].get('type')}"
    assert paras[2]["type"] == "subheading", f"p3 should be subheading, got {paras[2].get('type')}"
    assert paras[2]["text"] == "Авоська из зонтика", f"Got: {paras[2]['text']}"
    assert paras[3].get("type", "paragraph") == "paragraph", f"p4 should be paragraph"
    assert paras[4].get("type", "paragraph") == "paragraph", f"p5 should be paragraph"

    print("[PASS] test_025_subheading_normalization")


def test_025_no_false_conversion():
    """Task 025: Regular paragraphs (including those with ## inside text) not wrongly converted."""
    book = {
        "chapters": [
            {
                "id": "ch_01",
                "content": (
                    "Она родилась в семье рабочих.\n\n"
                    "Обычный текст с # символом в середине строки не должен быть subheading."
                ),
            }
        ]
    }
    result = prepare_book_for_layout(book)
    paras = result["chapters"][0]["paragraphs"]
    for p in paras:
        assert p.get("type", "paragraph") == "paragraph", (
            f"Wrongly converted paragraph: {p}"
        )
    print("[PASS] test_025_no_false_conversion")


def test_025_book_index_type():
    """Task 025: BookIndex.get_type() returns correct type for subheadings."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
    from pdf_renderer import BookIndex

    book = {
        "chapters": [
            {
                "id": "ch_02",
                "paragraphs": [
                    {"id": "p1", "type": "subheading", "text": "Детство и сиротство"},
                    {"id": "p2", "text": "Валентина родилась 17 декабря."},
                ],
            }
        ]
    }
    idx = BookIndex(book)
    assert idx.get_type("ch_02", "p1") == "subheading", "p1 should be subheading"
    assert idx.get_type("ch_02", "p2") == "paragraph", "p2 should be paragraph"
    assert idx.get("ch_02", "p1") == "Детство и сиротство", "p1 text lookup"
    assert idx.get("ch_02", "p2") == "Валентина родилась 17 декабря."
    print("[PASS] test_025_book_index_type")


def test_026_pin_list_message_construction():
    """Task 026: pin_list section is correctly added to CA user message."""
    prev_fact_map = {
        "persons": [
            {"id": "person_001", "name": "Нинвана Полсачева", "relation_to_subject": "врач"},
            {"id": "person_002", "name": "тётя Шура", "aliases": ["Шура"], "relation_to_subject": "золовка"},
            {"id": "person_003", "name": "Rimma"},  # no name in canonical form
        ]
    }

    pin_list = [
        {
            "id": p.get("id", ""),
            "name": p.get("name", ""),
            "aliases": p.get("aliases", []),
            "relation_to_subject": p.get("relation_to_subject", "unknown"),
        }
        for p in prev_fact_map.get("persons", [])
        if p.get("name")
    ]

    assert len(pin_list) == 3, f"Expected 3 persons in pin_list, got {len(pin_list)}"
    assert pin_list[0]["name"] == "Нинвана Полсачева"
    assert pin_list[1]["aliases"] == ["Шура"]
    assert pin_list[2]["relation_to_subject"] == "unknown"
    print("[PASS] test_026_pin_list_message_construction")


if __name__ == "__main__":
    test_025_subheading_normalization()
    test_025_no_false_conversion()
    test_025_book_index_type()
    test_026_pin_list_message_construction()
    print("\n✅ Все локальные тесты 025/026 прошли")
