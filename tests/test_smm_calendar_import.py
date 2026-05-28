# -*- coding: utf-8 -*-
"""
Тесты для smm/calendar_import.py (v2 — новая схема smm_content_calendar).

Запуск: python -m pytest tests/test_smm_calendar_import.py -v
"""
import pytest
from datetime import date
from smm.calendar_import import (
    parse_text,
    run_import,
    ParsedItem,
    ImportRow,
    ImportReport,
)


# ── Хелперы ────────────────────────────────────────────────────────────────────

def _make_platform(pid=1, name="Дзен"):
    return {"id": pid, "name": name}

def _make_rubric(rid=10, name="советы"):
    return {"id": rid, "name": name}

def _noop_add(**kwargs) -> int:
    return 0


# ── parse_text: PIPE ───────────────────────────────────────────────────────────

class TestParsePipe:
    def test_basic_5_fields(self):
        rows = parse_text("2026-05-29 | Дзен | статья | советы | Как сохранить воспоминания")
        assert len(rows) == 1
        r = rows[0]
        assert r.status == ""
        assert r.item.publish_date == date(2026, 5, 29)
        assert r.item.platform_name == "Дзен"
        assert r.item.material_type == "статья"
        assert r.item.rubric_name == "советы"
        assert r.item.title == "Как сохранить воспоминания"
        assert r.item.extra_info == ""

    def test_6_fields_with_extra_info(self):
        rows = parse_text("2026-06-01 | Дзен | статья | практика | Тема | Подробности здесь")
        assert rows[0].item.extra_info == "Подробности здесь"

    def test_multiple_lines(self):
        text = (
            "2026-05-29 | Дзен | статья | советы | Тема 1\n"
            "2026-05-30 | Дзен | пост   | история | Тема 2\n"
        )
        rows = parse_text(text)
        assert len(rows) == 2
        assert all(r.status == "" for r in rows)

    def test_skips_blank_lines(self):
        text = "2026-05-29 | Дзен | статья | советы | Тема 1\n\n\n2026-05-30 | Дзен | пост | история | Тема 2"
        rows = parse_text(text)
        assert len(rows) == 2

    def test_skips_comment_lines(self):
        text = "# это комментарий\n2026-05-29 | Дзен | статья | советы | Тема 1"
        rows = parse_text(text)
        assert len(rows) == 1

    def test_error_on_4_fields(self):
        rows = parse_text("2026-05-29 | Дзен | статья | советы")
        assert rows[0].status == "error"
        assert "5" in rows[0].message

    def test_error_on_bad_date(self):
        rows = parse_text("не-дата | Дзен | статья | советы | Тема")
        assert rows[0].status == "error"
        assert "дату" in rows[0].message.lower()

    def test_error_empty_platform(self):
        rows = parse_text("2026-05-29 |  | статья | советы | Тема")
        assert rows[0].status == "error"

    def test_error_empty_title(self):
        rows = parse_text("2026-05-29 | Дзен | статья | советы |  ")
        assert rows[0].status == "error"

    def test_date_formats(self):
        for date_str in ("2026-05-29", "29.05.2026", "29/05/2026"):
            rows = parse_text(f"{date_str} | Дзен | статья | советы | Тема")
            assert rows[0].item.publish_date == date(2026, 5, 29), f"Ошибка для {date_str}"

    def test_empty_rubric_allowed(self):
        rows = parse_text("2026-05-29 | Дзен | статья |  | Тема без рубрики")
        assert rows[0].status == ""
        assert rows[0].item.rubric_name == ""

    def test_empty_text_returns_empty(self):
        assert parse_text("") == []
        assert parse_text("   ") == []


# ── parse_text: JSON ───────────────────────────────────────────────────────────

class TestParseJSON:
    def test_basic_json(self):
        text = '[{"date": "2026-05-29", "platform": "Дзен", "material_type": "статья", "rubric": "советы", "title": "Тема"}]'
        rows = parse_text(text)
        assert len(rows) == 1
        assert rows[0].status == ""
        assert rows[0].item.title == "Тема"

    def test_json_alias_publish_date(self):
        text = '[{"publish_date": "2026-05-29", "platform": "Дзен", "material_type": "пост", "rubric": "", "title": "Тема"}]'
        rows = parse_text(text)
        assert rows[0].item.publish_date == date(2026, 5, 29)

    def test_json_alias_topic(self):
        text = '[{"date": "2026-06-01", "platform": "ВК", "material_type": "пост", "rubric": "", "topic": "Тема 2"}]'
        rows = parse_text(text)
        assert rows[0].item.title == "Тема 2"

    def test_json_error_not_list(self):
        # JSON-массив, но из примитивов — не объекты
        rows = parse_text('[1, 2, 3]')
        assert rows[0].status == "error"

    def test_json_error_bad_date(self):
        rows = parse_text('[{"date": "abc", "platform": "Дзен", "material_type": "", "rubric": "", "title": "T"}]')
        assert rows[0].status == "error"

    def test_json_error_missing_platform(self):
        rows = parse_text('[{"date": "2026-05-29", "material_type": "", "rubric": "", "title": "T"}]')
        assert rows[0].status == "error"

    def test_json_error_missing_title(self):
        rows = parse_text('[{"date": "2026-05-29", "platform": "Дзен", "material_type": "", "rubric": ""}]')
        assert rows[0].status == "error"


# ── parse_text: TSV ────────────────────────────────────────────────────────────

class TestParseTSV:
    def test_tsv_with_header(self):
        text = "Дата\tПлощадка\tТип\tРубрика\tНазвание\n2026-05-29\tДзен\tстатья\tсоветы\tТема TSV"
        rows = parse_text(text)
        assert len(rows) == 1
        assert rows[0].item.title == "Тема TSV"
        assert rows[0].item.platform_name == "Дзен"

    def test_tsv_without_header(self):
        text = "2026-05-29\tДзен\tстатья\tсоветы\tТема TSV 2"
        rows = parse_text(text)
        assert len(rows) == 1
        assert rows[0].item.publish_date == date(2026, 5, 29)


# ── run_import ─────────────────────────────────────────────────────────────────

class TestRunImport:
    def _make_deps(self, platform=None, rubric=None, existing=None, added=None):
        if added is None:
            added = []

        def get_platform(name):
            return platform if platform else None

        def get_rubric(name):
            return rubric if rubric else None

        def get_sigs():
            return existing or set()

        def add_entry(**kwargs):
            added.append(kwargs)
            return len(added)

        return get_platform, get_rubric, get_sigs, add_entry

    def test_successful_import(self):
        added = []
        gp, gr, gs, ae = self._make_deps(
            platform=_make_platform(), rubric=_make_rubric(), added=added
        )
        report = run_import(
            "2026-05-29 | Дзен | статья | советы | Тема",
            get_platform_by_name=gp, get_rubric_by_name=gr,
            get_existing_signatures=gs, add_entry=ae,
        )
        assert report.created == 1
        assert report.errors == 0
        assert len(added) == 1
        assert added[0]["title"] == "Тема"
        assert added[0]["platform_id"] == 1
        assert added[0]["rubric_id"] == 10

    def test_platform_not_found(self):
        gp, gr, gs, ae = self._make_deps(platform=None)
        report = run_import(
            "2026-05-29 | НеизвестнаяПлощадка | статья | советы | Тема",
            get_platform_by_name=gp, get_rubric_by_name=gr,
            get_existing_signatures=gs, add_entry=ae,
        )
        assert report.errors == 1
        assert report.created == 0
        assert "не найдена" in report.rows[0].message.lower()

    def test_rubric_not_found(self):
        gp, gr, gs, ae = self._make_deps(platform=_make_platform(), rubric=None)
        report = run_import(
            "2026-05-29 | Дзен | статья | неизвестная рубрика | Тема",
            get_platform_by_name=gp, get_rubric_by_name=gr,
            get_existing_signatures=gs, add_entry=ae,
        )
        assert report.errors == 1

    def test_empty_rubric_no_rubric_id(self):
        added = []
        gp, gr, gs, ae = self._make_deps(platform=_make_platform(), added=added)
        report = run_import(
            "2026-05-29 | Дзен | статья |  | Тема без рубрики",
            get_platform_by_name=gp, get_rubric_by_name=gr,
            get_existing_signatures=gs, add_entry=ae,
        )
        assert report.created == 1
        assert added[0]["rubric_id"] is None

    def test_dedup_existing(self):
        existing = {(1, "2026-05-29", "тема")}
        gp, gr, gs, ae = self._make_deps(
            platform=_make_platform(), rubric=_make_rubric(), existing=existing
        )
        report = run_import(
            "2026-05-29 | Дзен | статья | советы | Тема",
            get_platform_by_name=gp, get_rubric_by_name=gr,
            get_existing_signatures=gs, add_entry=ae,
        )
        assert report.duplicates == 1
        assert report.created == 0

    def test_dedup_within_batch(self):
        added = []
        gp, gr, gs, ae = self._make_deps(
            platform=_make_platform(), rubric=_make_rubric(), added=added
        )
        text = (
            "2026-05-29 | Дзен | статья | советы | Тема\n"
            "2026-05-29 | Дзен | статья | советы | Тема\n"
        )
        report = run_import(
            text,
            get_platform_by_name=gp, get_rubric_by_name=gr,
            get_existing_signatures=gs, add_entry=ae,
        )
        assert report.created == 1
        assert report.duplicates == 1

    def test_dedup_case_insensitive_title(self):
        existing = {(1, "2026-05-29", "тема")}
        gp, gr, gs, ae = self._make_deps(
            platform=_make_platform(), rubric=_make_rubric(), existing=existing
        )
        report = run_import(
            "2026-05-29 | Дзен | статья | советы | ТЕМА",
            get_platform_by_name=gp, get_rubric_by_name=gr,
            get_existing_signatures=gs, add_entry=ae,
        )
        assert report.duplicates == 1

    def test_mixed_results(self):
        added = []
        gp, gr, gs, ae = self._make_deps(
            platform=_make_platform(), rubric=_make_rubric(), added=added
        )
        text = (
            "2026-05-29 | Дзен | статья | советы | Тема 1\n"
            "не-дата | Дзен | статья | советы | Тема 2\n"
            "2026-05-31 | Дзен | статья | советы | Тема 3\n"
        )
        report = run_import(
            text,
            get_platform_by_name=gp, get_rubric_by_name=gr,
            get_existing_signatures=gs, add_entry=ae,
        )
        assert report.created == 2
        assert report.errors == 1

    def test_empty_text_empty_report(self):
        gp, gr, gs, ae = self._make_deps(platform=_make_platform())
        report = run_import(
            "",
            get_platform_by_name=gp, get_rubric_by_name=gr,
            get_existing_signatures=gs, add_entry=ae,
        )
        assert report.created == 0
        assert report.errors == 0

    def test_report_to_dict(self):
        added = []
        gp, gr, gs, ae = self._make_deps(
            platform=_make_platform(), rubric=_make_rubric(), added=added
        )
        report = run_import(
            "2026-05-29 | Дзен | статья | советы | Тема",
            get_platform_by_name=gp, get_rubric_by_name=gr,
            get_existing_signatures=gs, add_entry=ae,
        )
        d = report.to_dict()
        assert d["created"] == 1
        assert d["duplicates"] == 0
        assert d["errors"] == 0
        assert len(d["rows"]) == 1
        assert d["rows"][0]["title"] == "Тема"
