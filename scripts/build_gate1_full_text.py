#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_gate1_full_text.py — детерминированный сборщик продакт-артефакта
для Ворота 1 (текст книги до вёрстки).

Цель: собрать ОДИН Markdown файл из book_FINAL_stage3 + fact_map.bio_data,
который Никита/Даша читают глазами для прохождения чек-листа продуктовых
ворот. Это инфраструктура контроля качества, не часть production пайплайна.

Структура выходного MD:
- ch_01 «Основные даты жизни» — bio_data раскрытый (паспорт, образование,
  военная служба, награды, семья) + timeline (если есть)
- ch_02..ch_04 + epilogue — content из book_FINAL с подзаголовками `##`
- callouts курсивом в конце каждой главы (привязанные к этой главе)
- historical_notes в выделенных блоках с разделителем `***...***`

БЕЗ LLM. БЕЗ внешних API. Только Python json + строковая сборка.

Использование:
    python scripts/build_gate1_full_text.py \\
        --book-final exports/karakulina_v54/karakulina_v54_book_FINAL_stage3_*.json \\
        --output exports/karakulina_v54/karakulina_v54_text_FULL.md

    # Опционально — fact_map для дополнения bio_data:
    python scripts/build_gate1_full_text.py \\
        --book-final ... \\
        --fact-map exports/karakulina_v54a/karakulina_fact_map_*.json \\
        --output ...
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


# ──────────────────────────────────────────────────────────────────
# Helpers — раскрытие bio_data в Markdown
# ──────────────────────────────────────────────────────────────────


def _md_section(title: str, body_lines: list[str], level: int = 4) -> list[str]:
    """Markdown section с заголовком и списком пунктов."""
    if not body_lines:
        return []
    prefix = "#" * level
    return [f"{prefix} {title}", "", *body_lines, ""]


def _bullet(text: str) -> str:
    return f"- {text}"


def _format_personal(personal: dict | None) -> list[str]:
    """bio_data.personal → Markdown."""
    if not personal or not isinstance(personal, dict):
        return []
    lines = []
    full_name = personal.get("full_name") or personal.get("name")
    if full_name:
        maiden = personal.get("maiden_name")
        if maiden:
            lines.append(_bullet(f"**Полное имя** — {full_name} _(девичья фамилия {maiden})_"))
        else:
            lines.append(_bullet(f"**Полное имя** — {full_name}"))
    if birth := personal.get("birth_date") or personal.get("birth_year"):
        place = personal.get("birth_place")
        if place:
            lines.append(_bullet(f"**Дата рождения** — {birth}"))
            lines.append(_bullet(f"**Место рождения** — {place}"))
        else:
            lines.append(_bullet(f"**Дата рождения** — {birth}"))
    if death := personal.get("death_date") or personal.get("death_year"):
        lines.append(_bullet(f"**Дата смерти** — {death}"))
    return _md_section("Личное", lines)


def _format_education(education: list | dict | None) -> list[str]:
    """bio_data.education → Markdown."""
    if not education:
        return []
    items = education if isinstance(education, list) else [education]
    lines = []
    for item in items:
        if not isinstance(item, dict):
            lines.append(_bullet(str(item)))
            continue
        period = item.get("period") or item.get("years") or ""
        name = item.get("name") or item.get("institution") or item.get("title") or ""
        spec = item.get("specialty") or item.get("specialization")
        text_parts = [period] if period else []
        text_parts.append(name)
        if spec:
            text_parts.append(f"специальность {spec}")
        line = " — ".join(filter(None, text_parts[:2])) if len(text_parts) >= 2 else name
        if spec and len(text_parts) >= 2:
            line += f", специальность {spec}"
        lines.append(_bullet(f"**{period}** — {name}" if period else f"**{name}**"))
        if spec:
            lines[-1] += f", специальность {spec}"
    return _md_section("Образование", lines)


def _format_military(military: dict | list | None) -> list[str]:
    """bio_data.military → Markdown."""
    if not military:
        return []
    if isinstance(military, list):
        military = military[0] if military else {}
    if not isinstance(military, dict):
        return []
    lines = []
    if years := military.get("years") or military.get("period"):
        lines.append(_bullet(f"**Годы** — {years}"))
    if rank := military.get("rank"):
        lines.append(_bullet(f"**Звание** — {rank}"))
    if role := military.get("role") or military.get("position"):
        lines.append(_bullet(f"**Должность** — {role}"))
    if fronts := military.get("fronts") or military.get("front"):
        if isinstance(fronts, list):
            fronts = ", ".join(fronts)
        lines.append(_bullet(f"**Фронты** — {fronts}"))
    if unit := military.get("unit"):
        lines.append(_bullet(f"**Часть** — {unit}"))
    return _md_section("Военная служба", lines)


def _format_awards(awards: list | None) -> list[str]:
    """bio_data.awards → Markdown."""
    if not awards or not isinstance(awards, list):
        return []
    lines = []
    for a in awards:
        if isinstance(a, str):
            lines.append(_bullet(a))
            continue
        if not isinstance(a, dict):
            continue
        year = a.get("year") or a.get("date") or ""
        name = a.get("name") or a.get("title") or ""
        if year and name:
            lines.append(_bullet(f"**{year}** — {name}"))
        elif name:
            lines.append(_bullet(name))
    return _md_section("Награды и звания", lines)


def _format_family(family: list | None) -> list[str]:
    """bio_data.family → Markdown."""
    if not family or not isinstance(family, list):
        return []
    lines = []
    for f in family:
        if isinstance(f, str):
            lines.append(_bullet(f))
            continue
        if not isinstance(f, dict):
            continue
        relation = f.get("relation") or f.get("role") or ""
        name = f.get("name") or ""
        note = f.get("note") or f.get("detail")
        relation_label = relation.capitalize() if relation else "Родственник"
        if name and note:
            lines.append(_bullet(f"**{relation_label}** — {name}  _({note})_"))
        elif name:
            lines.append(_bullet(f"**{relation_label}** — {name}"))
    return _md_section("Семья", lines)


def _format_timeline(timeline: list | None) -> list[str]:
    """chapters[ch_01].timeline (или bio_data.timeline) → Markdown."""
    if not timeline or not isinstance(timeline, list):
        return []
    lines = []
    for stage in timeline:
        if not isinstance(stage, dict):
            continue
        period = stage.get("period") or stage.get("years") or ""
        title = stage.get("title") or ""
        text = stage.get("text") or stage.get("description") or ""
        header = f"**{period}** — {title}" if period and title else (title or period)
        if header:
            lines.append(_bullet(header))
        if text:
            lines.append(f"  {text}")
    if not lines:
        return []
    return _md_section("Хронология жизни", lines)


def _render_ch01_bio(book: dict, fact_map: dict | None) -> list[str]:
    """ch_01 — полное раскрытие bio_data + timeline."""
    chapters = book.get("chapters") or []
    ch01 = next((c for c in chapters if c.get("id") == "ch_01"), None)
    if not ch01:
        return ["## Основные даты жизни", "", "_(глава ch_01 отсутствует в book_FINAL)_", ""]

    title = ch01.get("title") or "Основные даты жизни"
    out = [f"## {title}", "", "### Биография в фактах", ""]

    bio = ch01.get("bio_data") or {}
    # Если bio_data в book_FINAL пуст — fallback на fact_map.subject
    if not bio and fact_map:
        subj = fact_map.get("subject") or {}
        if subj:
            bio = {"personal": subj}

    out.extend(_format_personal(bio.get("personal") or fact_map.get("subject") if fact_map else None))
    out.extend(_format_education(bio.get("education")))
    out.extend(_format_military(bio.get("military")))
    out.extend(_format_awards(bio.get("awards")))
    out.extend(_format_family(bio.get("family")))

    # Timeline может быть в bio_data.timeline или прямо в ch_01.timeline
    timeline = bio.get("timeline") or ch01.get("timeline")
    out.extend(_format_timeline(timeline))

    # Если есть content (старый формат) — добавляем как note
    content = (ch01.get("content") or "").strip()
    if content:
        out.extend(["### Дополнительный текст ch_01", "", content, ""])

    return out


# ──────────────────────────────────────────────────────────────────
# Helpers — рендер narrative chapters (ch_02..ch_04, epilogue)
# ──────────────────────────────────────────────────────────────────


def _attach_to_chapter(items: list, chapter_id: str, key_text: str) -> list[dict]:
    """Возвращает items привязанные к chapter_id."""
    if not items:
        return []
    return [
        it for it in items
        if isinstance(it, dict) and it.get("chapter_id") == chapter_id
    ]


def _render_callouts(callouts: list[dict]) -> list[str]:
    """Callouts → Markdown блоки."""
    if not callouts:
        return []
    out = ["", "---", "", "**Цитаты-выноски (callouts):**", ""]
    for c in callouts:
        text = (c.get("text") or "").strip()
        type_ = c.get("type") or ""
        if text:
            label = f" _({type_})_" if type_ else ""
            out.append(f"> _«{text}»_{label}")
            out.append("")
    return out


def _render_historical_notes(notes: list[dict]) -> list[str]:
    """Historical_notes → выделенные блоки."""
    if not notes:
        return []
    out = ["", "---", "", "**Исторические справки:**", ""]
    for n in notes:
        text = (n.get("text") or n.get("content") or "").strip()
        if text:
            out.append(f"***{text}***")
            out.append("")
    return out


def _render_narrative_chapter(ch: dict, callouts: list, hist_notes: list) -> list[str]:
    """ch_02..ch_04 + epilogue → Markdown."""
    chid = ch.get("id", "?")
    title = ch.get("title") or chid
    content = (ch.get("content") or "").strip()

    out = [f"## {title}", "", f"_(id: `{chid}`)_", ""]
    if not content:
        out.append("_(пустое content — возможно деградация Stage 3)_")
        out.append("")
    else:
        # content уже содержит ## подсекции (по спеке GW v2.16)
        out.append(content)
        out.append("")

    # Прикреплённые callouts/notes — после контента главы
    ch_callouts = _attach_to_chapter(callouts, chid, "text")
    out.extend(_render_callouts(ch_callouts))

    ch_notes = _attach_to_chapter(hist_notes, chid, "text")
    out.extend(_render_historical_notes(ch_notes))

    return out


# ──────────────────────────────────────────────────────────────────
# Helpers — статистика для верха документа
# ──────────────────────────────────────────────────────────────────


def _build_summary(book: dict) -> list[str]:
    """Сводная статистика — для быстрого скана."""
    chapters = book.get("chapters") or []
    callouts = book.get("callouts") or []
    notes = book.get("historical_notes") or []

    total_chars = 0
    per_chapter = []
    for ch in chapters:
        chid = ch.get("id", "?")
        chars = len(ch.get("content") or "")
        per_chapter.append(f"  - `{chid}` — {chars:,} chars".replace(",", " "))
        total_chars += chars

    ch01 = next((c for c in chapters if c.get("id") == "ch_01"), {}) or {}
    bio = ch01.get("bio_data") or {}
    family_count = len(bio.get("family") or [])
    awards_count = len(bio.get("awards") or [])
    timeline = bio.get("timeline") or ch01.get("timeline") or []
    timeline_count = len(timeline)

    out = [
        "# Сводка по книге",
        "",
        f"**Глав:** {len(chapters)}",
        f"**Объём текста:** {total_chars:,} chars".replace(",", " "),
        "",
        "**По главам:**",
        *per_chapter,
        "",
        f"**Callouts:** {len(callouts)}",
        f"**Historical notes:** {len(notes)}",
        "",
        f"**bio_data.family:** {family_count} записей",
        f"**bio_data.awards:** {awards_count} наград",
        f"**ch_01 timeline:** {timeline_count} этапов",
        "",
        "---",
        "",
    ]
    return out


# ──────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────


def _unwrap_book(raw: Any) -> dict:
    """book_FINAL может быть обёрнут в book_draft / book_final ключи."""
    if isinstance(raw, str):
        raw = json.loads(raw)
    if not isinstance(raw, dict):
        return {}
    book = raw.get("book_draft", raw)
    if isinstance(book, dict):
        book = book.get("book_final", book)
    if isinstance(book, str):
        book = json.loads(book)
    return book if isinstance(book, dict) else {}


def build_gate1_text(book: dict, fact_map: dict | None = None) -> str:
    """
    Основная функция: book_FINAL → Markdown.

    Args:
        book: распакованный book_FINAL (через _unwrap_book)
        fact_map: опционально для fallback bio_data

    Returns:
        Markdown текст готовый к чтению.
    """
    lines: list[str] = []

    # 1. Сводка
    lines.extend(_build_summary(book))

    # 2. ch_01 паспорт
    lines.extend(_render_ch01_bio(book, fact_map))
    lines.append("---")
    lines.append("")

    # 3. Narrative chapters
    chapters = book.get("chapters") or []
    callouts = book.get("callouts") or []
    notes = book.get("historical_notes") or []

    for ch in chapters:
        if ch.get("id") == "ch_01":
            continue  # уже отрендерили выше
        lines.extend(_render_narrative_chapter(ch, callouts, notes))
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Build single Markdown product artefact from book_FINAL_stage3 "
                    "for Gate-1 product review."
    )
    parser.add_argument(
        "--book-final", required=True,
        help="Path to book_FINAL_stage3_*.json (after Literary Editor + Proofreader)"
    )
    parser.add_argument(
        "--fact-map", default=None,
        help="Optional fact_map_*.json — fallback source for bio_data if missing in book"
    )
    parser.add_argument(
        "--output", required=True,
        help="Output Markdown file path"
    )
    args = parser.parse_args()

    book_path = Path(args.book_final)
    if not book_path.exists():
        print(f"[ERROR] book_final not found: {book_path}", file=sys.stderr)
        sys.exit(1)

    with open(book_path, encoding="utf-8") as f:
        book_raw = json.load(f)
    book = _unwrap_book(book_raw)
    if not book or not book.get("chapters"):
        print(f"[ERROR] book_FINAL has no chapters: {book_path}", file=sys.stderr)
        sys.exit(2)

    fact_map = None
    if args.fact_map:
        fm_path = Path(args.fact_map)
        if fm_path.exists():
            with open(fm_path, encoding="utf-8") as f:
                fact_map = json.load(f)
        else:
            print(f"[WARN] fact_map not found, skipping: {fm_path}", file=sys.stderr)

    md = build_gate1_text(book, fact_map)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")

    chars = len(md)
    print(f"[OK] Gate-1 full text -> {out_path} ({chars:,} chars)".replace(",", " "))


if __name__ == "__main__":
    main()
