#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit-тесты для расширения run_fact_checker сигнатурой historical_context
(волна 1.3, шаг 1.3.1).

Покрытие:
  1. Backward compat: вызов без historical_context — historical_context
     не появляется в user_message
  2. Прямой dict-формат от Historian (с обёрткой historical_context+era_glossary)
     — распакован корректно
  3. Список — передан как есть
  4. None — игнорируется (не добавляется в user_message)
  5. Пустой dict / список — также игнорируется
  6. Other dict (без обёртки) — обёрнут в список как fallback

Тесты не вызывают Anthropic — мокают client.messages.stream и проверяют
содержимое user_message.
"""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pipeline_utils  # noqa: E402


# ──────────────────────────────────────────────────────────────────
# Helpers — minimal mock for run_fact_checker
# ──────────────────────────────────────────────────────────────────

def _make_mock_client(response_json: str = '{"verdict":"pass","errors":[]}'):
    """Создаёт mock anthropic client возвращающий заданный JSON."""
    captured = {}

    class _StreamCtx:
        text_stream = [response_json]

        def __enter__(self_):
            return self_

        def __exit__(self_, *args):
            return False

        def get_final_message(self_):
            usage = MagicMock()
            usage.input_tokens = 100
            usage.output_tokens = 20
            msg = MagicMock()
            msg.usage = usage
            return msg

    def _stream(model, max_tokens, temperature, system, messages):
        # Захватываем user_message из messages для проверки в тесте
        captured["user_message"] = json.loads(messages[0]["content"])
        captured["system"] = system
        return _StreamCtx()

    client = MagicMock()
    client.messages.stream = _stream
    return client, captured


def _make_min_cfg():
    """Минимальный cfg чтобы run_fact_checker не падал на load_config."""
    return {
        "fact_checker": {
            "model": "test-model",
            "max_tokens": 1000,
            "temperature": 0.1,
            "prompt_file": "04_fact_checker_v2.11.md",
        }
    }


def _book() -> dict:
    return {"chapters": [{"id": "ch_01", "content": "test"}]}


def _fact_map() -> dict:
    return {"persons": [], "timeline": []}


def _transcripts() -> list:
    return [{"interview_id": "i1", "speaker_name": "X", "text": "..."}]


# ──────────────────────────────────────────────────────────────────
# Тесты
# ──────────────────────────────────────────────────────────────────

def test_backward_compat_no_historical_context():
    """Вызов без historical_context — поле не появляется в user_message."""
    client, captured = _make_mock_client()
    pipeline_utils.run_fact_checker(
        client, _book(), _fact_map(), _transcripts(),
        project_id="test", cfg=_make_min_cfg(),
    )
    assert "historical_context" not in captured["user_message"]
    assert "era_glossary" not in captured["user_message"]


def test_historian_dict_format_unpacked():
    """
    Прямой output от run_historian: {"historical_context": [...], "era_glossary": [...]}
    Должен быть распакован: оба поля переходят в user_message отдельно.
    """
    historian_output = {
        "historical_context": [
            {"ctx_id": "ctx_001", "type": "era_marker", "summary": "test"}
        ],
        "era_glossary": [
            {"term": "стахановец", "definition": "..."}
        ],
    }
    client, captured = _make_mock_client()
    pipeline_utils.run_fact_checker(
        client, _book(), _fact_map(), _transcripts(),
        project_id="test",
        historical_context=historian_output,
        cfg=_make_min_cfg(),
    )
    assert captured["user_message"]["historical_context"] == historian_output["historical_context"]
    assert captured["user_message"]["era_glossary"] == historian_output["era_glossary"]


def test_list_format_passed_as_is():
    """Список historical_context — передан как есть, era_glossary нет."""
    ctx_list = [{"ctx_id": "ctx_001", "type": "era_marker"}]
    client, captured = _make_mock_client()
    pipeline_utils.run_fact_checker(
        client, _book(), _fact_map(), _transcripts(),
        project_id="test",
        historical_context=ctx_list,
        cfg=_make_min_cfg(),
    )
    assert captured["user_message"]["historical_context"] == ctx_list
    assert "era_glossary" not in captured["user_message"]


def test_none_ignored():
    """historical_context=None — не добавляется в user_message (backward compat)."""
    client, captured = _make_mock_client()
    pipeline_utils.run_fact_checker(
        client, _book(), _fact_map(), _transcripts(),
        project_id="test",
        historical_context=None,
        cfg=_make_min_cfg(),
    )
    assert "historical_context" not in captured["user_message"]


def test_empty_dict_ignored():
    """Пустой dict {} — falsy, игнорируется."""
    client, captured = _make_mock_client()
    pipeline_utils.run_fact_checker(
        client, _book(), _fact_map(), _transcripts(),
        project_id="test",
        historical_context={},
        cfg=_make_min_cfg(),
    )
    assert "historical_context" not in captured["user_message"]


def test_empty_list_ignored():
    """Пустой list [] — falsy, игнорируется."""
    client, captured = _make_mock_client()
    pipeline_utils.run_fact_checker(
        client, _book(), _fact_map(), _transcripts(),
        project_id="test",
        historical_context=[],
        cfg=_make_min_cfg(),
    )
    assert "historical_context" not in captured["user_message"]


def test_dict_without_wrapper_wrapped_in_list():
    """
    Dict без ключа historical_context (странный edge case) — оборачивается
    в список как fallback. Защита от неожиданного формата.
    """
    weird_dict = {"ctx_id": "ctx_001", "summary": "raw"}
    client, captured = _make_mock_client()
    pipeline_utils.run_fact_checker(
        client, _book(), _fact_map(), _transcripts(),
        project_id="test",
        historical_context=weird_dict,
        cfg=_make_min_cfg(),
    )
    assert captured["user_message"]["historical_context"] == [weird_dict]


def test_historian_dict_without_era_glossary():
    """Если в Historian dict нет era_glossary — historical_context передаётся,
    era_glossary в user_message не добавляется."""
    historian_output = {
        "historical_context": [{"ctx_id": "ctx_001"}],
        # без era_glossary
    }
    client, captured = _make_mock_client()
    pipeline_utils.run_fact_checker(
        client, _book(), _fact_map(), _transcripts(),
        project_id="test",
        historical_context=historian_output,
        cfg=_make_min_cfg(),
    )
    assert captured["user_message"]["historical_context"] == [{"ctx_id": "ctx_001"}]
    assert "era_glossary" not in captured["user_message"]


def test_v48_regression_context_reaches_fc():
    """
    Регрессионный тест на v48: historical_context от Historian должен
    дойти до FC при стандартном workflow. Если не дойдёт — FC не сможет
    проверить Historian-материал в книге, любой такой текст будет
    помечен как hallucination и удалён в revision (v48 цикл).
    """
    # Симулируем реальный output run_historian с suggested_insertions
    historian_real = {
        "historical_context": [
            {
                "ctx_id": "ctx_001",
                "type": "era_marker",
                "period": "1946-1947",
                "summary": "Послевоенное восстановление",
                "suggested_insertions": [
                    {
                        "chapter_hint": "ch_02",
                        "placement_hint": "после возвращения с фронта",
                        "text": "В 1946 году тысячи фронтовиков создавали семьи — "
                                "война научила ценить каждый мирный день.",
                    }
                ],
            }
        ],
        "era_glossary": [],
    }
    client, captured = _make_mock_client()
    pipeline_utils.run_fact_checker(
        client, _book(), _fact_map(), _transcripts(),
        project_id="karakulina",
        historical_context=historian_real,
        cfg=_make_min_cfg(),
    )

    # FC должен получить весь historical_context включая suggested_insertions
    received_ctx = captured["user_message"]["historical_context"]
    assert len(received_ctx) == 1
    assert received_ctx[0]["suggested_insertions"][0]["text"].startswith(
        "В 1946 году тысячи фронтовиков"
    )
