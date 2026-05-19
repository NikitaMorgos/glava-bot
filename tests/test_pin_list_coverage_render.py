"""
tests/test_pin_list_coverage_render.py

task v65-meta-build_gate1: pin-list coverage breakdown в build_gate1_full_text
— required vs optional — unit tests.
"""
import sys
import os
import importlib.util

import pytest

# ---------------------------------------------------------------------------
# Load build_gate1_full_text as a module (it lives in scripts/)
# ---------------------------------------------------------------------------

def _load_build_gate1():
    spec_path = os.path.join(
        os.path.dirname(__file__), "..", "scripts", "build_gate1_full_text.py"
    )
    spec = importlib.util.spec_from_file_location("build_gate1_full_text", spec_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_book_stub(chapter_content: str = "Короткий контент для главы ch_02.") -> dict:
    return {
        "chapters": [
            {"id": "ch_01", "content": "Паспорт."},
            {"id": "ch_02", "content": chapter_content},
        ],
        "writing_notes": {},
    }


def _make_fact_map_stub() -> dict:
    return {
        "subject": {"name": "Тест", "birth_year": 1920},
        "bio_data": {},
        "persons": [],
    }


def _make_reports(req_cov: dict | None = None, pin_cov: dict | None = None) -> dict:
    return {
        "required_episodes_coverage_json": req_cov,
        "pin_coverage_json": pin_cov,
        "style_checks_json": {},
        "chronology_json": {},
        "discourse_markers_json": {},
        "timeline_anchors_json": {},
        "pin_list_depth_json": {},
    }


# ---------------------------------------------------------------------------
# test_pin_list_coverage_required_breakdown
# — When required episodes are present in the report,
#   the rendered text must include the «Required in narrative» line
#   with covered / total and ✅ or ⚠️ symbols.
# ---------------------------------------------------------------------------

def test_pin_list_coverage_required_breakdown():
    """v65-meta-build_gate1: required section renders with covered/total."""
    mod = _load_build_gate1()

    req_cov = {
        "total_required": 4,
        "covered_count": 3,
        "missing_count": 1,
        "optional_mentioned": 5,
        "optional_total": 10,
        "required_episodes": [
            {"episode_id": "ep_011", "title": "Голод 1933", "found": True},
            {"episode_id": "ep_022", "title": "Продажа дачи", "found": True},
            {"episode_id": "ep_031", "title": "Эвакуация", "found": True},
            {"episode_id": "ep_044", "title": "Возвращение в Харьков", "found": False},
        ],
    }

    book = _make_book_stub()
    fact_map = _make_fact_map_stub()
    reports = _make_reports(req_cov=req_cov)

    md_text = mod.build_gate1_text(book, fact_map, reports)

    # Must include the required section header
    assert "Required in narrative" in md_text, "Section header missing"
    # Must show 3/4
    assert "3 / 4" in md_text, "covered/total ratio (3/4) not rendered"
    # Must show warning symbol since missing_count > 0
    assert "⚠️" in md_text, "Warning symbol missing when there are missing episodes"
    # Must list the missing episode
    assert "ep_044" in md_text, "Missing episode id not shown"
    # Optional line
    assert "Optional episodes" in md_text, "Optional section missing"
    assert "5 / 10" in md_text, "Optional count (5/10) not rendered"


# ---------------------------------------------------------------------------
# test_pin_list_coverage_all_required_covered
# — When all required episodes are covered,
#   renders ✅ and no missing list.
# ---------------------------------------------------------------------------

def test_pin_list_coverage_all_required_covered():
    """v65-meta-build_gate1: all required covered → ✅, no missing line."""
    mod = _load_build_gate1()

    req_cov = {
        "total_required": 3,
        "covered_count": 3,
        "missing_count": 0,
        "optional_mentioned": 8,
        "optional_total": 12,
        "required_episodes": [
            {"episode_id": "ep_011", "title": "Голод 1933", "found": True},
            {"episode_id": "ep_022", "title": "Продажа дачи", "found": True},
            {"episode_id": "ep_031", "title": "Эвакуация", "found": True},
        ],
    }

    book = _make_book_stub()
    fact_map = _make_fact_map_stub()
    reports = _make_reports(req_cov=req_cov)

    md_text = mod.build_gate1_text(book, fact_map, reports)

    assert "Required in narrative" in md_text
    assert "3 / 3" in md_text, "covered/total ratio (3/3) not rendered"
    assert "✅" in md_text, "Checkmark missing when all required covered"
    # No missing line expected
    assert "Missing" not in md_text, "Should not show Missing line when all covered"
