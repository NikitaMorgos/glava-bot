"""Tests for Task 040: normalize_topo_via_gazeteer + normalize_fact_map_topo + normalize_book_topo."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pytest
from pipeline_utils import normalize_topo_via_gazeteer, normalize_fact_map_topo, normalize_book_topo


GAZETEER = {
    "topo_corrections": {
        "Новомергородский": "Новомиргородский",
        "Новомергородского": "Новомиргородского",
        "Керсанов": "Кирсанов",
        "Капашвара": "Капошвара",
        "Капашвары": "Капошвары",
    }
}


class TestNormalizeTopoViaGazeteer:
    def test_basic_replacement(self):
        text = "жил в Новомергородский районе"
        result, reps = normalize_topo_via_gazeteer(text, GAZETEER)
        assert "Новомиргородский" in result
        assert "Новомергородский" not in result
        assert len(reps) == 1
        assert reps[0]["count"] == 1

    def test_genitive_form(self):
        text = "уроженец Новомергородского района"
        result, reps = normalize_topo_via_gazeteer(text, GAZETEER)
        assert "Новомиргородского" in result
        assert "Новомергородского" not in result

    def test_case_preserving_upper(self):
        text = "НОВОМЕРГОРОДСКИЙ РАЙОН"
        # "Новомергородский" в словаре — exact match с заглавной
        # НОВОМЕРГОРОДСКИЙ — all upper → Новомиргородский.upper()
        gazeteer_simple = {"topo_corrections": {"Керсанов": "Кирсанов"}}
        text2 = "КЕРСАНОВ"
        result, _ = normalize_topo_via_gazeteer(text2, gazeteer_simple)
        assert result == "КИРСАНОВ"

    def test_case_preserving_title(self):
        text = "в городе Керсанов строили"
        result, reps = normalize_topo_via_gazeteer(text, GAZETEER)
        assert "Кирсанов" in result

    def test_case_preserving_lower(self):
        """lower-case вариант тоже заменяется (case-insensitive matching + case-preserving replacement)."""
        text = "про керсанов говорили"
        result, reps = normalize_topo_via_gazeteer(text, GAZETEER)
        assert "кирсанов" in result
        assert "керсанов" not in result

    def test_word_boundary(self):
        """Не заменять части слов."""
        text = "НовомергородскийОбъект"  # слитно — не заменять
        result, reps = normalize_topo_via_gazeteer(text, GAZETEER)
        # Word boundary \b: "Новомергородский" + сразу "О" — не является границей слова
        # Поэтому замена НЕ должна произойти
        assert "Новомергородский" in result  # не заменилось

    def test_multiple_occurrences_counted(self):
        text = "Новомергородский район и Новомергородского жители"
        result, reps = normalize_topo_via_gazeteer(text, GAZETEER)
        rep_by_type = {r["wrong"]: r["count"] for r in reps}
        assert rep_by_type.get("Новомергородский", 0) == 1
        assert rep_by_type.get("Новомергородского", 0) == 1

    def test_empty_text(self):
        result, reps = normalize_topo_via_gazeteer("", GAZETEER)
        assert result == ""
        assert reps == []

    def test_no_matches(self):
        text = "Москва, Санкт-Петербург"
        result, reps = normalize_topo_via_gazeteer(text, GAZETEER)
        assert result == text
        assert reps == []

    def test_idempotent(self):
        text = "Новомергородский район"
        r1, _ = normalize_topo_via_gazeteer(text, GAZETEER)
        r2, reps2 = normalize_topo_via_gazeteer(r1, GAZETEER)
        assert r1 == r2
        assert reps2 == []


class TestNormalizeFactMapTopo:
    def test_normalizes_description(self):
        fm = {
            "subject": {"birth_place": "Новомергородский район"},
            "timeline": [
                {"id": "e1", "description": "жил в Керсанов",
                 "source_quote": "жил в Керсанов тоже"}  # source_quote НЕ трогаем
            ],
        }
        result, reps = normalize_fact_map_topo(fm, GAZETEER)
        assert "Новомиргородский" in result["subject"]["birth_place"]
        assert "Кирсанов" in result["timeline"][0]["description"]
        assert "Керсанов" in result["timeline"][0]["source_quote"]  # не изменился

    def test_source_quote_preserved(self):
        fm = {
            "timeline": [
                {"source_quote": "Новомергородский (ASR)", "description": "Новомергородский"}
            ]
        }
        result, _ = normalize_fact_map_topo(fm, GAZETEER)
        assert "Новомергородский" in result["timeline"][0]["source_quote"]
        assert "Новомиргородский" in result["timeline"][0]["description"]

    def test_asr_variants_preserved(self):
        fm = {"persons": [{"name": "Test", "asr_variants": ["Капашвара", "Kapashvara"]}]}
        result, _ = normalize_fact_map_topo(fm, GAZETEER)
        assert "Капашвара" in result["persons"][0]["asr_variants"]

    def test_original_not_mutated(self):
        fm = {"subject": {"birth_place": "Новомергородский"}}
        normalize_fact_map_topo(fm, GAZETEER)
        assert fm["subject"]["birth_place"] == "Новомергородский"


class TestNormalizeBookTopo:
    def test_normalizes_chapter_text(self):
        book = {
            "chapters": [
                {"id": "ch_01", "paragraphs": [{"text": "из Новомергородский района"}]}
            ]
        }
        result, reps = normalize_book_topo(book, GAZETEER)
        assert "Новомиргородский" in result["chapters"][0]["paragraphs"][0]["text"]
        assert len(reps) > 0

    def test_evidence_field_preserved(self):
        book = {
            "callouts": [
                {"evidence": "Новомергородский ASR", "text": "Новомергородский"}
            ]
        }
        result, _ = normalize_book_topo(book, GAZETEER)
        assert "Новомергородский" in result["callouts"][0]["evidence"]
        assert "Новомиргородский" in result["callouts"][0]["text"]

    def test_idempotent_on_book(self):
        book = {"chapters": [{"id": "ch_01", "paragraphs": [{"text": "Новомергородский"}]}]}
        r1, _ = normalize_book_topo(book, GAZETEER)
        r2, reps2 = normalize_book_topo(r1, GAZETEER)
        assert reps2 == []

    def test_kapashvara_normalized(self):
        book = {"chapters": [{"id": "ch_02", "paragraphs": [{"text": "улица Капашвара"}]}]}
        result, reps = normalize_book_topo(book, GAZETEER)
        assert "Капошвара" in result["chapters"][0]["paragraphs"][0]["text"]
        assert "Капашвара" not in result["chapters"][0]["paragraphs"][0]["text"]
