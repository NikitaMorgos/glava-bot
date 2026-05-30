# -*- coding: utf-8 -*-
"""
Тесты для smm.scout.run_calendar_scout.

Запуск: python -m pytest tests/test_calendar_scout.py -v
"""
import pytest
from datetime import date, timedelta
from unittest.mock import patch, MagicMock


# ── Фикстуры ───────────────────────────────────────────────────────────────────

def _entry(
    eid=1,
    title="Тема статьи",
    publish_date=None,
    platform_name="Яндекс Дзен",
    rubric_id=10,
    has_post=False,
    content_ready=False,
    extra_info="",
):
    return {
        "id": eid,
        "title": title,
        "publish_date": publish_date or date.today() + timedelta(days=1),
        "platform_name": platform_name,
        "rubric_id": rubric_id,
        "has_post": has_post,
        "content_ready": content_ready,
        "extra_info": extra_info,
    }


# ── Базовые сценарии ───────────────────────────────────────────────────────────

class TestRunCalendarScout:

    def _run(self, entries, created_ids=None):
        """Запускает run_calendar_scout с замоканными DB-функциями."""
        if created_ids is None:
            created_ids = []

        # Патчим по фактическому пути — функции импортируются внутри run_calendar_scout
        with patch("smm.db_smm.get_calendar_entries_with_post_status", return_value=entries), \
             patch("smm.db_smm.create_post", side_effect=lambda **kw: created_ids.append(kw) or len(created_ids)):
            from smm.scout import run_calendar_scout
            return run_calendar_scout(days_ahead=30), created_ids

    def test_creates_post_for_new_entry(self):
        result, created = self._run([_entry()])
        assert result["created"] == 1
        assert result["skipped"] == 0
        assert len(created) == 1

    def test_skips_entry_with_existing_post(self):
        result, created = self._run([_entry(has_post=True)])
        assert result["created"] == 0
        assert result["skipped"] == 1
        assert len(created) == 0

    def test_mixed_entries(self):
        entries = [
            _entry(eid=1, has_post=False),
            _entry(eid=2, has_post=True),
            _entry(eid=3, has_post=False),
        ]
        result, created = self._run(entries)
        assert result["created"] == 2
        assert result["skipped"] == 1
        assert len(created) == 2

    def test_empty_calendar(self):
        result, created = self._run([])
        assert result["created"] == 0
        assert result["skipped"] == 0

    def test_passes_calendar_entry_id(self):
        result, created = self._run([_entry(eid=42)])
        assert created[0]["calendar_entry_id"] == 42

    def test_passes_rubric_id(self):
        result, created = self._run([_entry(rubric_id=7)])
        assert created[0]["rubric_id"] == 7

    def test_passes_publish_date_as_string(self):
        d = date(2026, 6, 1)
        result, created = self._run([_entry(publish_date=d)])
        assert created[0]["publish_date"] == "2026-06-01"

    def test_publish_date_already_string(self):
        result, created = self._run([_entry(publish_date="2026-06-15")])
        assert created[0]["publish_date"] == "2026-06-15"

    def test_channel_from_platform_name(self):
        result, created = self._run([_entry(platform_name="Яндекс Дзен")])
        assert created[0]["channel"] == "яндекс_дзен"

    def test_channel_fallback_when_no_platform(self):
        result, created = self._run([_entry(platform_name=None)])
        assert created[0]["channel"] == "dzen"

    def test_draft_status_by_default(self):
        result, created = self._run([_entry(content_ready=False)])
        assert created[0]["status"] == "draft"
        assert created[0]["article_body"] == ""

    def test_text_ready_when_content_ready_and_extra_info(self):
        entry = _entry(content_ready=True, extra_info="Готовый текст статьи")
        result, created = self._run([entry])
        assert created[0]["status"] == "text_ready"
        assert created[0]["article_body"] == "Готовый текст статьи"

    def test_draft_when_content_ready_but_no_extra_info(self):
        entry = _entry(content_ready=True, extra_info="")
        result, created = self._run([entry])
        assert created[0]["status"] == "draft"
        assert created[0]["article_body"] == ""

    def test_topic_equals_entry_title(self):
        result, created = self._run([_entry(title="Как сохранить воспоминания")])
        assert created[0]["topic"] == "Как сохранить воспоминания"

    def test_plan_id_is_none(self):
        result, created = self._run([_entry()])
        assert created[0]["plan_id"] is None
