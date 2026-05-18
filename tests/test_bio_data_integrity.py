"""Tests for Task 039: bio_data integrity — validate_bio_data_required_fields,
filter_bio_data_family_by_relation_whitelist, enforce_bio_data_completeness (Марфа case)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pytest
from pipeline_utils import (
    enforce_bio_data_completeness,
    filter_bio_data_family_by_relation_whitelist,
    validate_bio_data_required_fields,
)


def _make_book(family_entries=None, awards=None):
    return {
        "chapters": [
            {
                "id": "ch_01",
                "title": "Паспортичка",
                "content": "Тестовый текст",
                "bio_data": {
                    "family": family_entries if family_entries is not None else [],
                    "awards": awards if awards is not None else [],
                },
            }
        ]
    }


def _make_fact_map(persons=None, timeline=None):
    return {
        "subject": {"name": "Тест", "birth_year": 1920},
        "persons": persons if persons is not None else [],
        "timeline": timeline if timeline is not None else [],
    }


def _person(pid, name, relation, death_year=None, birth_year=None, confidence="high"):
    return {
        "id": pid,
        "name": name,
        "relation_to_subject": relation,
        "death_year": death_year,
        "birth_year": birth_year,
        "confidence": confidence,
    }


# ──────────────────────────────────────────────────────────────────
# enforce_bio_data_completeness (дебаг Марфы)
# ──────────────────────────────────────────────────────────────────

class TestEnforceBioDataCompleteness:
    def test_marfa_low_confidence_added_with_needs_verification(self):
        """Марфа (бабушка, confidence=low) должна добавляться с needs_verification=True."""
        marfa = _person("person_019", "Марфа", "бабушка", confidence="low")
        book = _make_book(family_entries=[])
        fm = _make_fact_map(persons=[marfa])
        result = enforce_bio_data_completeness(book, fm, strict=False)
        family = result["chapters"][0]["bio_data"]["family"]
        names = [e.get("value", "") for e in family]
        assert "Марфа" in names
        entry = next(e for e in family if "Марфа" in e.get("value", ""))
        assert entry.get("needs_verification") is True

    def test_high_confidence_no_needs_verification(self):
        dmitry = _person("person_006", "Дмитрий", "муж", confidence="high")
        book = _make_book(family_entries=[])
        fm = _make_fact_map(persons=[dmitry])
        result = enforce_bio_data_completeness(book, fm, strict=False)
        family = result["chapters"][0]["bio_data"]["family"]
        entry = next(e for e in family if "Дмитрий" in e.get("value", ""))
        assert entry.get("needs_verification") is not True

    def test_already_present_not_duplicated(self):
        tatyana = _person("p1", "Татьяна", "дочь")
        book = _make_book(family_entries=[{"label": "дочь", "value": "Татьяна"}])
        fm = _make_fact_map(persons=[tatyana])
        result = enforce_bio_data_completeness(book, fm, strict=False)
        family = result["chapters"][0]["bio_data"]["family"]
        names = [e.get("value", "") for e in family if "Татьяна" in e.get("value", "")]
        assert len(names) == 1

    def test_neighbour_not_added(self):
        """Тётя Маша (соседка) — не должна попасть в family через enforce."""
        sosedka = _person("p_s", "Тётя Маша", "соседка")
        book = _make_book(family_entries=[])
        fm = _make_fact_map(persons=[sosedka])
        result = enforce_bio_data_completeness(book, fm, strict=False)
        family = result["chapters"][0]["bio_data"]["family"]
        names = [e.get("value", "") for e in family]
        assert "Тётя Маша" not in names


# ──────────────────────────────────────────────────────────────────
# filter_bio_data_family_by_relation_whitelist
# ──────────────────────────────────────────────────────────────────

class TestFilterBioDataFamily:
    def test_neighbour_removed(self):
        family = [
            {"label": "дочь", "value": "Татьяна"},
            {"label": "соседка", "value": "Тётя Маша"},
        ]
        book = _make_book(family_entries=family)
        result, removed = filter_bio_data_family_by_relation_whitelist(book)
        result_family = result["chapters"][0]["bio_data"]["family"]
        assert len(result_family) == 1
        assert result_family[0]["value"] == "Татьяна"
        assert len(removed) == 1
        assert removed[0]["label"] == "соседка"

    def test_all_whitelist_kept(self):
        relations = ["муж", "дочь", "сын", "бабушка", "дедушка", "тётя", "дядя"]
        family = [{"label": r, "value": f"Person_{r}"} for r in relations]
        book = _make_book(family_entries=family)
        result, removed = filter_bio_data_family_by_relation_whitelist(book)
        result_family = result["chapters"][0]["bio_data"]["family"]
        assert len(result_family) == len(relations)
        assert removed == []

    def test_empty_label_kept(self):
        """Запись без label не удаляется (не можем определить relation)."""
        family = [{"value": "Кто-то"}]
        book = _make_book(family_entries=family)
        result, removed = filter_bio_data_family_by_relation_whitelist(book)
        result_family = result["chapters"][0]["bio_data"]["family"]
        assert len(result_family) == 1

    def test_svekrovj_kept(self):
        """Свекровь должна остаться (входит в whitelist)."""
        family = [{"label": "свекровь", "value": "Баба Аня"}]
        book = _make_book(family_entries=family)
        result, removed = filter_bio_data_family_by_relation_whitelist(book)
        result_family = result["chapters"][0]["bio_data"]["family"]
        assert len(result_family) == 1
        assert removed == []

    def test_no_ch01_returns_unchanged(self):
        book = {"chapters": [{"id": "ch_02", "bio_data": {"family": [{"label": "соседка", "value": "X"}]}}]}
        result, removed = filter_bio_data_family_by_relation_whitelist(book)
        assert removed == []

    def test_original_not_mutated(self):
        family = [{"label": "соседка", "value": "Маша"}]
        book = _make_book(family_entries=family)
        filter_bio_data_family_by_relation_whitelist(book)
        assert book["chapters"][0]["bio_data"]["family"][0]["label"] == "соседка"


# ──────────────────────────────────────────────────────────────────
# validate_bio_data_required_fields
# ──────────────────────────────────────────────────────────────────

class TestValidateBioDataRequiredFields:
    def test_death_year_added_to_note(self):
        """Дмитрий (муж, death_year=1978) без (ум. 1978) в family → auto-patch."""
        dmitry = _person("p6", "Дмитрий", "муж", death_year=1978)
        book = _make_book(family_entries=[{"label": "муж", "value": "Дмитрий"}])
        fm = _make_fact_map(persons=[dmitry])
        result, issues = validate_bio_data_required_fields(fm, book)
        family = result["chapters"][0]["bio_data"]["family"]
        entry = next(e for e in family if "Дмитрий" in e.get("value", ""))
        note = entry.get("note", "")
        assert "1978" in note
        assert len(issues) == 1
        assert issues[0]["field"] == "death_year"
        assert issues[0]["action"] == "auto-patched"

    def test_already_has_death_year_no_issue(self):
        dmitry = _person("p6", "Дмитрий", "муж", death_year=1978)
        book = _make_book(family_entries=[
            {"label": "муж", "value": "Дмитрий", "note": "(ум. 1978)"}
        ])
        fm = _make_fact_map(persons=[dmitry])
        result, issues = validate_bio_data_required_fields(fm, book)
        death_issues = [i for i in issues if i.get("field") == "death_year"]
        assert len(death_issues) == 0

    def test_birth_year_added_for_child(self):
        valeriy = _person("p7", "Валерий", "сын", birth_year=1948)
        book = _make_book(family_entries=[{"label": "сын", "value": "Валерий"}])
        fm = _make_fact_map(persons=[valeriy])
        result, issues = validate_bio_data_required_fields(fm, book)
        family = result["chapters"][0]["bio_data"]["family"]
        entry = next(e for e in family if "Валерий" in e.get("value", ""))
        note = entry.get("note", "")
        assert "1948" in note

    def test_birth_year_not_added_for_grandparent(self):
        """Для бабушки birth_year не обязателен (только для сын/дочь/муж/жена)."""
        marfa = _person("p19", "Марфа", "бабушка", birth_year=1895)
        book = _make_book(family_entries=[{"label": "бабушка", "value": "Марфа"}])
        fm = _make_fact_map(persons=[marfa])
        result, issues = validate_bio_data_required_fields(fm, book)
        birth_issues = [i for i in issues if i.get("field") == "birth_year"]
        assert len(birth_issues) == 0

    def test_no_match_in_family_no_issue(self):
        """Персона из fact_map, которой нет в family → не создаёт проблемы."""
        dmitry = _person("p6", "Дмитрий", "муж", death_year=1978)
        book = _make_book(family_entries=[])  # Дмитрий отсутствует
        fm = _make_fact_map(persons=[dmitry])
        _, issues = validate_bio_data_required_fields(fm, book)
        # Нет matching entry → нет и issues
        assert len(issues) == 0

    def test_original_not_mutated(self):
        dmitry = _person("p6", "Дмитрий", "муж", death_year=1978)
        entry = {"label": "муж", "value": "Дмитрий"}
        book = _make_book(family_entries=[entry])
        fm = _make_fact_map(persons=[dmitry])
        validate_bio_data_required_fields(fm, book)
        assert "note" not in entry  # оригинал не мутирован


# ──────────────────────────────────────────────────────────────────
# Integration: полный pipeline 039
# ──────────────────────────────────────────────────────────────────

class TestBioDataIntegrationPipeline:
    """Симулирует полный pipeline: enforce → filter → validate."""

    def test_v56_scenario(self):
        """Симуляция v56: Марфа missing, тётя Маша лишняя, Дмитрий без death_year."""
        persons = [
            _person("p1", "Марфа", "бабушка", confidence="low"),
            _person("p2", "Тётя Маша", "соседка"),
            _person("p3", "Дмитрий", "муж", death_year=1978),
            _person("p4", "Татьяна", "дочь"),
        ]
        # Начальный bio_data: Тётя Маша внутри, Марфа нет, Дмитрий без note
        initial_family = [
            {"label": "соседка", "value": "Тётя Маша"},
            {"label": "муж", "value": "Дмитрий"},
            {"label": "дочь", "value": "Татьяна"},
        ]
        book = _make_book(family_entries=initial_family)
        fm = _make_fact_map(persons=persons)

        # Step 1: enforce (добавляет Марфу)
        book = enforce_bio_data_completeness(book, fm, strict=False)
        family_after_enforce = book["chapters"][0]["bio_data"]["family"]
        assert any("Марфа" in e.get("value", "") for e in family_after_enforce)

        # Step 2: filter (убирает тётю Машу)
        book, removed = filter_bio_data_family_by_relation_whitelist(book)
        family_after_filter = book["chapters"][0]["bio_data"]["family"]
        assert not any("Тётя Маша" in e.get("value", "") for e in family_after_filter)
        assert len(removed) == 1

        # Step 3: validate + auto-patch (добавляет death_year к Дмитрию)
        book, issues = validate_bio_data_required_fields(fm, book)
        family_final = book["chapters"][0]["bio_data"]["family"]
        dmitry_entry = next(e for e in family_final if "Дмитрий" in e.get("value", ""))
        assert "1978" in dmitry_entry.get("note", "")

        # Итог: Марфа есть, тёти Маши нет, у Дмитрия есть (ум. 1978)
        names = [e.get("value", "") for e in family_final]
        assert "Марфа" in names
        assert "Тётя Маша" not in names
