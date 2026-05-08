#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit-тесты для merge_revision_out_of_scope_chapters (волна 1.3.3).

Защита от регрессии класса «GW out-of-scope modification при revision»:
v52 показал что FC errors в ch_01/ch_02 → GW v2.15 при revision удалил
ch_03/ch_04/epilogue (52.8% drop). GW v2.15 промпт SCOPE LOCK правило
проигнорировал. merge_revision_out_of_scope_chapters — детерминированная
защита: out-of-scope главы программно копируются из book_before snapshot.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline_utils import merge_revision_out_of_scope_chapters


# ──────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────

def _book(chapters_text: dict[str, str], callouts=None, historical_notes=None) -> dict:
    """Минимальная книга: словарь chapter_id → content. callouts/notes — list[(chapter_id, text)]."""
    return {
        "title": "Test Book",
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


# ──────────────────────────────────────────────────────────────────
# Базовые сценарии
# ──────────────────────────────────────────────────────────────────

def test_happy_path_in_scope_from_after_out_of_scope_from_before():
    """In-scope главы — из book_after, out-of-scope — из book_before."""
    book_before = _book({
        "ch_01": "before ch_01 content",
        "ch_02": "before ch_02 content",
        "ch_03": "before ch_03 content",
    })
    book_after = _book({
        "ch_01": "AFTER ch_01 modified",
        "ch_02": "AFTER ch_02 modified",
        "ch_03": "AFTER ch_03 SHOULD NOT BE TAKEN",
    })

    merged, details = merge_revision_out_of_scope_chapters(
        book_before, book_after, ["ch_01", "ch_02"]
    )

    chapters = {ch["id"]: ch["content"] for ch in merged["chapters"]}
    assert chapters["ch_01"] == "AFTER ch_01 modified"
    assert chapters["ch_02"] == "AFTER ch_02 modified"
    # ch_03 — out of scope, должен быть из book_before
    assert chapters["ch_03"] == "before ch_03 content"

    assert details["scope_enforcement"] == "applied"
    assert len(details["chapters_restored"]) == 1
    assert details["chapters_restored"][0]["chapter_id"] == "ch_03"


def test_v52_regression_gw_emptied_out_of_scope_chapters():
    """v52 точная репродукция: FC errors в ch_01/ch_02, GW снёс ch_03/ch_04/epilogue."""
    book_before = _book({
        "ch_01": "x" * 2000,
        "ch_02": "y" * 3500,
        "ch_03": "z" * 4000,
        "ch_04": "a" * 4500,
        "epilogue": "b" * 1900,
    })
    # GW при revision: оставил ch_01/ch_02 модифицированными,
    # снёс ch_03/ch_04/epilogue (вернул пустые content)
    book_after = _book({
        "ch_01": "x_modified" * 200,
        "ch_02": "y_modified" * 350,
        "ch_03": "",
        "ch_04": "",
        "epilogue": "",
    })

    merged, details = merge_revision_out_of_scope_chapters(
        book_before, book_after, ["ch_01", "ch_02"]
    )

    chapters = {ch["id"]: ch["content"] for ch in merged["chapters"]}
    # In-scope: модифицированный контент сохраняется
    assert chapters["ch_01"] == "x_modified" * 200
    assert chapters["ch_02"] == "y_modified" * 350
    # Out-of-scope: восстановлены из snapshot
    assert chapters["ch_03"] == "z" * 4000
    assert chapters["ch_04"] == "a" * 4500
    assert chapters["epilogue"] == "b" * 1900

    # 3 главы должны быть восстановлены
    restored_ids = {c["chapter_id"] for c in details["chapters_restored"]}
    assert restored_ids == {"ch_03", "ch_04", "epilogue"}

    # Восстановили примерно 4000+4500+1900 = 10400 chars
    assert details["chars_restored"] == 4000 + 4500 + 1900


def test_no_changes_when_gw_respected_scope():
    """Если GW честно не трогал out-of-scope — restored список пустой."""
    book_before = _book({
        "ch_01": "before ch_01",
        "ch_02": "before ch_02",
        "ch_03": "untouched ch_03",
    })
    book_after = _book({
        "ch_01": "after ch_01 modified",
        "ch_02": "after ch_02 modified",
        "ch_03": "untouched ch_03",  # byte-identical
    })

    merged, details = merge_revision_out_of_scope_chapters(
        book_before, book_after, ["ch_01", "ch_02"]
    )

    assert details["scope_enforcement"] == "applied"
    assert details["chapters_restored"] == []
    assert details["chars_restored"] == 0
    chapters = {ch["id"]: ch["content"] for ch in merged["chapters"]}
    assert chapters["ch_03"] == "untouched ch_03"


def test_all_chapters_in_scope_returns_after_as_is():
    """Если все главы in scope — merged == book_after."""
    book_before = _book({"ch_01": "old1", "ch_02": "old2"})
    book_after = _book({"ch_01": "new1", "ch_02": "new2"})

    merged, details = merge_revision_out_of_scope_chapters(
        book_before, book_after, ["ch_01", "ch_02"]
    )

    chapters = {ch["id"]: ch["content"] for ch in merged["chapters"]}
    assert chapters == {"ch_01": "new1", "ch_02": "new2"}
    assert details["chapters_restored"] == []


# ──────────────────────────────────────────────────────────────────
# Edge cases
# ──────────────────────────────────────────────────────────────────

def test_empty_affected_chapters_returns_after_unchanged():
    """affected_chapters=[] — нет защиты. Возвращаем book_after as-is."""
    book_before = _book({"ch_01": "old"})
    book_after = _book({"ch_01": "new"})

    merged, details = merge_revision_out_of_scope_chapters(book_before, book_after, [])

    assert details["scope_enforcement"] == "skipped"
    assert details["reason"] == "no_scope_provided"
    chapters = {ch["id"]: ch["content"] for ch in merged["chapters"]}
    assert chapters["ch_01"] == "new"


def test_none_affected_chapters_returns_after_unchanged():
    """affected_chapters=None — то же что []."""
    book_before = _book({"ch_01": "old"})
    book_after = _book({"ch_01": "new"})

    merged, details = merge_revision_out_of_scope_chapters(book_before, book_after, None)

    assert details["scope_enforcement"] == "skipped"
    chapters = {ch["id"]: ch["content"] for ch in merged["chapters"]}
    assert chapters["ch_01"] == "new"


def test_in_scope_chapter_missing_in_after_restored_from_before():
    """Глава из affected_chapters отсутствует в book_after — восстанавливаем."""
    book_before = _book({
        "ch_01": "before ch_01",
        "ch_02": "before ch_02",
    })
    # GW потерял ch_02 (вообще убрал из chapters)
    book_after = _book({"ch_01": "after ch_01"})

    merged, details = merge_revision_out_of_scope_chapters(
        book_before, book_after, ["ch_01", "ch_02"]
    )

    chapters = {ch["id"]: ch["content"] for ch in merged["chapters"]}
    assert chapters == {"ch_01": "after ch_01", "ch_02": "before ch_02"}
    # ch_02 восстановлен с reason=in_scope_but_missing_in_after
    restored = next(c for c in details["chapters_restored"] if c["chapter_id"] == "ch_02")
    assert restored["reason"] == "in_scope_but_missing_in_after"


def test_new_in_scope_chapter_added_at_end():
    """Новая глава в book_after которой не было в before, в scope — добавляется."""
    book_before = _book({"ch_01": "before"})
    book_after = _book({"ch_01": "after", "ch_new": "brand new"})

    merged, _ = merge_revision_out_of_scope_chapters(
        book_before, book_after, ["ch_01", "ch_new"]
    )

    chapter_ids = [ch["id"] for ch in merged["chapters"]]
    assert chapter_ids == ["ch_01", "ch_new"]


def test_new_out_of_scope_chapter_dropped():
    """Новая глава вне scope — отбрасывается (GW не должен был её добавлять)."""
    book_before = _book({"ch_01": "before"})
    book_after = _book({"ch_01": "after", "ch_extra": "should not appear"})

    merged, details = merge_revision_out_of_scope_chapters(
        book_before, book_after, ["ch_01"]
    )

    chapter_ids = [ch["id"] for ch in merged["chapters"]]
    assert chapter_ids == ["ch_01"]
    assert len(details["new_out_of_scope_dropped"]) == 1
    assert details["new_out_of_scope_dropped"][0]["chapter_id"] == "ch_extra"


def test_chapter_order_preserved_from_before():
    """Порядок глав сохраняется как в book_before."""
    book_before = _book({
        "ch_01": "1", "ch_02": "2", "ch_03": "3", "ch_04": "4", "ch_05": "5",
    })
    # GW мог переупорядочить главы
    book_after = {
        "title": "Test Book",
        "chapters": [
            {"id": "ch_03", "content": "3-changed"},
            {"id": "ch_01", "content": "1-changed"},
            {"id": "ch_02", "content": "2-changed"},
            {"id": "ch_04", "content": "4-changed"},
            {"id": "ch_05", "content": "5-changed"},
        ],
        "callouts": [],
        "historical_notes": [],
    }

    merged, _ = merge_revision_out_of_scope_chapters(
        book_before, book_after, ["ch_01", "ch_02", "ch_03"]
    )

    # Порядок должен быть из before
    chapter_ids = [ch["id"] for ch in merged["chapters"]]
    assert chapter_ids == ["ch_01", "ch_02", "ch_03", "ch_04", "ch_05"]


# ──────────────────────────────────────────────────────────────────
# callouts / historical_notes
# ──────────────────────────────────────────────────────────────────

def test_callout_out_of_scope_chapter_restored():
    """Callout привязанный к out-of-scope главе — восстанавливается из before."""
    book_before = _book(
        {"ch_01": "1", "ch_02": "2", "ch_03": "3"},
        callouts=[("ch_03", "callout for ch_03")],
    )
    # GW удалил callout привязанный к ch_03 (out of scope)
    book_after = _book(
        {"ch_01": "1-mod", "ch_02": "2-mod", "ch_03": "3"},
        callouts=[],
    )

    merged, details = merge_revision_out_of_scope_chapters(
        book_before, book_after, ["ch_01", "ch_02"]
    )

    callouts = merged["callouts"]
    callout_chapters = [c["chapter_id"] for c in callouts]
    assert "ch_03" in callout_chapters
    ch03_callout = next(c for c in callouts if c["chapter_id"] == "ch_03")
    assert ch03_callout["text"] == "callout for ch_03"
    assert details["callouts_restored"] >= 1


def test_callout_in_scope_chapter_passes_through_from_after():
    """Callout привязанный к in-scope главе — берётся из after (GW мог изменить)."""
    book_before = _book(
        {"ch_01": "1", "ch_02": "2"},
        callouts=[("ch_02", "old callout")],
    )
    book_after = _book(
        {"ch_01": "1-mod", "ch_02": "2-mod"},
        callouts=[("ch_02", "NEW callout text")],
    )

    merged, _ = merge_revision_out_of_scope_chapters(
        book_before, book_after, ["ch_01", "ch_02"]
    )

    ch02_callouts = [c for c in merged["callouts"] if c["chapter_id"] == "ch_02"]
    assert len(ch02_callouts) == 1
    assert ch02_callouts[0]["text"] == "NEW callout text"


def test_callout_without_chapter_id_passes_through():
    """Глобальный callout (без chapter_id) — pass-through из after."""
    book_before = {
        "title": "T",
        "chapters": [{"id": "ch_01", "content": "1"}],
        "callouts": [{"id": "co_global", "text": "old global"}],
        "historical_notes": [],
    }
    book_after = {
        "title": "T",
        "chapters": [{"id": "ch_01", "content": "1-mod"}],
        "callouts": [{"id": "co_global", "text": "NEW global"}],
        "historical_notes": [],
    }

    merged, _ = merge_revision_out_of_scope_chapters(
        book_before, book_after, ["ch_01"]
    )

    global_callouts = [c for c in merged["callouts"] if "chapter_id" not in c]
    assert len(global_callouts) == 1
    assert global_callouts[0]["text"] == "NEW global"


def test_historical_notes_out_of_scope_restored():
    """historical_note для out-of-scope главы — восстанавливается."""
    book_before = _book(
        {"ch_01": "1", "ch_02": "2", "ch_03": "3"},
        historical_notes=[("ch_03", "WWII context for ch_03")],
    )
    book_after = _book(
        {"ch_01": "1-mod", "ch_02": "2-mod", "ch_03": "3"},
        historical_notes=[],
    )

    merged, details = merge_revision_out_of_scope_chapters(
        book_before, book_after, ["ch_01", "ch_02"]
    )

    notes = merged["historical_notes"]
    assert any(n.get("chapter_id") == "ch_03" for n in notes)
    assert details["historical_notes_restored"] >= 1


# ──────────────────────────────────────────────────────────────────
# Top-level fields preserved
# ──────────────────────────────────────────────────────────────────

def test_top_level_fields_preserved_from_after():
    """Title и другие top-level поля — pass-through из book_after (GW мог изменить)."""
    book_before = _book({"ch_01": "1"})
    book_before["title"] = "Old Title"
    book_after = _book({"ch_01": "1-mod"})
    book_after["title"] = "New Title"
    book_after["bio_data"] = {"family": ["Alice"]}

    merged, _ = merge_revision_out_of_scope_chapters(
        book_before, book_after, ["ch_01"]
    )

    assert merged["title"] == "New Title"
    assert merged.get("bio_data") == {"family": ["Alice"]}


# ──────────────────────────────────────────────────────────────────
# Details / diagnostics
# ──────────────────────────────────────────────────────────────────

def test_details_chars_after_merged_correctly_calculated():
    """chars_after_merged отражает финальный объём после merge."""
    book_before = _book({"ch_01": "x" * 100, "ch_02": "y" * 200})
    book_after = _book({"ch_01": "x" * 150, "ch_02": ""})

    merged, details = merge_revision_out_of_scope_chapters(
        book_before, book_after, ["ch_01"]
    )

    # ch_01 после = 150, ch_02 восстановлен = 200
    assert details["chars_after_merged"] == 150 + 200
    # chars_after_gw = только то что вернул GW
    assert details["chars_after_gw"] == 150
    # chars_before_total = объём snapshot
    assert details["chars_before_total"] == 100 + 200


def test_details_lists_specific_restored_chapter_ids():
    """В details.chapters_restored явно перечислены chapter_ids."""
    book_before = _book({
        "ch_01": "1", "ch_02": "2", "ch_03": "3", "ch_04": "4",
    })
    book_after = _book({
        "ch_01": "1-mod", "ch_02": "2", "ch_03": "MODIFIED-WRONG", "ch_04": "",
    })

    _, details = merge_revision_out_of_scope_chapters(
        book_before, book_after, ["ch_01"]
    )

    restored_ids = {c["chapter_id"] for c in details["chapters_restored"]}
    # ch_02: byte-identical с before (не модифицировано) — не должно быть в restored
    # ch_03: модифицирован (out-of-scope) — должно быть в restored
    # ch_04: удалён (empty) — должно быть в restored
    assert "ch_03" in restored_ids
    assert "ch_04" in restored_ids
    assert "ch_02" not in restored_ids


def test_no_chapter_id_chapters_skipped_safely():
    """Главы без id не ломают merge (defensive)."""
    book_before = {
        "title": "T",
        "chapters": [
            {"id": "ch_01", "content": "1"},
            {"content": "no_id_chapter"},  # no id
        ],
        "callouts": [],
        "historical_notes": [],
    }
    book_after = {
        "title": "T",
        "chapters": [{"id": "ch_01", "content": "1-mod"}],
        "callouts": [],
        "historical_notes": [],
    }

    # Не должно упасть
    merged, _ = merge_revision_out_of_scope_chapters(
        book_before, book_after, ["ch_01"]
    )
    chapter_ids = [ch.get("id") for ch in merged["chapters"]]
    assert "ch_01" in chapter_ids


# ──────────────────────────────────────────────────────────────────
# Изоляция: merge не мутирует входы
# ──────────────────────────────────────────────────────────────────

def test_merge_does_not_mutate_inputs():
    """merge возвращает новый объект, не модифицирует book_before/book_after."""
    book_before = _book({"ch_01": "1", "ch_02": "2"})
    book_after = _book({"ch_01": "1-mod", "ch_02": ""})

    before_snapshot = repr(book_before)
    after_snapshot = repr(book_after)

    merge_revision_out_of_scope_chapters(book_before, book_after, ["ch_01"])

    assert repr(book_before) == before_snapshot
    assert repr(book_after) == after_snapshot
