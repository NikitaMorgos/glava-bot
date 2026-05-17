"""Tests for Task 044: apply_relation_overrides + enforce_persona_notes."""
import copy
import pytest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline_utils import apply_relation_overrides, enforce_persona_notes


OVERRIDES_CFG = {
    "subject_id": "test",
    "overrides": [
        {
            "person_name": "тётя Маша",
            "aliases": ["Маша соседка"],
            "ca_relation": "тётя",
            "real_relation": "соседка",
            "in_bio_data_family": False,
        },
        {
            "person_name": "Баба Аня",
            "aliases": ["баба Аня"],
            "ca_relation": "свекровь или родственница зятя",
            "real_relation": "свекровь рассказчика",
            "in_bio_data_family": False,
        },
    ],
}

PERSONA_NOTES_CFG = {
    "subject_id": "test",
    "required_notes": [
        {
            "label_match": "Полина",
            "note": "забрала из детдома",
            "note_keywords": ["забрал", "детдом"],
            "replacement_policy": "replace_if_conflict",
        },
        {
            "label_match": "Татьяна",
            "note": "рассказчик интервью",
            "note_keywords": ["рассказчик"],
            "replacement_policy": "append_if_missing",
        },
    ],
    "separate_entries_required": [
        {
            "merged_label_pattern": "Внуки",
            "split_into": [
                {"label": "Внук", "value_keyword": "Никита"},
                {"label": "Внучка", "value_keyword": "Даша"},
            ],
        }
    ],
}


def _make_fact_map(persons):
    return {"persons": persons}


def _make_book(family_entries):
    return {
        "chapters": [
            {
                "id": "ch_01",
                "bio_data": {"family": family_entries},
                "content": "",
            }
        ]
    }


class TestApplyRelationOverrides:
    def test_tiotia_masha_corrected(self):
        fm = _make_fact_map([{"name": "тётя Маша", "relation_to_subject": "тётя"}])
        patched_fm, corrections = apply_relation_overrides(fm, OVERRIDES_CFG)
        assert corrections, "Должна быть хотя бы одна коррекция"
        assert corrections[0]["real_relation"] == "соседка"
        p = patched_fm["persons"][0]
        assert p["relation_to_subject"] == "соседка"
        assert p.get("in_bio_data_family") is False

    def test_alias_match(self):
        fm = _make_fact_map([{"name": "Маша соседка", "relation_to_subject": "тётя"}])
        _, corrections = apply_relation_overrides(fm, OVERRIDES_CFG)
        assert corrections

    def test_no_match(self):
        fm = _make_fact_map([{"name": "Полина", "relation_to_subject": "сестра"}])
        _, corrections = apply_relation_overrides(fm, OVERRIDES_CFG)
        assert not corrections

    def test_idempotent(self):
        fm = _make_fact_map([{"name": "тётя Маша", "relation_to_subject": "тётя"}])
        fm1, c1 = apply_relation_overrides(fm, OVERRIDES_CFG)
        fm2, c2 = apply_relation_overrides(fm1, OVERRIDES_CFG)
        # Second pass should find same relation already set → no change
        assert fm1["persons"][0]["relation_to_subject"] == fm2["persons"][0]["relation_to_subject"]


class TestEnforcePersonaNotes:
    def test_polina_note_replaced(self):
        book = _make_book([{"label": "Сестра", "value": "Полина", "note": "жила в Старобельске"}])
        patched, log = enforce_persona_notes(book, PERSONA_NOTES_CFG)
        family = patched["chapters"][0]["bio_data"]["family"]
        assert family[0]["note"] == "забрала из детдома"
        assert any(l["action"] == "replaced_note" for l in log)

    def test_tatiana_note_appended(self):
        book = _make_book([{"label": "Дочь", "value": "Татьяна", "note": "1956 года рождения"}])
        patched, log = enforce_persona_notes(book, PERSONA_NOTES_CFG)
        family = patched["chapters"][0]["bio_data"]["family"]
        note = family[0]["note"]
        assert "рассказчик" in note
        assert "1956" in note  # old note preserved

    def test_note_already_present_no_change(self):
        book = _make_book([{"label": "Сестра", "value": "Полина", "note": "забрала из детдома и воспитала"}])
        _, log = enforce_persona_notes(book, PERSONA_NOTES_CFG)
        assert not any(l.get("label_match") == "полина" for l in log)

    def test_split_vnutki(self):
        book = _make_book([{"label": "Внуки", "value": "Никита, Даша", "note": ""}])
        patched, log = enforce_persona_notes(book, PERSONA_NOTES_CFG)
        family = patched["chapters"][0]["bio_data"]["family"]
        labels = [e["label"] for e in family]
        assert "Внук" in labels
        assert "Внучка" in labels
        assert len(family) == 2
        assert any(l["action"] == "split_entry" for l in log)

    def test_idempotent(self):
        book = _make_book([{"label": "Сестра", "value": "Полина", "note": "жила в Старобельске"}])
        patched1, _ = enforce_persona_notes(book, PERSONA_NOTES_CFG)
        patched2, log2 = enforce_persona_notes(patched1, PERSONA_NOTES_CFG)
        assert patched1["chapters"][0]["bio_data"]["family"][0]["note"] == \
               patched2["chapters"][0]["bio_data"]["family"][0]["note"]
