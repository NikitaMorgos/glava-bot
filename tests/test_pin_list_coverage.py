"""Tests for Task 041: parse_pin_list_from_markdown, validate_pin_list_coverage, diff_episodes_between_versions."""
import pytest
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline_utils import (
    parse_pin_list_from_markdown,
    validate_pin_list_coverage,
    diff_episodes_between_versions,
)


# Section headers must match exactly what the parser looks for
SAMPLE_MD = """# Known Episodes

## Хронологические эпизоды

| # | episode_id | Эпизод | Описание | Глава | Маркеры |
|---|-----------|--------|----------|-------|---------|
| 1 | E01 | Детский дом в 1929 году | Попала в детдом | ch_02 | детдом, 1929, сирота |
| 2 | E02 | Фельдшерская школа в Кировограде | Учёба | ch_03 | фельдшерская, Кировоград, 1938 |

## Бытовые эпизоды

| # | byt_id | Эпизод | Маркеры |
|---|--------|--------|---------|
| B1 | B01 | Яблочный пирог с Полиной | яблочный, пирог, Полина |
| B2 | B02 | Огород в Харькове | огород, Харьков |
"""


def _write_md(content: str) -> str:
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8")
    tmp.write(content)
    tmp.flush()
    return tmp.name


def _book_with_content(text: str) -> dict:
    return {"chapters": [{"id": "ch_01", "content": text}]}


def _pin_with_markers(*episodes):
    """Helper to create pin_list in the implementation's expected format (episode_id + markers)."""
    return {
        "episodes": [
            {"episode_id": ep.get("id", str(i + 1)), "title": ep["title"], "markers": ep["markers"]}
            for i, ep in enumerate(episodes)
        ],
        "bytovye": [],
    }


class TestParsePinListFromMarkdown:
    def test_returns_dict_with_expected_keys(self):
        path = _write_md(SAMPLE_MD)
        pin = parse_pin_list_from_markdown(path)
        assert "episodes" in pin
        assert "bytovye" in pin

    def test_parse_episodes_count(self):
        path = _write_md(SAMPLE_MD)
        pin = parse_pin_list_from_markdown(path)
        # Parser expects ≥4 cells per episode row; with 6-column table it should parse correctly
        assert len(pin["episodes"]) == 2

    def test_parse_bytovye_count(self):
        path = _write_md(SAMPLE_MD)
        pin = parse_pin_list_from_markdown(path)
        assert len(pin["bytovye"]) == 2

    def test_episode_has_markers(self):
        path = _write_md(SAMPLE_MD)
        pin = parse_pin_list_from_markdown(path)
        assert len(pin["episodes"]) > 0
        ep = pin["episodes"][0]
        assert "markers" in ep
        assert isinstance(ep["markers"], list)

    def test_empty_file(self):
        path = _write_md("# Empty\n")
        pin = parse_pin_list_from_markdown(path)
        assert pin["episodes"] == []
        assert pin["bytovye"] == []

    def test_missing_file(self):
        pin = parse_pin_list_from_markdown("/nonexistent/path.md")
        assert pin["episodes"] == []

    def test_real_karakulina_pin_list(self):
        path = ROOT / "collab" / "context" / "known_episodes_karakulina.md"
        if not path.exists():
            pytest.skip("known_episodes_karakulina.md not found")
        pin = parse_pin_list_from_markdown(str(path))
        assert len(pin["episodes"]) + len(pin["bytovye"]) >= 5


class TestValidatePinListCoverage:
    def test_all_covered(self):
        pin = _pin_with_markers(
            {"title": "Детский дом", "markers": ["детдом", "1929"]},
            {"title": "Фельдшерская школа", "markers": ["фельдшерская", "Кировоград"]},
        )
        # Use nominative forms matching the markers exactly (Russian declension)
        book = _book_with_content("В 1929 году она попала в детдом. Поступила в фельдшерская школа в Кировоград.")
        result = validate_pin_list_coverage(book, pin)
        summary = result["summary"]
        assert summary["full"] == 2
        assert summary["skipped"] == 0

    def test_missing_episode(self):
        pin = _pin_with_markers({"title": "Призыв на фронт", "markers": ["фронт", "1941", "призыв"]})
        book = _book_with_content("Она работала акушеркой после войны.")
        result = validate_pin_list_coverage(book, pin)
        assert result["summary"]["skipped"] == 1

    def test_partial_coverage(self):
        pin = _pin_with_markers(
            {"title": "Детдом в 1929", "markers": ["детдом", "1929", "сирота"]}
        )
        # Only "1929" present → 1/3 = below 60% threshold → partial
        book = _book_with_content("В 1929 году начался голод, она осталась одна.")
        result = validate_pin_list_coverage(book, pin)
        summary = result["summary"]
        assert summary["partial"] >= 1 or summary["skipped"] >= 1

    def test_result_has_episodes_and_summary(self):
        pin = _pin_with_markers({"title": "Тест", "markers": ["слово"]})
        book = _book_with_content("слово в тексте")
        result = validate_pin_list_coverage(book, pin)
        assert "episodes" in result
        assert "summary" in result
        for key in ("full", "partial", "skipped", "total"):
            assert key in result["summary"]

    def test_empty_pin_list(self):
        book = _book_with_content("Любой текст")
        result = validate_pin_list_coverage(book, {"episodes": [], "bytovye": []})
        assert result["summary"]["total"] == 0


class TestDiffEpisodesBetweenVersions:
    def test_improvement_detected(self):
        pin = _pin_with_markers(
            {"title": "Детдом", "markers": ["детдом"]},
            {"title": "Фельдшерская", "markers": ["фельдшерская"]},
        )
        book_new = _book_with_content("В 1929 году детдом. Потом фельдшерская школа.")
        book_old = _book_with_content("Она работала врачом.")
        result = diff_episodes_between_versions(book_new, book_old, pin)
        assert result["improvement_count"] >= 1
        assert result["regression_count"] == 0

    def test_regression_detected(self):
        pin = _pin_with_markers({"title": "Детдом", "markers": ["детдом"]})
        book_new = _book_with_content("Она жила и работала.")
        book_old = _book_with_content("В 1929 году детдом.")
        result = diff_episodes_between_versions(book_new, book_old, pin)
        assert result["regression_count"] >= 1
        assert result["improvement_count"] == 0

    def test_no_change(self):
        pin = _pin_with_markers({"title": "Детдом", "markers": ["детдом"]})
        text = "В 1929 году детдом."
        book = _book_with_content(text)
        result = diff_episodes_between_versions(book, book, pin)
        assert result["regression_count"] == 0
        assert result["improvement_count"] == 0

    def test_result_has_required_keys(self):
        pin = _pin_with_markers({"title": "Тест", "markers": ["слово"]})
        book = _book_with_content("слово")
        result = diff_episodes_between_versions(book, book, pin)
        for key in ("regressions", "improvements", "regression_count", "improvement_count", "verdict"):
            assert key in result
