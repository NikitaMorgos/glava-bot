# -*- coding: utf-8 -*-
"""
Тесты массового импорта контент-календаря.

Покрывает:
- parse_text: pipe, TSV (с заголовком и без), JSON, авто-детект формата
- _parse_date / _parse_bool: разные форматы
- resolve_rubric_id / resolve_pformat_id: slug, имя, "platform/format"
- import_items: создание, дедупликация (внутри пачки и с БД), ошибки резолва,
  пропуск ошибок парсинга, ошибки коллбэков

Все обращения к БД — через коллбэки, реальный psycopg2 не нужен.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from smm import calendar_import as ci


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture()
def rubrics():
    return [
        {"id": 1, "slug": "family_stories", "name": "Семейные истории"},
        {"id": 2, "slug": "children", "name": "Дети"},
        {"id": 3, "slug": "reviews", "name": "Отзывы"},
    ]


@pytest.fixture()
def pformats():
    return [
        {"id": 10, "slug": "dzen_long", "platform_name": "Дзен", "format_name": "Лонгрид"},
        {"id": 11, "slug": "vk_short", "platform_name": "VK", "format_name": "Короткий"},
        {"id": 12, "slug": "tg_post", "platform_name": "Telegram", "format_name": "Пост"},
    ]


@pytest.fixture()
def empty_existing():
    return []


@pytest.fixture()
def make_callbacks():
    """Фабрика спай-коллбэков: возвращает (callbacks_dict, captured_state)."""
    def _factory(plan_id_value: int = 100):
        state = {
            "plan_calls": 0,
            "posts": [],
            "extras": [],
            "next_post_id": 500,
        }

        def create_plan() -> int:
            state["plan_calls"] += 1
            return plan_id_value

        def create_post(plan_id, item, rubric_id, pf_id):
            state["next_post_id"] += 1
            post_id = state["next_post_id"]
            state["posts"].append({
                "post_id": post_id,
                "plan_id": plan_id,
                "topic": item.topic,
                "rubric_id": rubric_id,
                "pf_id": pf_id,
            })
            return post_id

        def apply_extras(post_id, item):
            state["extras"].append({
                "post_id": post_id,
                "publish_date": item.publish_date.isoformat(),
                "article_title": item.article_title,
                "image_prompt": item.image_prompt,
                "initiate_dialog": item.initiate_dialog,
            })

        return {
            "create_plan_fn": create_plan,
            "create_post_fn": create_post,
            "apply_extras_fn": apply_extras,
        }, state

    return _factory


# ── Тесты парсера: pipe-формат ───────────────────────────────────────────────


class TestParsePipe:
    def test_basic_4_fields(self):
        text = "2026-06-01 | dzen_long | family_stories | Тема номер один"
        items, errors = ci.parse_text(text)
        assert errors == []
        assert len(items) == 1
        it = items[0]
        assert it.publish_date == date(2026, 6, 1)
        assert it.pf_ref == "dzen_long"
        assert it.rubric_ref == "family_stories"
        assert it.topic == "Тема номер один"
        assert it.article_title == ""
        assert it.image_prompt == ""
        assert it.initiate_dialog is False
        assert it.line_no == 1

    def test_extended_fields(self):
        text = "2026-06-03 | vk_short | children | Тема | Заголовок | promo prompt | true"
        items, errors = ci.parse_text(text)
        assert errors == []
        assert len(items) == 1
        it = items[0]
        assert it.article_title == "Заголовок"
        assert it.image_prompt == "promo prompt"
        assert it.initiate_dialog is True

    def test_multiple_lines_and_comments(self):
        text = """
2026-06-01 | dzen_long | family_stories | Первая тема
# это комментарий
2026-06-02 | dzen_long | family_stories | Вторая тема

2026-06-03 | dzen_long | family_stories | Третья тема
"""
        items, errors = ci.parse_text(text)
        assert errors == []
        assert len(items) == 3
        assert [i.topic for i in items] == ["Первая тема", "Вторая тема", "Третья тема"]

    def test_blank_text_returns_empty(self):
        assert ci.parse_text("") == ([], [])
        assert ci.parse_text("   \n\n  ") == ([], [])

    def test_too_few_fields_is_error(self):
        text = "2026-06-01 | dzen_long | family_stories"
        items, errors = ci.parse_text(text)
        assert items == []
        assert len(errors) == 1
        assert "ожидалось 4+" in errors[0].message
        assert errors[0].status == "error"
        assert errors[0].line_no == 1

    def test_bad_date_is_error(self):
        text = "2026/06/01 invalid | dzen_long | family_stories | Тема"
        items, errors = ci.parse_text(text)
        assert items == []
        assert len(errors) == 1
        assert "некорректная дата" in errors[0].message

    def test_empty_required_field_is_error(self):
        text = "2026-06-01 |  | family_stories | Тема"
        items, errors = ci.parse_text(text)
        assert items == []
        assert len(errors) == 1
        assert "пустое" in errors[0].message

    def test_ddmmyyyy_date_accepted(self):
        text = "01.06.2026 | dzen_long | family_stories | Тема"
        items, errors = ci.parse_text(text)
        assert errors == []
        assert items[0].publish_date == date(2026, 6, 1)

    def test_mixed_good_and_bad_lines(self):
        text = """\
2026-06-01 | dzen_long | family_stories | Тема 1
bad_date | dzen_long | family_stories | Тема 2
2026-06-03 | dzen_long | family_stories | Тема 3"""
        items, errors = ci.parse_text(text)
        assert len(items) == 2
        assert len(errors) == 1
        assert errors[0].line_no == 2


# ── Тесты парсера: TSV ───────────────────────────────────────────────────────


class TestParseTsv:
    def test_basic_tsv(self):
        text = "2026-06-01\tdzen_long\tfamily_stories\tТема одна"
        items, errors = ci.parse_text(text)
        assert errors == []
        assert len(items) == 1
        assert items[0].topic == "Тема одна"

    def test_header_row_skipped(self):
        text = "date\tplatform\trubric\ttopic\n2026-06-01\tdzen_long\tfamily_stories\tТема"
        items, errors = ci.parse_text(text)
        assert errors == []
        assert len(items) == 1
        assert items[0].publish_date == date(2026, 6, 1)

    def test_no_header_works_without_skip(self):
        text = "2026-06-01\tdzen_long\tfamily_stories\tТема A\n2026-06-02\tdzen_long\tfamily_stories\tТема B"
        items, errors = ci.parse_text(text)
        assert errors == []
        assert len(items) == 2


# ── Тесты парсера: JSON ──────────────────────────────────────────────────────


class TestParseJson:
    def test_basic_json(self):
        text = '[{"date": "2026-06-01", "platform_format": "dzen_long", "rubric": "family_stories", "topic": "Тема"}]'
        items, errors = ci.parse_text(text)
        assert errors == []
        assert len(items) == 1
        assert items[0].publish_date == date(2026, 6, 1)

    def test_alias_keys(self):
        text = '[{"publish_date": "2026-06-01", "pf": "dzen_long", "rubric": "family_stories", "topic": "T", "article_title": "Z", "initiate_dialog": true}]'
        items, errors = ci.parse_text(text)
        assert errors == []
        assert items[0].article_title == "Z"
        assert items[0].initiate_dialog is True

    def test_missing_required_field(self):
        text = '[{"date": "2026-06-01", "platform_format": "dzen_long", "rubric": "family_stories"}]'
        items, errors = ci.parse_text(text)
        assert items == []
        assert len(errors) == 1
        assert "topic" in errors[0].message

    def test_invalid_json(self):
        text = '[{"date": "2026-06-01", "platform_format": '
        items, errors = ci.parse_text(text)
        assert items == []
        assert errors and "JSON" in errors[0].message

    def test_not_array(self):
        text = '{"date": "2026-06-01"}'
        items, errors = ci.parse_text(text)
        assert items == []
        assert errors and "массив" in errors[0].message


# ── Резолв ───────────────────────────────────────────────────────────────────


class TestResolve:
    def test_rubric_by_slug(self, rubrics):
        assert ci.resolve_rubric_id("family_stories", rubrics) == 1

    def test_rubric_by_name(self, rubrics):
        assert ci.resolve_rubric_id("Семейные истории", rubrics) == 1

    def test_rubric_case_insensitive(self, rubrics):
        assert ci.resolve_rubric_id("FAMILY_STORIES", rubrics) == 1

    def test_rubric_not_found(self, rubrics):
        assert ci.resolve_rubric_id("missing", rubrics) is None

    def test_pformat_by_slug(self, pformats):
        assert ci.resolve_pformat_id("dzen_long", pformats) == 10

    def test_pformat_by_platform_slash_format(self, pformats):
        assert ci.resolve_pformat_id("Дзен/Лонгрид", pformats) == 10
        assert ci.resolve_pformat_id("дзен/лонгрид", pformats) == 10

    def test_pformat_by_platform_only(self, pformats):
        assert ci.resolve_pformat_id("Telegram", pformats) == 12

    def test_pformat_not_found(self, pformats):
        assert ci.resolve_pformat_id("instagram/story", pformats) is None


# ── Импорт ───────────────────────────────────────────────────────────────────


class TestImportItems:
    def test_basic_import(self, rubrics, pformats, empty_existing, make_callbacks):
        text = "2026-06-01 | dzen_long | family_stories | Тема 1"
        items, errs = ci.parse_text(text)
        cbs, state = make_callbacks()
        report = ci.import_items(
            items, errs, rubrics=rubrics, pformats=pformats,
            existing_posts=empty_existing, **cbs,
        )
        assert report.created == 1
        assert report.duplicate == 0
        assert report.error == 0
        assert state["plan_calls"] == 1
        assert state["posts"][0]["topic"] == "Тема 1"
        assert state["posts"][0]["rubric_id"] == 1
        assert state["posts"][0]["pf_id"] == 10

    def test_plan_created_once_for_batch(self, rubrics, pformats, empty_existing, make_callbacks):
        text = """\
2026-06-01 | dzen_long | family_stories | A
2026-06-02 | dzen_long | family_stories | B
2026-06-03 | dzen_long | family_stories | C"""
        items, errs = ci.parse_text(text)
        cbs, state = make_callbacks()
        report = ci.import_items(
            items, errs, rubrics=rubrics, pformats=pformats,
            existing_posts=empty_existing, **cbs,
        )
        assert report.created == 3
        assert state["plan_calls"] == 1

    def test_intra_batch_duplicate_skipped(self, rubrics, pformats, empty_existing, make_callbacks):
        text = """\
2026-06-01 | dzen_long | family_stories | Тема одинаковая
2026-06-02 | dzen_long | family_stories | Другая тема
2026-06-01 | dzen_long | family_stories | Тема одинаковая"""
        items, errs = ci.parse_text(text)
        cbs, state = make_callbacks()
        report = ci.import_items(
            items, errs, rubrics=rubrics, pformats=pformats,
            existing_posts=empty_existing, **cbs,
        )
        assert report.created == 2
        assert report.duplicate == 1
        # дубль — это 3-я запись
        dup_rows = [r for r in report.rows if r.status == "duplicate"]
        assert len(dup_rows) == 1
        assert dup_rows[0].line_no == 3

    def test_existing_in_db_treated_as_duplicate(self, rubrics, pformats, make_callbacks):
        existing = [{
            "publish_date": date(2026, 6, 1),
            "platform_format_id": 10,
            "rubric_id": 1,
            "topic": "Уже была такая тема",
        }]
        text = "2026-06-01 | dzen_long | family_stories | Уже была такая тема"
        items, errs = ci.parse_text(text)
        cbs, state = make_callbacks()
        report = ci.import_items(
            items, errs, rubrics=rubrics, pformats=pformats,
            existing_posts=existing, **cbs,
        )
        assert report.created == 0
        assert report.duplicate == 1
        assert state["plan_calls"] == 0
        assert state["posts"] == []

    def test_duplicate_topic_case_insensitive(self, rubrics, pformats, make_callbacks):
        existing = [{
            "publish_date": date(2026, 6, 1),
            "platform_format_id": 10,
            "rubric_id": 1,
            "topic": "Семейные традиции",
        }]
        text = "2026-06-01 | dzen_long | family_stories | СЕМЕЙНЫЕ ТРАДИЦИИ"
        items, errs = ci.parse_text(text)
        cbs, _ = make_callbacks()
        report = ci.import_items(
            items, errs, rubrics=rubrics, pformats=pformats,
            existing_posts=existing, **cbs,
        )
        assert report.duplicate == 1
        assert report.created == 0

    def test_unknown_rubric_is_error(self, rubrics, pformats, empty_existing, make_callbacks):
        text = "2026-06-01 | dzen_long | unknown_rubric | Тема"
        items, errs = ci.parse_text(text)
        cbs, state = make_callbacks()
        report = ci.import_items(
            items, errs, rubrics=rubrics, pformats=pformats,
            existing_posts=empty_existing, **cbs,
        )
        assert report.error == 1
        assert report.created == 0
        assert state["plan_calls"] == 0
        assert "не найдена рубрика" in report.rows[0].message

    def test_unknown_pformat_is_error(self, rubrics, pformats, empty_existing, make_callbacks):
        text = "2026-06-01 | instagram_story | family_stories | Тема"
        items, errs = ci.parse_text(text)
        cbs, _ = make_callbacks()
        report = ci.import_items(
            items, errs, rubrics=rubrics, pformats=pformats,
            existing_posts=empty_existing, **cbs,
        )
        assert report.error == 1
        assert "не найден формат площадки" in report.rows[0].message

    def test_parse_errors_are_in_report(self, rubrics, pformats, empty_existing, make_callbacks):
        text = """\
2026-06-01 | dzen_long | family_stories | OK
broken_line_only_one_field
2026-06-02 | dzen_long | family_stories | OK2"""
        items, errs = ci.parse_text(text)
        cbs, _ = make_callbacks()
        report = ci.import_items(
            items, errs, rubrics=rubrics, pformats=pformats,
            existing_posts=empty_existing, **cbs,
        )
        assert report.created == 2
        assert report.error == 1

    def test_extras_applied(self, rubrics, pformats, empty_existing, make_callbacks):
        text = "2026-06-01 | dzen_long | family_stories | Тема | Заголовок | картинка-промпт | true"
        items, errs = ci.parse_text(text)
        cbs, state = make_callbacks()
        ci.import_items(
            items, errs, rubrics=rubrics, pformats=pformats,
            existing_posts=empty_existing, **cbs,
        )
        assert len(state["extras"]) == 1
        x = state["extras"][0]
        assert x["publish_date"] == "2026-06-01"
        assert x["article_title"] == "Заголовок"
        assert x["image_prompt"] == "картинка-промпт"
        assert x["initiate_dialog"] is True

    def test_create_post_callback_exception_recorded(self, rubrics, pformats, empty_existing):
        text = """\
2026-06-01 | dzen_long | family_stories | A
2026-06-02 | dzen_long | family_stories | B"""
        items, errs = ci.parse_text(text)
        plan_calls = [0]
        created = []

        def create_plan():
            plan_calls[0] += 1
            return 99

        def create_post(plan_id, item, rubric_id, pf_id):
            if "B" in item.topic:
                raise RuntimeError("simulated DB failure")
            created.append(item.topic)
            return 1

        def apply_extras(post_id, item):
            pass

        report = ci.import_items(
            items, errs, rubrics=rubrics, pformats=pformats,
            existing_posts=empty_existing,
            create_plan_fn=create_plan,
            create_post_fn=create_post,
            apply_extras_fn=apply_extras,
        )
        assert report.created == 1
        assert report.error == 1
        assert plan_calls[0] == 1
        assert "simulated DB failure" in [r.message for r in report.rows if r.status == "error"][0]

    def test_to_dict_serialization(self, rubrics, pformats, empty_existing, make_callbacks):
        text = "2026-06-01 | dzen_long | family_stories | Тема"
        items, errs = ci.parse_text(text)
        cbs, _ = make_callbacks()
        report = ci.import_items(
            items, errs, rubrics=rubrics, pformats=pformats,
            existing_posts=empty_existing, **cbs,
        )
        d = report.to_dict()
        assert d["created"] == 1
        assert d["total"] == 1
        assert isinstance(d["rows"], list)
        assert d["rows"][0]["status"] == "created"


# ── Граничные кейсы ──────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_empty_text_returns_empty_report(self, rubrics, pformats, empty_existing, make_callbacks):
        items, errs = ci.parse_text("")
        cbs, state = make_callbacks()
        report = ci.import_items(
            items, errs, rubrics=rubrics, pformats=pformats,
            existing_posts=empty_existing, **cbs,
        )
        assert report.total == 0
        assert state["plan_calls"] == 0

    def test_only_comments(self, rubrics, pformats, empty_existing, make_callbacks):
        items, errs = ci.parse_text("# header\n# nothing here")
        cbs, _ = make_callbacks()
        report = ci.import_items(
            items, errs, rubrics=rubrics, pformats=pformats,
            existing_posts=empty_existing, **cbs,
        )
        assert report.total == 0

    def test_dedup_does_not_create_plan(self, rubrics, pformats, make_callbacks):
        existing = [{
            "publish_date": date(2026, 6, 1),
            "platform_format_id": 10,
            "rubric_id": 1,
            "topic": "Дубль",
        }]
        text = "2026-06-01 | dzen_long | family_stories | Дубль"
        items, errs = ci.parse_text(text)
        cbs, state = make_callbacks()
        ci.import_items(
            items, errs, rubrics=rubrics, pformats=pformats,
            existing_posts=existing, **cbs,
        )
        assert state["plan_calls"] == 0
