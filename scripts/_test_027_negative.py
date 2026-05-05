#!/usr/bin/env python3
"""Task 027 — negative test: enforce_bio_data_completeness must activate auto-fill
when GW produces a minimal bio_data.family (regression to v40 scenario).

Run: pytest scripts/_test_027_negative.py -v
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pipeline_utils import enforce_bio_data_completeness


def _make_minimal_book(family_entries):
    """book_FINAL with only the given family entries in ch_01."""
    return {
        "chapters": [
            {
                "id": "ch_01",
                "title": "Основные даты жизни",
                "bio_data": {
                    "family": family_entries
                }
            }
        ]
    }


def _make_karakulina_fact_map():
    """Full Karakulina fact_map with 17 family persons (relation_to_subject format)."""
    family_data = [
        ("person_001", "Рудай Иван Андреевич", "отец"),
        ("person_002", "Рудая Пелагея Алексеевна", "мать"),
        ("person_003", "младший брат", "младший брат"),
        ("person_004", "Полина Амельченко", "старшая сестра"),
        ("person_005", "тётя Маня", "старшая сестра"),
        ("person_006", "Каракулин Дмитрий", "муж"),
        ("person_007", "Каракулин Валерий", "сын"),
        ("person_008", "Каракулина Татьяна", "дочь"),
        ("person_009", "тётя Шура", "золовка (сестра мужа)"),
        ("person_010", "Маргось Владимир", "зять"),
        ("person_011", "Кужба Олег", "зять"),
        ("person_012", "Никита", "внук"),
        ("person_013", "Даша", "внучка"),
        ("person_014", "Толя", "племянник"),
        ("person_015", "Коля", "племянник"),
        ("person_016", "Витя", "племянник"),
        ("person_017", "Римма", "племянница (дочь золовки)"),
        ("person_018", "Зина", "племянница (дочь золовки)"),
        # Non-family — should NOT be auto-filled
        ("person_019", "тётя Маша", "соседка"),
        ("person_020", "Нинвана Полсачева", "врач"),
    ]
    return {
        "project_id": "karakulina",
        "persons": [
            {"id": pid, "name": name, "relation_to_subject": rel}
            for pid, name, rel in family_data
        ]
    }


MINIMAL_FAMILY = [
    {"label": "Муж", "value": "Каракулин Дмитрий"},
    {"label": "Дочь", "value": "Каракулина Татьяна"},
    {"label": "Отец", "value": "Рудай Иван Андреевич"},
    {"label": "Мать", "value": "Рудая Пелагея Алексеевна"},
]


def test_autofill_activates_on_minimal_bio_data():
    """Auto-fill must trigger and add >= 13 persons when book has only 4 family entries.

    Note: Каракулин Валерий (сын) is not auto-filled because the substring 'каракулин'
    already appears in the existing 'Каракулин Дмитрий' entry — intentional dedup behavior.
    Effective auto-fill count: 13, total entries: 17.
    """
    book = _make_minimal_book(list(MINIMAL_FAMILY))
    fact_map = _make_karakulina_fact_map()

    result = enforce_bio_data_completeness(book, fact_map, strict=False)

    family = result["chapters"][0]["bio_data"]["family"]
    autofilled = [e for e in family if e.get("source") == "auto-filled"]

    assert len(family) >= 17, (
        f"Expected >= 17 family entries after auto-fill, got {len(family)}"
    )
    assert len(autofilled) >= 13, (
        f"Expected >= 13 auto-filled entries, got {len(autofilled)}"
    )


def test_autofill_entries_have_correct_structure():
    """Auto-filled entries must have label, value, source='auto-filled'."""
    book = _make_minimal_book(list(MINIMAL_FAMILY))
    fact_map = _make_karakulina_fact_map()

    result = enforce_bio_data_completeness(book, fact_map, strict=False)
    family = result["chapters"][0]["bio_data"]["family"]
    autofilled = [e for e in family if e.get("source") == "auto-filled"]

    for entry in autofilled:
        assert "label" in entry, f"Missing 'label' in {entry}"
        assert "value" in entry, f"Missing 'value' in {entry}"
        assert entry["value"], f"Empty 'value' in {entry}"
        assert entry["source"] == "auto-filled"


def test_autofill_includes_specific_missing_persons():
    """Key previously-unstable persons must be auto-filled."""
    book = _make_minimal_book(list(MINIMAL_FAMILY))
    fact_map = _make_karakulina_fact_map()

    result = enforce_bio_data_completeness(book, fact_map, strict=False)
    family = result["chapters"][0]["bio_data"]["family"]
    values_lower = [e.get("value", "").lower() for e in family]

    for expected in ["тётя маня", "тётя шура", "римма", "зина"]:
        found = any(expected in v for v in values_lower)
        assert found, (
            f"Expected '{expected}' to be present in bio_data.family after auto-fill, "
            f"but not found. Entries: {values_lower}"
        )


def test_neighbour_not_autofilled():
    """Non-family persons (соседка, врач) must NOT be auto-filled."""
    book = _make_minimal_book(list(MINIMAL_FAMILY))
    fact_map = _make_karakulina_fact_map()

    result = enforce_bio_data_completeness(book, fact_map, strict=False)
    family = result["chapters"][0]["bio_data"]["family"]
    values_lower = [e.get("value", "").lower() for e in family]

    for non_family in ["тётя маша", "нинвана"]:
        found = any(non_family in v for v in values_lower)
        assert not found, (
            f"Non-family person '{non_family}' should NOT be in bio_data.family, "
            f"but was found. Entries: {values_lower}"
        )


def test_ziat_detected_as_family():
    """'зять' relation must be detected as family (regression fix for missing зять in _FAMILY_RELATIONS)."""
    book = _make_minimal_book([])
    fact_map = {
        "persons": [
            {"id": "p1", "name": "Маргось Владимир", "relation_to_subject": "зять"}
        ]
    }

    result = enforce_bio_data_completeness(book, fact_map, strict=False)
    family = result["chapters"][0]["bio_data"]["family"]

    assert len(family) == 1, f"Expected 1 auto-filled entry for зять, got {len(family)}"
    assert family[0]["value"] == "Маргось Владимир"
    assert family[0]["source"] == "auto-filled"


def test_strict_raises_on_minimal_bio_data():
    """strict=True must raise RuntimeError when persons are missing."""
    import pytest
    book = _make_minimal_book(list(MINIMAL_FAMILY))
    fact_map = _make_karakulina_fact_map()

    with pytest.raises(RuntimeError, match="STRICT"):
        enforce_bio_data_completeness(book, fact_map, strict=True)


def test_no_duplicates_when_already_complete():
    """When bio_data already has all persons, no entries are added."""
    all_family = [
        {"label": rel, "value": name}
        for _, name, rel in [
            ("p1", "Рудай Иван Андреевич", "отец"),
            ("p2", "Рудая Пелагея Алексеевна", "мать"),
            ("p3", "младший брат", "младший брат"),
            ("p4", "Полина Амельченко", "старшая сестра"),
            ("p5", "тётя Маня", "старшая сестра"),
            ("p6", "Каракулин Дмитрий", "муж"),
            ("p7", "Каракулин Валерий", "сын"),
            ("p8", "Каракулина Татьяна", "дочь"),
            ("p9", "тётя Шура", "золовка"),
            ("p10", "Маргось Владимир", "зять"),
            ("p11", "Кужба Олег", "зять"),
            ("p12", "Никита", "внук"),
            ("p13", "Даша", "внучка"),
            ("p14", "Толя", "племянник"),
            ("p15", "Коля", "племянник"),
            ("p16", "Витя", "племянник"),
            ("p17", "Римма", "племянница"),
            ("p18", "Зина", "племянница"),
        ]
    ]
    book = _make_minimal_book(all_family)
    fact_map = _make_karakulina_fact_map()
    before_count = len(all_family)

    result = enforce_bio_data_completeness(book, fact_map, strict=False)
    after_count = len(result["chapters"][0]["bio_data"]["family"])

    assert after_count == before_count, (
        f"Expected no additions when already complete ({before_count}), "
        f"got {after_count}"
    )
