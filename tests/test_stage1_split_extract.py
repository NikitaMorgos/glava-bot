#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit-тесты для task 035 split-extract логики:
- run_fact_extractor с phase="B" / call_type="incremental"
- merge_fact_maps (Phase B incremental + base from Phase A)
- run_completeness_auditor с pin-list events
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline_utils import merge_fact_maps


# ──────────────────────────────────────────────────────────────────
# merge_fact_maps — Phase B incremental merge
# ──────────────────────────────────────────────────────────────────

def test_merge_fact_maps_persons_dedup_by_id():
    """Persons: дедупликация по id. TR2 incremental добавляет новые, не дублирует существующие."""
    base = {
        "subject": {"name": "Каракулина В.И."},
        "persons": [
            {"id": "person_001", "name": "Дмитрий", "relation_to_subject": "муж"},
            {"id": "person_002", "name": "Татьяна", "relation_to_subject": "дочь"},
        ],
        "timeline": [],
    }
    incremental = {
        "persons": [
            {"id": "person_001", "name": "Дмитрий Каракулин", "relation_to_subject": "муж"},  # дубль по id
            {"id": "person_003", "name": "Нинвана Полсачева", "relation_to_subject": "врач"},  # новый
        ],
    }
    merged = merge_fact_maps(base, incremental)

    person_ids = [p["id"] for p in merged["persons"]]
    assert person_ids == ["person_001", "person_002", "person_003"]
    # person_003 помечен как is_new
    p3 = next(p for p in merged["persons"] if p["id"] == "person_003")
    assert p3.get("is_new") is True
    # person_001 не помечен (был в base)
    p1 = next(p for p in merged["persons"] if p["id"] == "person_001")
    assert "is_new" not in p1 or p1.get("is_new") is not True


def test_merge_fact_maps_timeline_dedup_by_id():
    """Timeline: дедупликация по id. v54 регрессия — огурцы новый event_id появляется."""
    base = {
        "persons": [],
        "timeline": [
            {"id": "event_001", "title": "Рождение 1920", "year": 1920},
            {"id": "event_002", "title": "Война 1941-1945", "year": "1941-1945"},
        ],
    }
    incremental = {
        "timeline": [
            {"id": "event_002", "title": "Война (refined)"},  # дубль
            {"id": "event_auto_010", "title": "Огурцы Молдавия 1990", "year": 1990},  # новый
            {"id": "event_auto_011", "title": "Счётчик 1977", "year": 1977},  # новый
        ],
    }
    merged = merge_fact_maps(base, incremental)

    timeline_ids = [e["id"] for e in merged["timeline"]]
    assert "event_001" in timeline_ids
    assert "event_002" in timeline_ids
    assert "event_auto_010" in timeline_ids  # огурцы добавлены
    assert "event_auto_011" in timeline_ids  # счётчик добавлен
    # Новые помечены
    e10 = next(e for e in merged["timeline"] if e["id"] == "event_auto_010")
    assert e10.get("is_new") is True


def test_merge_fact_maps_subject_no_overwrite():
    """Subject: incremental НЕ перезаписывает существующие поля base."""
    base = {
        "subject": {"name": "Каракулина В.И.", "birth_year": 1920},
        "persons": [],
        "timeline": [],
    }
    incremental = {
        "subject": {"name": "Каракулина другая", "birth_year": 1925, "death_year": 2005},
    }
    merged = merge_fact_maps(base, incremental)

    # Существующие base поля сохраняются
    assert merged["subject"]["name"] == "Каракулина В.И."
    assert merged["subject"]["birth_year"] == 1920
    # Новые поля из incremental добавляются
    assert merged["subject"]["death_year"] == 2005


def test_merge_fact_maps_marks_as_merged_from_phase_b():
    """Merged result имеет метку _merged_from_phase_b: True."""
    base = {"persons": [], "timeline": []}
    incremental = {"persons": [{"id": "p1", "name": "X"}]}
    merged = merge_fact_maps(base, incremental)
    assert merged.get("_merged_from_phase_b") is True


def test_merge_fact_maps_no_incremental_returns_base():
    """Если incremental пуст — возвращает base без изменений."""
    base = {"persons": [{"id": "p1"}]}
    assert merge_fact_maps(base, None) == base
    assert merge_fact_maps(base, {}).get("persons") == [{"id": "p1"}]


def test_merge_fact_maps_locations_dedup_by_name():
    """Locations: дедупликация по name."""
    base = {
        "persons": [], "timeline": [],
        "locations": [{"name": "Кировоград", "region": "UA"}],
    }
    incremental = {
        "locations": [
            {"name": "Кировоград", "year": 1938},  # дубль по name
            {"name": "Молдавия", "year": 1990},    # новый (TR2 only)
        ],
    }
    merged = merge_fact_maps(base, incremental)

    location_names = [l["name"] for l in merged["locations"]]
    assert "Кировоград" in location_names
    assert "Молдавия" in location_names
    moldavia = next(l for l in merged["locations"] if l["name"] == "Молдавия")
    assert moldavia.get("is_new") is True


def test_merge_fact_maps_character_traits_dedup_by_trait():
    """Character traits: дедупликация по trait."""
    base = {
        "persons": [], "timeline": [],
        "character_traits": [{"trait": "трудолюбие"}],
    }
    incremental = {
        "character_traits": [
            {"trait": "трудолюбие"},  # дубль
            {"trait": "стойкость"},   # новый
        ],
    }
    merged = merge_fact_maps(base, incremental)
    traits = [t["trait"] for t in merged["character_traits"]]
    assert traits == ["трудолюбие", "стойкость"]


# ──────────────────────────────────────────────────────────────────
# v54 регрессионный — TR2 events добавляются к TR1 fact_map
# ──────────────────────────────────────────────────────────────────

def test_v54_regression_cucumber_episode_added_via_phase_b():
    """v54 регрессия: эпизод огурцы Молдавия был в TR2, потерян в combined.
    Split-extract Phase B на TR2 с existing_facts=fact_map_TR1 → событие добавляется."""

    # Симуляция fact_map_TR1 (Phase A на TR1: основные события жизни)
    fact_map_tr1 = {
        "subject": {"name": "Каракулина В.И.", "birth_year": 1920},
        "persons": [
            {"id": "person_001", "name": "Валентина"},
            {"id": "person_002", "name": "Дмитрий", "relation_to_subject": "муж"},
            {"id": "person_003", "name": "Татьяна", "relation_to_subject": "дочь"},
            {"id": "person_004", "name": "Маргось Владимир", "relation_to_subject": "зять"},
        ],
        "timeline": [
            {"id": "event_001", "title": "Рождение 1920"},
            {"id": "event_002", "title": "Война 1941-1945"},
            {"id": "event_003", "title": "Брак Татьяны и Маргось 1977"},
            {"id": "event_004", "title": "Смерть Дмитрия 1978"},
        ],
    }

    # Симуляция fact_map от FE Phase B на TR2 — только новые события
    fact_map_tr2_incremental = {
        "persons": [
            {"id": "person_005", "name": "Нинвана Полсачева", "relation_to_subject": "врач"},
        ],
        "timeline": [
            {"id": "event_auto_005", "title": "Конфликт счётчик 1977", "year": 1977,
             "description": "Замечание про счётчик электричества от Владимира"},
            {"id": "event_auto_006", "title": "Огурцы Молдавия 1990", "year": 1990,
             "description": "Чемодан огурцов привёз Владимир"},
            {"id": "event_auto_007", "title": "Шарлотка", "description": "Любимый рецепт"},
        ],
    }

    merged = merge_fact_maps(fact_map_tr1, fact_map_tr2_incremental)

    # Все TR2-уникальные эпизоды добавлены
    titles = [e["title"] for e in merged["timeline"]]
    assert "Конфликт счётчик 1977" in titles
    assert "Огурцы Молдавия 1990" in titles
    assert "Шарлотка" in titles

    # Нинвана добавлена в persons
    person_names = [p["name"] for p in merged["persons"]]
    assert "Нинвана Полсачева" in person_names

    # TR1 события сохранены
    assert "Война 1941-1945" in titles
    assert "Брак Татьяны и Маргось 1977" in titles


# ──────────────────────────────────────────────────────────────────
# run_fact_extractor — phase parameter
# ──────────────────────────────────────────────────────────────────

def test_run_fact_extractor_default_phase_a():
    """По умолчанию run_fact_extractor использует phase='A' (backward compat)."""
    from pipeline_utils import run_fact_extractor
    import inspect

    sig = inspect.signature(run_fact_extractor)
    assert sig.parameters["phase"].default == "A"
    assert sig.parameters["call_type"].default == "initial"


def test_run_fact_extractor_signature_supports_phase_b():
    """run_fact_extractor принимает phase + call_type параметры."""
    from pipeline_utils import run_fact_extractor
    import inspect

    sig = inspect.signature(run_fact_extractor)
    assert "phase" in sig.parameters
    assert "call_type" in sig.parameters
    assert "existing_facts" in sig.parameters


# ──────────────────────────────────────────────────────────────────
# run_completeness_auditor — pin-list events support
# ──────────────────────────────────────────────────────────────────

def test_ca_pin_list_includes_events_in_user_message():
    """run_completeness_auditor передаёт events в pin_list (v1.2)."""
    from pipeline_utils import run_completeness_auditor

    # Мокаем client и streaming response
    mock_response = MagicMock()
    mock_response.usage.input_tokens = 100
    mock_response.usage.output_tokens = 200

    mock_stream = MagicMock()
    mock_stream.__enter__ = MagicMock(return_value=mock_stream)
    mock_stream.__exit__ = MagicMock(return_value=None)
    mock_stream.text_stream = iter(['{"auto_enrich": {}, "log_only_gaps": {}, "processing_notes": {}}'])
    mock_stream.get_final_message = MagicMock(return_value=mock_response)

    mock_client = MagicMock()
    mock_client.messages.stream.return_value = mock_stream

    pin_list_fact_map = {
        "persons": [
            {"id": "person_001", "name": "Нинвана", "aliases": [], "relation_to_subject": "врач"},
        ],
        "timeline": [
            {"id": "event_001", "title": "Огурцы Молдавия 1990",
             "year": 1990, "markers": ["огурцы", "Молдавия", "чемодан"]},
        ],
    }

    cfg = {
        "completeness_auditor": {
            "model": "claude-haiku-test",
            "max_tokens": 1000,
            "temperature": 0.1,
            "prompt_file": "16_completeness_auditor_v1.2.md",
        }
    }

    with patch("pipeline_utils.load_prompt", return_value="test prompt"):
        result = run_completeness_auditor(
            mock_client,
            cleaned_text="test transcript",
            fact_map={"persons": [], "timeline": []},
            subject_name="X",
            narrator_name="Y",
            narrator_relation="Z",
            project_id="test",
            pin_list_fact_map=pin_list_fact_map,
            cfg=cfg,
        )

    # Проверяем что pin_list передан с events
    call_args = mock_client.messages.stream.call_args
    user_message_json = call_args.kwargs["messages"][0]["content"]
    import json
    user_message = json.loads(user_message_json)
    assert "pin_list" in user_message
    assert "persons" in user_message["pin_list"]
    assert "events" in user_message["pin_list"]
    assert len(user_message["pin_list"]["events"]) == 1
    assert user_message["pin_list"]["events"][0]["title"] == "Огурцы Молдавия 1990"


def test_ca_pin_list_persons_only_no_events_field_optional():
    """Если в pin_list_fact_map нет events — events передаётся пустым list, не падает."""
    from pipeline_utils import run_completeness_auditor

    mock_response = MagicMock()
    mock_response.usage.input_tokens = 100
    mock_response.usage.output_tokens = 200
    mock_stream = MagicMock()
    mock_stream.__enter__ = MagicMock(return_value=mock_stream)
    mock_stream.__exit__ = MagicMock(return_value=None)
    mock_stream.text_stream = iter(['{"auto_enrich": {}, "log_only_gaps": {}, "processing_notes": {}}'])
    mock_stream.get_final_message = MagicMock(return_value=mock_response)
    mock_client = MagicMock()
    mock_client.messages.stream.return_value = mock_stream

    pin_list_fact_map = {
        "persons": [{"id": "p1", "name": "X"}],
        # нет timeline / events
    }

    cfg = {"completeness_auditor": {"model": "m", "max_tokens": 100, "temperature": 0.1, "prompt_file": "p"}}

    with patch("pipeline_utils.load_prompt", return_value="test"):
        # Не должно падать
        run_completeness_auditor(
            mock_client, "transcript", {"persons": [], "timeline": []},
            "X", "Y", "Z", "test", pin_list_fact_map=pin_list_fact_map, cfg=cfg,
        )

    import json as _json
    user_msg = _json.loads(mock_client.messages.stream.call_args.kwargs["messages"][0]["content"])
    assert user_msg["pin_list"]["events"] == []


def test_ca_pin_list_events_only_no_persons():
    """Pin-list только с events (известные эпизоды), без persons — работает."""
    from pipeline_utils import run_completeness_auditor

    mock_response = MagicMock()
    mock_response.usage.input_tokens = 100
    mock_response.usage.output_tokens = 200
    mock_stream = MagicMock()
    mock_stream.__enter__ = MagicMock(return_value=mock_stream)
    mock_stream.__exit__ = MagicMock(return_value=None)
    mock_stream.text_stream = iter(['{"auto_enrich": {}, "log_only_gaps": {}}'])
    mock_stream.get_final_message = MagicMock(return_value=mock_response)
    mock_client = MagicMock()
    mock_client.messages.stream.return_value = mock_stream

    pin_list_fact_map = {
        "timeline": [
            {"id": "e1", "title": "Огурцы", "markers": ["огурцы", "Молдавия"]},
            {"id": "e2", "title": "Счётчик 1977", "markers": ["счётчик", "1977"]},
        ],
    }
    cfg = {"completeness_auditor": {"model": "m", "max_tokens": 100, "temperature": 0.1, "prompt_file": "p"}}

    with patch("pipeline_utils.load_prompt", return_value="test"):
        run_completeness_auditor(
            mock_client, "transcript", {"persons": [], "timeline": []},
            "X", "Y", "Z", "test", pin_list_fact_map=pin_list_fact_map, cfg=cfg,
        )

    import json as _json
    user_msg = _json.loads(mock_client.messages.stream.call_args.kwargs["messages"][0]["content"])
    assert user_msg["pin_list"]["persons"] == []
    assert len(user_msg["pin_list"]["events"]) == 2


def test_ca_no_pin_list_no_field_in_user_message():
    """Если pin_list_fact_map не передан — поле pin_list отсутствует в user_message."""
    from pipeline_utils import run_completeness_auditor

    mock_response = MagicMock()
    mock_response.usage.input_tokens = 100
    mock_response.usage.output_tokens = 200
    mock_stream = MagicMock()
    mock_stream.__enter__ = MagicMock(return_value=mock_stream)
    mock_stream.__exit__ = MagicMock(return_value=None)
    mock_stream.text_stream = iter(['{"auto_enrich": {}, "log_only_gaps": {}}'])
    mock_stream.get_final_message = MagicMock(return_value=mock_response)
    mock_client = MagicMock()
    mock_client.messages.stream.return_value = mock_stream

    cfg = {"completeness_auditor": {"model": "m", "max_tokens": 100, "temperature": 0.1, "prompt_file": "p"}}

    with patch("pipeline_utils.load_prompt", return_value="test"):
        run_completeness_auditor(
            mock_client, "transcript", {"persons": [], "timeline": []},
            "X", "Y", "Z", "test", pin_list_fact_map=None, cfg=cfg,
        )

    import json as _json
    user_msg = _json.loads(mock_client.messages.stream.call_args.kwargs["messages"][0]["content"])
    assert "pin_list" not in user_msg
