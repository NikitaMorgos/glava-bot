#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit-тесты для validate_le_fact_preservation (волна 1.4.0).

Защита от регрессии #7 (v53b, 2026-05-08): Stage 3 Literary Editor
удалил эпизод об огурцах в Молдавии тихо, без revision-цикла. Stage 2
защиты пропустили эпизод корректно. validate_revision_volume работает
только на GW revision iters, не на Stage 2→3 transition.

Эта функция проверяет на Stage 2→3 переходе что каждое событие из
fact_map.timeline имеет ≥2 предметных маркеров в book после LE.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline_utils import (
    validate_le_fact_preservation,
    _extract_event_markers,
    _event_present_in_book,
    LE_EVENT_MIN_MARKERS,
)


# ──────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────

def _book(chapters_text: dict[str, str], callouts=None, historical_notes=None) -> dict:
    """Минимальная книга: словарь chapter_id → content."""
    return {
        "chapters": [
            {"id": ch_id, "content": text} for ch_id, text in chapters_text.items()
        ],
        "callouts": [
            {"id": f"co_{i:02d}", "chapter_id": ch_id, "text": text}
            for i, (ch_id, text) in enumerate(callouts or [], 1)
        ],
        "historical_notes": [
            {"id": f"hn_{i:02d}", "chapter_id": ch_id, "text": text}
            for i, (ch_id, text) in enumerate(historical_notes or [], 1)
        ],
    }


def _event(event_id: str, *, source_quotes=None, description="", title="", year=None) -> dict:
    """Минимальное timeline event."""
    e = {"id": event_id}
    if source_quotes:
        e["source_quotes"] = [{"text": q} for q in source_quotes]
    if description:
        e["description"] = description
    if title:
        e["title"] = title
    if year:
        e["year"] = year
    return e


def _fact_map(events: list[dict]) -> dict:
    """fact_map с timeline."""
    return {"timeline": events}


# ──────────────────────────────────────────────────────────────────
# Базовый сценарий: события сохраняются → passed
# ──────────────────────────────────────────────────────────────────

def test_all_events_preserved_passes():
    """Все события из timeline присутствуют в book_after_le → passed.

    Маркеры из source_quote — предметные (Воронеж/Куйбышев/институт),
    LE перефразирует но маркеры остаются.
    """
    fact_map = _fact_map([
        _event("event_001", source_quotes=["Воронеж школа институт 1955"]),
        _event("event_002", source_quotes=["Куйбышев институт связи общежитие"]),
    ])
    book_before = _book({
        "ch_01": (
            "Школа Воронеж 1955 — потом институт. "
            "Куйбышев институт связи общежитие тесное."
        ),
    })
    book_after = _book({
        # LE перефразировал, маркеры остались
        "ch_01": (
            "Школа в Воронеже 1955 — затем поступление в институт. "
            "В Куйбышеве институт связи, жила в общежитии."
        ),
    })

    passed, details = validate_le_fact_preservation(book_before, book_after, fact_map)

    assert passed
    assert details["verdict"] == "ok_all_events_preserved"
    assert details["events_lost_in_le"] == 0
    assert details["events_preserved"] == 2


# ──────────────────────────────────────────────────────────────────
# v53b регрессия: огурцы удалены LE
# ──────────────────────────────────────────────────────────────────

def test_v53b_regression_le_deleted_episode_blocks():
    """v53b: эпизод про огурцы был в book после Stage 2, удалён LE → blocked."""
    fact_map = _fact_map([
        _event(
            "event_auto_002",
            source_quotes=[
                "Зять Владимир привёз чемодан огурцов из Молдавии в 1990 году."
            ],
            title="Огурцы из Молдавии",
            year=1990,
        ),
        _event(
            "event_auto_004",
            source_quotes=[
                "Зять сделал замечание про счётчик электричества в 1977 году."
            ],
            title="Замечание про счётчик",
            year=1977,
        ),
    ])
    book_before = _book({
        "ch_01": "Жизнь шла своим чередом. Электричество, быт, семья.",
        "ch_02": (
            "В 1977 году зять Владимир сделал замечание про счётчик электричества. "
            "А в 1990 году он же привёз огромный чемодан огурцов из Молдавии — "
            "история стала семейной легендой."
        ),
    })
    # LE удалил эпизод про огурцы (счёл дублем темы «конфликт с зятем»)
    book_after = _book({
        "ch_01": "Жизнь шла своим чередом. Электричество, быт, семья.",
        "ch_02": "В 1977 году зять Владимир сделал замечание про счётчик электричества.",
    })

    passed, details = validate_le_fact_preservation(book_before, book_after, fact_map)

    assert not passed
    assert details["verdict"] == "blocked_events_lost_in_le"
    assert details["events_lost_in_le"] == 1
    lost = details["lost_events"][0]
    assert lost["event_id"] == "event_auto_002"
    assert lost["title"] == "Огурцы из Молдавии"
    # Маркеры огурцы/чемодан/молдавии должны были быть найдены в book_before
    # но не в book_after
    assert any("огурц" in m for m in lost["markers"])
    assert any("молдави" in m for m in lost["markers"])


def test_v53b_other_event_preserved_when_one_lost():
    """v53b: даже если один эпизод удалён, остальные регистрируются как preserved."""
    fact_map = _fact_map([
        _event(
            "event_auto_002",
            source_quotes=["Чемодан огурцов из Молдавии 1990"],
        ),
        _event(
            "event_auto_004",
            source_quotes=["Замечание про счётчик электричества 1977"],
        ),
    ])
    book_before = _book({
        "ch_02": (
            "Замечание про счётчик электричества 1977. "
            "Чемодан огурцов из Молдавии 1990."
        ),
    })
    book_after = _book({
        "ch_02": "Замечание про счётчик электричества 1977.",  # огурцы удалены
    })

    _, details = validate_le_fact_preservation(book_before, book_after, fact_map)

    assert details["events_lost_in_le"] == 1
    assert details["events_preserved"] == 1


# ──────────────────────────────────────────────────────────────────
# Edge cases
# ──────────────────────────────────────────────────────────────────

def test_empty_timeline_passes():
    """Пустой timeline — нечего проверять, passed."""
    fact_map = _fact_map([])
    book_before = _book({"ch_01": "any"})
    book_after = _book({"ch_01": "any"})

    passed, details = validate_le_fact_preservation(book_before, book_after, fact_map)

    assert passed
    assert details["events_in_timeline"] == 0


def test_event_not_in_book_before_le_skipped():
    """Если события не было в book_before_le — пропускается, не наша зона."""
    fact_map = _fact_map([
        _event("event_999", source_quotes=["Уникальный эпизод про вертолёт в Кустанае"]),
    ])
    book_before = _book({"ch_01": "Совсем другой текст без вертолёта."})
    book_after = _book({"ch_01": "Совсем другой текст без вертолёта."})

    passed, details = validate_le_fact_preservation(book_before, book_after, fact_map)

    assert passed
    assert details["events_not_in_book_before_le"] == 1
    assert details["events_lost_in_le"] == 0


def test_event_with_insufficient_markers_skipped():
    """Event с <2 маркеров пропускается с пометкой insufficient_markers."""
    fact_map = _fact_map([
        _event("event_short", source_quotes=["Шла."]),  # 0 значимых маркеров
    ])
    book_before = _book({"ch_01": "Шла."})
    book_after = _book({"ch_01": "Шла."})

    passed, details = validate_le_fact_preservation(book_before, book_after, fact_map)

    assert passed
    assert details["events_insufficient_markers"] == 1


def test_legitimate_le_rephrasing_preserves_markers():
    """LE может перефразировать эпизод, но маркеры остаются → passed."""
    fact_map = _fact_map([
        _event(
            "event_001",
            source_quotes=[
                "Поехала в Молдавию в 1990 году, привезла чемодан огурцов."
            ],
        ),
    ])
    book_before = _book({
        "ch_01": "Поехала в Молдавию в 1990 году, привезла чемодан огурцов.",
    })
    book_after = _book({
        # LE перефразировал, маркеры остались
        "ch_01": "В 1990 году отправилась в Молдавию и вернулась с чемоданом огурцов.",
    })

    passed, details = validate_le_fact_preservation(book_before, book_after, fact_map)

    assert passed


def test_event_preserved_in_callout():
    """Событие может быть представлено в callout, не основном тексте → preserved."""
    fact_map = _fact_map([
        _event(
            "event_001",
            source_quotes=["Чемодан огурцов из Молдавии в 1990"],
        ),
    ])
    book_before = _book(
        {"ch_02": "Чемодан огурцов из Молдавии в 1990. Длинный нарратив."},
    )
    book_after = _book(
        {"ch_02": "Длинный нарратив без эпизода."},
        callouts=[("ch_02", "Чемодан огурцов из Молдавии в 1990 — семейная легенда.")],
    )

    passed, _ = validate_le_fact_preservation(book_before, book_after, fact_map)
    assert passed


def test_event_preserved_in_historical_note():
    """Событие может быть в historical_note → preserved."""
    fact_map = _fact_map([
        _event(
            "event_001",
            source_quotes=["Перестройка в Молдавии 1990 чемодан огурцов"],
        ),
    ])
    book_before = _book({
        "ch_02": "Перестройка в Молдавии 1990 чемодан огурцов.",
    })
    book_after = _book(
        {"ch_02": "Текст без маркеров."},
        historical_notes=[("ch_02", "В 1990 в Молдавии был дефицит. Чемодан огурцов из той эпохи.")],
    )

    passed, _ = validate_le_fact_preservation(book_before, book_after, fact_map)
    assert passed


def test_partial_marker_loss_below_threshold_blocks():
    """Если маркеров было 4, осталось 1 — это blocked (нужно ≥2)."""
    fact_map = _fact_map([
        _event(
            "event_001",
            source_quotes=[
                "Чемодан огурцов из Молдавии в 1990 году привёз Владимир."
            ],
        ),
    ])
    book_before = _book({
        "ch_02": "Чемодан огурцов из Молдавии в 1990 году привёз Владимир.",
    })
    # LE сжал так что остался только один маркер
    book_after = _book({
        "ch_02": "Владимир что-то привозил из поездки.",
    })

    passed, details = validate_le_fact_preservation(book_before, book_after, fact_map)

    assert not passed
    assert details["events_lost_in_le"] == 1


def test_events_field_alternative_name():
    """fact_map может использовать events вместо timeline — обрабатывается."""
    fact_map = {
        "events": [
            _event("event_001", source_quotes=["Молдавия чемодан огурцов 1990"]),
        ]
    }
    book_before = _book({"ch_01": "Молдавия чемодан огурцов 1990"})
    book_after = _book({"ch_01": "Молдавия чемодан огурцов 1990"})

    passed, details = validate_le_fact_preservation(book_before, book_after, fact_map)
    assert passed
    assert details["events_in_timeline"] == 1


def test_no_timeline_field_passes_safely():
    """fact_map без timeline/events — defensively passes."""
    fact_map = {}
    passed, _ = validate_le_fact_preservation(_book({"ch_01": "x"}), _book({"ch_01": "x"}), fact_map)
    assert passed


# ──────────────────────────────────────────────────────────────────
# Helpers tests
# ──────────────────────────────────────────────────────────────────

def test_extract_event_markers_filters_stop_words_and_short():
    """Маркеры — длинные значимые токены, не имена/темы."""
    event = _event(
        "e1",
        source_quotes=["Семья отправилась в Молдавию за огурцами в 1990 году"],
    )
    markers = _extract_event_markers(event)

    # Должны быть: молдавию (или молдавии), огурцами
    # НЕ должны быть: семья (стоп-слово), отправилась (общее), году (общее)
    assert any("молдави" in m for m in markers)
    assert any("огурц" in m for m in markers)
    assert "семья" not in markers


def test_extract_event_markers_uses_description_as_fallback():
    """Если source_quotes пуст, использует description."""
    event = {"id": "e1", "description": "Молдавия чемодан огурцов 1990"}
    markers = _extract_event_markers(event)

    assert any("молдави" in m for m in markers)


def test_extract_event_markers_top_n_limit():
    """Результат не больше max_markers (default 4)."""
    event = _event(
        "e1",
        source_quotes=[
            "Молдавия Воронеж Куйбышев Тбилиси Ереван Минск Архангельск"
        ],
    )
    markers = _extract_event_markers(event, max_markers=4)
    assert len(markers) <= 4


def test_event_present_in_book_min_markers_threshold():
    """≥2 общих маркеров → True. <2 → False."""
    markers = {"молдавия", "огурцы", "чемодан", "владимир"}
    book = _book({"ch_01": "Привёз огурцы и чемодан."})

    present, shared = _event_present_in_book(markers, book, min_markers=2)
    assert present
    assert shared == {"огурцы", "чемодан"}


def test_event_present_in_book_below_threshold():
    """1 общий маркер → False."""
    markers = {"молдавия", "огурцы", "чемодан"}
    book = _book({"ch_01": "Только огурцы упомянуты, ничего больше."})

    present, shared = _event_present_in_book(markers, book, min_markers=2)
    assert not present
    assert shared == {"огурцы"}


def test_le_event_min_markers_constant():
    """LE_EVENT_MIN_MARKERS = 2 — соответствует FC EVIDENCE_MIN_SHARED_TOKENS."""
    assert LE_EVENT_MIN_MARKERS == 2


# ──────────────────────────────────────────────────────────────────
# Не мутирует входы
# ──────────────────────────────────────────────────────────────────

def test_validator_does_not_mutate_inputs():
    """validate_le_fact_preservation не модифицирует book_before/book_after/fact_map."""
    fact_map = _fact_map([_event("e1", source_quotes=["Молдавия огурцы 1990"])])
    book_before = _book({"ch_01": "Молдавия огурцы 1990"})
    book_after = _book({"ch_01": ""})

    fm_snap = repr(fact_map)
    before_snap = repr(book_before)
    after_snap = repr(book_after)

    validate_le_fact_preservation(book_before, book_after, fact_map)

    assert repr(fact_map) == fm_snap
    assert repr(book_before) == before_snap
    assert repr(book_after) == after_snap
