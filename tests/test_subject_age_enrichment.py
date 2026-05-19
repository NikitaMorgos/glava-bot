"""Tests for Task 042: enrich_timeline_with_subject_age (pipeline_utils.py)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pytest
from pipeline_utils import enrich_timeline_with_subject_age


def _make_fact_map(birth_year, events):
    return {
        "subject": {"name": "Test", "birth_year": birth_year},
        "timeline": events,
        "persons": [],
    }


def _event(event_id, year, precision="exact", month=None):
    return {
        "id": event_id,
        "date": {"year": year, "month": month, "precision": precision},
        "title": f"Event {event_id}",
    }


class TestBasicEnrichment:
    def test_exact_year(self):
        fm = _make_fact_map(1920, [_event("e1", 1962)])
        result = enrich_timeline_with_subject_age(fm)
        assert result["timeline"][0]["subject_age"] == 42

    def test_multiple_events(self):
        events = [_event("e1", 1920), _event("e2", 1933), _event("e3", 1962)]
        fm = _make_fact_map(1920, events)
        result = enrich_timeline_with_subject_age(fm)
        ages = [e["subject_age"] for e in result["timeline"]]
        assert ages == [0, 13, 42]

    def test_decade_precision_mid_decade(self):
        fm = _make_fact_map(1920, [_event("e1", 1960, precision="decade")])
        result = enrich_timeline_with_subject_age(fm)
        assert result["timeline"][0]["subject_age"] == 45  # (1960+5) - 1920

    def test_decade_1970(self):
        fm = _make_fact_map(1920, [_event("e1", 1970, precision="decade")])
        result = enrich_timeline_with_subject_age(fm)
        assert result["timeline"][0]["subject_age"] == 55  # (1970+5) - 1920


class TestEdgeCases:
    def test_missing_year_skipped(self):
        event = {"id": "e1", "date": {"year": None, "precision": "unknown"}, "title": "No year"}
        fm = _make_fact_map(1920, [event])
        result = enrich_timeline_with_subject_age(fm)
        assert "subject_age" not in result["timeline"][0]

    def test_missing_date_field_skipped(self):
        event = {"id": "e1", "title": "No date at all"}
        fm = _make_fact_map(1920, [event])
        result = enrich_timeline_with_subject_age(fm)
        assert "subject_age" not in result["timeline"][0]

    def test_no_birth_year_returns_unchanged(self):
        fm = {"subject": {"name": "Test"}, "timeline": [_event("e1", 1962)], "persons": []}
        result = enrich_timeline_with_subject_age(fm)
        assert "subject_age" not in result["timeline"][0]

    def test_birth_year_none_returns_unchanged(self):
        fm = _make_fact_map(None, [_event("e1", 1962)])
        result = enrich_timeline_with_subject_age(fm)
        assert "subject_age" not in result["timeline"][0]

    def test_empty_timeline(self):
        fm = _make_fact_map(1920, [])
        result = enrich_timeline_with_subject_age(fm)
        assert result["timeline"] == []


class TestIdempotency:
    def test_already_enriched_not_overwritten(self):
        event = {"id": "e1", "date": {"year": 1962, "precision": "exact"}, "subject_age": 99}
        fm = _make_fact_map(1920, [event])
        result = enrich_timeline_with_subject_age(fm)
        assert result["timeline"][0]["subject_age"] == 99  # preserved

    def test_double_call_same_result(self):
        fm = _make_fact_map(1920, [_event("e1", 1962)])
        r1 = enrich_timeline_with_subject_age(fm)
        r2 = enrich_timeline_with_subject_age(r1)
        assert r1["timeline"][0]["subject_age"] == r2["timeline"][0]["subject_age"]


class TestOriginalNotMutated:
    def test_original_fact_map_unchanged(self):
        events = [_event("e1", 1962)]
        fm = _make_fact_map(1920, events)
        enrich_timeline_with_subject_age(fm)
        assert "subject_age" not in fm["timeline"][0]


class TestIntegrationV56:
    """Smoke test на реальном формате v56 fact_map (синтетически)."""

    def test_karakulina_birth_1920(self):
        events = [
            _event("event_001", 1920, precision="exact"),
            _event("event_002", 1933, precision="approximate"),
            _event("event_007", 1962, precision="approximate"),
        ]
        fm = _make_fact_map(1920, events)
        result = enrich_timeline_with_subject_age(fm)
        assert result["timeline"][0]["subject_age"] == 0
        assert result["timeline"][1]["subject_age"] == 13
        assert result["timeline"][2]["subject_age"] == 42
