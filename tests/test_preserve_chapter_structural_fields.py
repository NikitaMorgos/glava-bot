#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit-тесты для preserve_chapter_structural_fields (Этап 1, task 034).

Защита от регрессии Stage 3 LE: LE v3.0 не описывает в output schema
структурные поля главы (bio_data, timeline, facts_used) → модель их не
возвращает → теряются в book_FINAL_stage3.

v53b: Stage 2 GW v2.16 сгенерировал ch_01.timeline = 6 этапов жизни.
Stage 3 LE v3.0 вернул главу без timeline. Регрессия.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline_utils import preserve_chapter_structural_fields


def _ch(chid: str, content: str = "", **fields) -> dict:
    """Минимальная глава."""
    base = {"id": chid, "content": content}
    base.update(fields)
    return base


def _book(chapters: list[dict]) -> dict:
    return {"chapters": chapters, "callouts": [], "historical_notes": []}


# ──────────────────────────────────────────────────────────────────
# v53b регрессия — главная история
# ──────────────────────────────────────────────────────────────────

def test_v53b_regression_le_dropped_timeline_restored():
    """v53b: GW сгенерировал ch_01.timeline=6 этапов, LE вернул без него."""
    timeline_6 = [
        {"period": "1920–1933", "title": "Детство и сиротство", "text": "Родилась в Мариевке..."},
        {"period": "1938–1945", "title": "Учёба и война", "text": "Фельдшерская школа..."},
        {"period": "1946–1962", "title": "Семья и переезды", "text": "Замужество..."},
        {"period": "1962–1978", "title": "Работа в поликлинике", "text": "Химинститут..."},
        {"period": "1978–1994", "title": "Самостоятельная жизнь", "text": "Вдовство..."},
        {"period": "1994–2005", "title": "Пенсия и старость", "text": "Перевод к дочери..."},
    ]
    bio = {"family": [{"name": "Татьяна", "relation": "дочь"}], "awards": []}

    book_before = _book([
        _ch("ch_01", content="", bio_data=bio, timeline=timeline_6, facts_used=["e1"]),
        _ch("ch_02", content="История жизни...", facts_used=["e1", "e2"]),
    ])
    # LE дропнул timeline и facts_used, изменил content в ch_02
    book_after = _book([
        _ch("ch_01", content=""),  # bio_data, timeline, facts_used пропали
        _ch("ch_02", content="История жизни (стилистически правленая)..."),  # facts_used пропали
    ])

    merged, details = preserve_chapter_structural_fields(book_before, book_after)

    # ch_01: всё восстановлено
    ch01_merged = merged["chapters"][0]
    assert ch01_merged["timeline"] == timeline_6
    assert ch01_merged["bio_data"] == bio
    assert ch01_merged["facts_used"] == ["e1"]

    # ch_02: facts_used восстановлен, content из after
    ch02_merged = merged["chapters"][1]
    assert ch02_merged["content"] == "История жизни (стилистически правленая)..."
    assert ch02_merged["facts_used"] == ["e1", "e2"]

    # Details
    assert details["chapters_with_restored_fields"] == 2
    restored_ids = {r["chapter_id"] for r in details["restorations"]}
    assert restored_ids == {"ch_01", "ch_02"}


def test_le_preserved_all_fields_no_restorations():
    """Happy path: LE послушно вернул все поля — restorations пустой."""
    bio = {"family": [{"name": "X"}]}
    book_before = _book([
        _ch("ch_01", bio_data=bio, timeline=[{"period": "1920"}]),
    ])
    # LE вернул всё включая bio_data + timeline
    book_after = _book([
        _ch("ch_01", bio_data=bio, timeline=[{"period": "1920"}], is_modified=False),
    ])

    merged, details = preserve_chapter_structural_fields(book_before, book_after)

    assert details["chapters_with_restored_fields"] == 0
    assert merged["chapters"][0]["bio_data"] == bio


# ──────────────────────────────────────────────────────────────────
# Mutable fields — LE может их менять
# ──────────────────────────────────────────────────────────────────

def test_content_is_mutable_le_can_change():
    """LE редактирует content — это его работа, не восстанавливаем."""
    book_before = _book([_ch("ch_02", content="Оригинал текста")])
    book_after = _book([_ch("ch_02", content="Отредактированный стилистически текст")])

    merged, _ = preserve_chapter_structural_fields(book_before, book_after)

    assert merged["chapters"][0]["content"] == "Отредактированный стилистически текст"


def test_is_modified_is_mutable():
    """is_modified — LE проставляет true/false."""
    book_before = _book([_ch("ch_02", is_modified=False)])
    book_after = _book([_ch("ch_02", is_modified=True)])

    merged, _ = preserve_chapter_structural_fields(book_before, book_after)

    assert merged["chapters"][0]["is_modified"] is True


def test_paragraphs_is_mutable_le_can_drop():
    """paragraphs — derived field, LE может опустить."""
    paragraphs = [{"id": "p1", "text": "abc"}, {"id": "p2", "text": "def"}]
    book_before = _book([_ch("ch_02", content="abc def", paragraphs=paragraphs)])
    book_after = _book([_ch("ch_02", content="abc def edited")])  # без paragraphs

    merged, details = preserve_chapter_structural_fields(book_before, book_after)

    # paragraphs не восстановлен (он mutable)
    assert "paragraphs" not in merged["chapters"][0]
    # И этого нет в restorations
    ch_resto = next((r for r in details["restorations"] if r["chapter_id"] == "ch_02"), None)
    if ch_resto:
        assert "paragraphs" not in ch_resto["restored_fields"]


def test_custom_mutable_fields():
    """Можно настроить le_mutable_fields tuple."""
    book_before = _book([_ch("ch_02", content="A", title="Old Title")])
    book_after = _book([_ch("ch_02", content="B", title="New Title")])

    # Если title считается mutable — он не восстанавливается
    merged, _ = preserve_chapter_structural_fields(
        book_before, book_after,
        le_mutable_fields=("content", "is_modified", "paragraphs", "title"),
    )
    assert merged["chapters"][0]["title"] == "New Title"


# ──────────────────────────────────────────────────────────────────
# Не-mutable structural fields
# ──────────────────────────────────────────────────────────────────

def test_bio_data_restored_byte_identical():
    """bio_data с нестандартными ключами восстанавливается полностью."""
    bio = {
        "family": [{"name": "А", "relation": "мать"}, {"name": "Б", "relation": "отец"}],
        "awards": [{"name": "Медаль", "year": 1945}],
        "personal": {"birth_year": 1920, "birth_place": "Мариевка"},
        "education": [{"period": "1938-1940", "name": "Школа"}],
        "military": {"years": "1941-1945", "rank": "лейтенант"},
        "timeline": [{"period": "1920"}],
        "custom_field": "preserved",  # любое поле тоже сохраняется
    }
    book_before = _book([_ch("ch_01", bio_data=bio)])
    book_after = _book([_ch("ch_01")])  # bio_data вообще нет

    merged, _ = preserve_chapter_structural_fields(book_before, book_after)

    assert merged["chapters"][0]["bio_data"] == bio
    # Byte-identical: nested структуры тоже совпадают
    assert merged["chapters"][0]["bio_data"]["timeline"][0]["period"] == "1920"


def test_id_title_order_preserved():
    """id, title, order — структурные, восстанавливаются."""
    book_before = _book([
        _ch("ch_02", title="История жизни", order=2),
    ])
    book_after = _book([
        _ch("ch_02", title="ИЗМЕНЁННЫЙ", order=99),
    ])

    merged, _ = preserve_chapter_structural_fields(book_before, book_after)

    assert merged["chapters"][0]["title"] == "История жизни"
    assert merged["chapters"][0]["order"] == 2


def test_facts_used_preserved():
    """facts_used — структурное поле трекинга фактов."""
    book_before = _book([_ch("ch_02", facts_used=["e1", "e2", "e3"])])
    book_after = _book([_ch("ch_02")])  # пропал

    merged, _ = preserve_chapter_structural_fields(book_before, book_after)

    assert merged["chapters"][0]["facts_used"] == ["e1", "e2", "e3"]


# ──────────────────────────────────────────────────────────────────
# Edge cases
# ──────────────────────────────────────────────────────────────────

def test_chapter_only_in_after_no_restoration():
    """Глава которой нет в before — игнорируется (это другой класс проблем)."""
    book_before = _book([_ch("ch_01")])
    book_after = _book([_ch("ch_01"), _ch("ch_new", content="brand new")])

    merged, details = preserve_chapter_structural_fields(book_before, book_after)

    # ch_new остаётся в merged
    assert any(c.get("id") == "ch_new" for c in merged["chapters"])
    # restorations не упоминают ch_new (нечего восстанавливать)
    assert all(r["chapter_id"] != "ch_new" for r in details["restorations"])


def test_chapter_only_in_before_not_added():
    """Глава только в before (LE потерял) — не добавляется автоматически.
    Это другая защита — scope merge (волна 1.3.3) для GW revision."""
    book_before = _book([_ch("ch_01"), _ch("ch_02"), _ch("ch_03")])
    book_after = _book([_ch("ch_01"), _ch("ch_02")])  # ch_03 пропал

    merged, _ = preserve_chapter_structural_fields(book_before, book_after)

    # ch_03 НЕ добавляется (LE не должен терять главы, но это вне scope этого validator)
    ch_ids = {c.get("id") for c in merged["chapters"]}
    assert "ch_03" not in ch_ids


def test_chapter_without_id_skipped():
    """Глава без id — defensive skip."""
    book_before = _book([_ch("ch_01", bio_data={"family": []})])
    book_after = {
        "chapters": [{"content": "no id"}, _ch("ch_01")],
        "callouts": [],
        "historical_notes": [],
    }

    # Не должно упасть
    merged, _ = preserve_chapter_structural_fields(book_before, book_after)
    # ch_01 с bio_data восстановлен
    ch01 = next((c for c in merged["chapters"] if c.get("id") == "ch_01"), None)
    assert ch01 is not None
    assert "bio_data" in ch01


def test_empty_books_no_crash():
    """Пустые books — defensive."""
    merged, details = preserve_chapter_structural_fields(
        {"chapters": []}, {"chapters": []}
    )
    assert merged["chapters"] == []
    assert details["chapters_with_restored_fields"] == 0


# ──────────────────────────────────────────────────────────────────
# Не мутирует входы
# ──────────────────────────────────────────────────────────────────

def test_does_not_mutate_inputs():
    """preserve не модифицирует book_before / book_after."""
    book_before = _book([_ch("ch_01", bio_data={"x": 1}, timeline=[{"period": "1920"}])])
    book_after = _book([_ch("ch_01")])

    before_snap = repr(book_before)
    after_snap = repr(book_after)

    preserve_chapter_structural_fields(book_before, book_after)

    assert repr(book_before) == before_snap
    assert repr(book_after) == after_snap


# ──────────────────────────────────────────────────────────────────
# Details структура
# ──────────────────────────────────────────────────────────────────

def test_details_includes_restoration_diagnostics():
    """Details содержит достаточно информации для аудита."""
    book_before = _book([
        _ch("ch_01", bio_data={"family": []}, timeline=[{"period": "1920"}]),
    ])
    book_after = _book([_ch("ch_01")])

    _, details = preserve_chapter_structural_fields(book_before, book_after)

    assert "le_mutable_fields" in details
    assert "chapters_with_restored_fields" in details
    assert "restorations" in details
    assert details["restorations"][0]["chapter_id"] == "ch_01"
    restored_fields = set(details["restorations"][0]["restored_fields"])
    assert "bio_data" in restored_fields
    assert "timeline" in restored_fields
    assert "reason" in details  # описание для логов


def test_details_no_reason_when_clean():
    """Если ничего не восстановлено — reason отсутствует."""
    book_before = _book([_ch("ch_01")])
    book_after = _book([_ch("ch_01")])

    _, details = preserve_chapter_structural_fields(book_before, book_after)

    assert details["chapters_with_restored_fields"] == 0
    assert "reason" not in details
