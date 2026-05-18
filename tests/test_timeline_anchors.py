"""Tests for Task 045: validate_timeline_anchors + enforce_timeline_anchors."""
import pytest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline_utils import validate_timeline_anchors, enforce_timeline_anchors


ANCHORS_CFG = {
    "min_periods": 7,
    "anchors": [
        {
            "anchor_id": "childhood",
            "title_keywords": ["детство", "сиротство"],
            "year_range": "1920-1933",
            "required_events": ["голод 1933", "детдом"],
            "merge_forbidden_with": [],
        },
        {
            "anchor_id": "education",
            "title_keywords": ["образование", "учёба", "акушерск"],
            "year_range": "1938-1940",
            "required_events": ["фельдшерско-акушерская школа"],
            "merge_forbidden_with": ["war"],
        },
        {
            "anchor_id": "war",
            "title_keywords": ["война", "военная служба"],
            "year_range": "1941-1945",
            "required_events": ["призыв 1941", "медаль"],
            "merge_forbidden_with": ["education"],
        },
    ],
}


def _make_book_with_timeline(periods):
    return {
        "chapters": [
            {
                "id": "ch_01",
                "content": "",
                "bio_data": {"timeline": periods},
            }
        ]
    }


def _period(title, text=""):
    return {"title": title, "text": text}


class TestValidateTimelineAnchors:
    def test_all_found(self):
        book = _make_book_with_timeline([
            _period("1920-1933. Детство и сиротство"),
            _period("1938-1940. Медицинское образование и учёба"),
            _period("1941-1945. Война и военная служба"),
        ])
        result = validate_timeline_anchors(book, ANCHORS_CFG)
        assert len(result["anchors_found"]) == 3
        assert len(result["anchors_missing"]) == 0
        assert result["merges"] == []

    def test_missing_anchor(self):
        book = _make_book_with_timeline([
            _period("1920-1933. Детство и сиротство"),
            _period("1941-1945. Война и военная служба"),
        ])
        result = validate_timeline_anchors(book, ANCHORS_CFG)
        assert "education" in result["anchors_missing"]

    def test_merge_detected(self):
        book = _make_book_with_timeline([
            _period("1920-1933. Детство и сиротство"),
            _period("1938-1945. Учёба и война", "фельдшерско-акушерская школа, призыв 1941, медаль"),
        ])
        result = validate_timeline_anchors(book, ANCHORS_CFG)
        assert len(result["merges"]) >= 1
        merge = result["merges"][0]
        assert "education" in merge["merged_anchor_ids"]
        assert "war" in merge["merged_anchor_ids"]

    def test_idempotent(self):
        book = _make_book_with_timeline([_period("1920-1933. Детство")])
        r1 = validate_timeline_anchors(book, ANCHORS_CFG)
        r2 = validate_timeline_anchors(book, ANCHORS_CFG)
        assert r1["anchors_missing"] == r2["anchors_missing"]


class TestEnforceTimelineAnchors:
    def test_split_when_both_contents_present(self):
        merged_text = "Фельдшерско-акушерская школа в Кировограде. В 1941 году призыв на фронт, медаль за храбрость."
        book = _make_book_with_timeline([
            _period("1920-1933. Детство и сиротство", "голод 1933, детдом"),
            _period("1938-1945. Учёба и война", merged_text),
        ])
        patched, report = enforce_timeline_anchors(book, ANCHORS_CFG, {})
        timeline = patched["chapters"][0]["bio_data"]["timeline"]
        # Should now have 3 periods (childhood + education + war)
        assert len(timeline) >= 3
        assert any(r["action"] == "split" for r in report["actions"])

    def test_no_split_when_missing_content(self):
        book = _make_book_with_timeline([
            _period("1938-1945. Учёба и война", "только война, медаль, призыв 1941"),
        ])
        patched, report = enforce_timeline_anchors(book, ANCHORS_CFG, {})
        # Should flag skipped but not split (education content not present)
        assert any("insufficient_content" in s.get("reason", "") for s in report["skipped"])

    def test_idempotent_no_merge(self):
        book = _make_book_with_timeline([
            _period("1920-1933. Детство"),
            _period("1938-1940. Учёба"),
            _period("1941-1945. Война"),
        ])
        p1, r1 = enforce_timeline_anchors(book, ANCHORS_CFG, {})
        p2, r2 = enforce_timeline_anchors(p1, ANCHORS_CFG, {})
        assert len(p1["chapters"][0]["bio_data"]["timeline"]) == \
               len(p2["chapters"][0]["bio_data"]["timeline"])
