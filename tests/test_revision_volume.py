#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit-тесты для validate_revision_volume (волна 1.2.2).

Защита от регрессии #3 v43: Ghostwriter «исправил» ошибку при revision
через удаление эпизода (огурцы исчезли) вместо корректировки даты.

Покрывают три сценария:
  A. Объём после revision ≥ 95% от до — passed=True (норма)
  B. Объём упал > 5%, но FC явно разрешил удаление через
     legitimate_deletion=true — passed=True (исключение)
  C. Объём упал > 5%, FC не разрешил удаление — passed=False (защита сработала)

Плюс edge cases: пустая книга до, callouts/notes учитываются в подсчёте,
порог настраиваемый через min_ratio.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline_utils import (
    validate_revision_volume,
    _book_total_chars,
    REVISION_MIN_VOLUME_RATIO,
)


# ──────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────

def _book(chapters_text: dict[str, str], callouts: list[str] = None,
          historical_notes: list[str] = None) -> dict:
    """Минимальная книга: словарь chapter_id → content."""
    return {
        "chapters": [
            {"id": ch_id, "content": text}
            for ch_id, text in chapters_text.items()
        ],
        "callouts": [
            {"id": f"co_{i:02d}", "chapter_id": "ch_02", "text": t}
            for i, t in enumerate(callouts or [], 1)
        ],
        "historical_notes": [
            {"id": f"hist_{i:02d}", "chapter_id": "ch_02", "text": t}
            for i, t in enumerate(historical_notes or [], 1)
        ],
    }


def _err(err_id: str, *, legitimate_deletion: bool = False, **kwargs) -> dict:
    """Минимальная FC-ошибка."""
    return {
        "id": err_id,
        "type": kwargs.get("type", "distortion"),
        "severity": kwargs.get("severity", "major"),
        "chapter_id": kwargs.get("chapter_id", "ch_02"),
        "fix_instruction": kwargs.get("fix_instruction", "..."),
        "legitimate_deletion": legitimate_deletion,
    }


def _fc_report(errors: list[dict]) -> dict:
    return {"verdict": "fail", "errors": errors}


# ──────────────────────────────────────────────────────────────────
# Сценарий A: объём не упал — passed=True
# ──────────────────────────────────────────────────────────────────

def test_volume_within_threshold_passes():
    """Объём после revision ≈ объём до — норма, passed=True."""
    before = _book({"ch_02": "А" * 10000})
    after = _book({"ch_02": "А" * 9700})  # 97% от исходного

    passed, details = validate_revision_volume(before, after)

    assert passed is True
    assert details["verdict"] == "ok_within_threshold"
    assert details["ratio"] >= REVISION_MIN_VOLUME_RATIO


def test_volume_grew_after_revision_passes():
    """Объём вырос после revision (например, добавлен контекст) — passed=True."""
    before = _book({"ch_02": "А" * 5000})
    after = _book({"ch_02": "А" * 5500})

    passed, details = validate_revision_volume(before, after)

    assert passed is True
    assert details["ratio"] > 1.0


# ──────────────────────────────────────────────────────────────────
# Сценарий B: объём упал, но FC разрешил удаление — passed=True
# ──────────────────────────────────────────────────────────────────

def test_volume_drop_with_legitimate_deletion_passes():
    """
    Объём упал на 15%, но FC поставил legitimate_deletion=true для одной
    ошибки — это разрешённое удаление галлюцинированного эпизода. passed=True.
    """
    before = _book({"ch_02": "А" * 10000})
    after = _book({"ch_02": "А" * 8500})  # 85%, упал на 15%
    fc = _fc_report([
        _err("err_001", legitimate_deletion=True,
             type="hallucination",
             fix_instruction="Удалить эпизод о Магадане целиком — нет источника"),
    ])

    passed, details = validate_revision_volume(before, after, fc_report=fc)

    assert passed is True
    assert details["verdict"] == "ok_with_legitimate_deletion"
    assert details["legitimate_deletions_count"] == 1
    assert details["legitimate_deletions"][0]["id"] == "err_001"


# ──────────────────────────────────────────────────────────────────
# Сценарий C: объём упал, FC НЕ разрешил — passed=False (защита!)
# ──────────────────────────────────────────────────────────────────

def test_volume_drop_without_legitimate_deletion_fails():
    """
    Объём упал на 15%, FC не пометил ни одну ошибку как
    legitimate_deletion. Это ровно регрессия #3 v43 — GW «исправил»
    через удаление. passed=False.
    """
    before = _book({"ch_02": "А" * 10000})
    after = _book({"ch_02": "А" * 8500})  # 85%, упал на 15%
    fc = _fc_report([
        _err("err_001", legitimate_deletion=False,
             type="confidence_inflation",
             fix_instruction="Заменить датировку «90-е» на «1970-80-е»"),
    ])

    passed, details = validate_revision_volume(before, after, fc_report=fc)

    assert passed is False
    assert details["verdict"] == "blocked_unauthorized_deletion"
    assert details["legitimate_deletions_count"] == 0
    assert "anti-deletion" in details["reason"].lower() or "deletion" in details["reason"]
    assert details["drop_chars"] == 1500


def test_volume_drop_without_fc_report_fails():
    """Объём упал, но FC отчёт вообще не передан — fail."""
    before = _book({"ch_02": "А" * 10000})
    after = _book({"ch_02": "А" * 8000})

    passed, details = validate_revision_volume(before, after, fc_report=None)

    assert passed is False
    assert details["legitimate_deletions_count"] == 0


# ──────────────────────────────────────────────────────────────────
# Edge case: пустая книга до — любой объём после допустим
# ──────────────────────────────────────────────────────────────────

def test_empty_book_before_passes():
    """Пустая исходная книга — нет смысла считать ratio. passed=True."""
    before = _book({})
    after = _book({"ch_02": "А" * 5000})

    passed, details = validate_revision_volume(before, after)

    assert passed is True
    assert details["chars_before"] == 0


# ──────────────────────────────────────────────────────────────────
# Учёт callouts и historical_notes в объёме
# ──────────────────────────────────────────────────────────────────

def test_callouts_and_historical_notes_count_toward_volume():
    """
    _book_total_chars учитывает суммарный объём chapters + callouts +
    historical_notes. Удаление callout также падает в drop_chars.
    """
    before = _book(
        {"ch_02": "А" * 5000},
        callouts=["Цитата1" * 100, "Цитата2" * 100],  # 1400 chars total
        historical_notes=["Историч1" * 100, "Историч2" * 100],  # 1600 chars
    )
    # Удалили все callouts и historical_notes
    after = _book({"ch_02": "А" * 5000})

    chars_before = _book_total_chars(before)
    chars_after = _book_total_chars(after)
    assert chars_before > chars_after  # объём упал
    assert chars_before - chars_after == 3000  # callouts + notes удалены

    passed, details = validate_revision_volume(before, after, fc_report=None)
    # Удалили 3000 из 8000 = 37.5% — far below 95% threshold
    assert passed is False
    assert details["drop_chars"] == 3000


# ──────────────────────────────────────────────────────────────────
# Граничный случай: ровно 95% (на пороге)
# ──────────────────────────────────────────────────────────────────

def test_exactly_at_threshold_passes():
    """ratio = 0.95 — ровно порог, должен PASS (>= не >)."""
    before = _book({"ch_02": "А" * 10000})
    after = _book({"ch_02": "А" * 9500})  # ровно 95%

    passed, details = validate_revision_volume(before, after)

    assert passed is True
    assert details["ratio"] == 0.95


def test_just_below_threshold_with_no_authorization_fails():
    """ratio = 0.949 — чуть ниже порога, без legitimate — FAIL."""
    before = _book({"ch_02": "А" * 10000})
    after = _book({"ch_02": "А" * 9490})  # 94.9%

    passed, details = validate_revision_volume(before, after)

    assert passed is False


# ──────────────────────────────────────────────────────────────────
# Custom min_ratio параметр
# ──────────────────────────────────────────────────────────────────

def test_custom_min_ratio_strict():
    """Если caller хочет более строгий порог — параметр min_ratio."""
    before = _book({"ch_02": "А" * 10000})
    after = _book({"ch_02": "А" * 9700})  # 97%

    # При дефолте 95% — passed
    passed_default, _ = validate_revision_volume(before, after)
    assert passed_default is True

    # При строгом 98% — fail
    passed_strict, details = validate_revision_volume(before, after, min_ratio=0.98)
    assert passed_strict is False
    assert details["threshold"] == 0.98


# ──────────────────────────────────────────────────────────────────
# Регрессия #3 v43: конкретный кейс «огурцы исчезли»
# ──────────────────────────────────────────────────────────────────

def test_regression_3_v43_cucumbers_episode_deletion_blocked():
    """
    Реалистичный кейс v43: эпизод об огурцах (~600 символов) был в v36,
    исчез в v43. FC отметил ошибку в датировке (90-е vs 70-80-е) как
    confidence_inflation, не legitimate_deletion. GW удалил эпизод
    вместо корректировки. После этого фикса post-validator должен
    блокировать такой revision.
    """
    cucumber_episode = (
        "В советское время Валентина возила огурцы в Молдавию. "
        "Семья жила небогато, и она находила способы дополнительного "
        "заработка. Поездки были регулярными — два-три раза в сезон. "
        "Чемодан огурцов из тверских огородов окупал дорогу с лихвой."
    )
    book_v36_like = _book({"ch_02": "Хроника жизни. " * 200 + cucumber_episode})
    book_v43_like = _book({"ch_02": "Хроника жизни. " * 200})  # эпизод удалён

    fc_with_inflation = _fc_report([
        _err("err_cucumbers",
             type="confidence_inflation",
             severity="major",
             fix_instruction="Заменить «в 90-е годы» на «в советское время».",
             legitimate_deletion=False),
    ])

    passed, details = validate_revision_volume(
        book_v36_like, book_v43_like, fc_report=fc_with_inflation
    )

    assert passed is False, "Регрессия #3 должна блокироваться"
    assert details["verdict"] == "blocked_unauthorized_deletion"
    assert details["drop_chars"] >= len(cucumber_episode) - 50
