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
    """bio_data.family → Markdown.

    Supports both entry formats:
    - pipeline_utils.enforce_bio_data_completeness: {label, value, note, source}
    - pipeline_utils.enforce_bio_data_required_persons: {name, relation, note}

    v62a-044d: skip entries marked in_bio_data_family=False (override entries);
    skip entries where both name/value are empty or label/relation is "?".
    """
    if not family or not isinstance(family, list):
        return []
    lines = []
    seen = set()
    for f in family:
        if isinstance(f, str):
            lines.append(_bullet(f))
            continue
        if not isinstance(f, dict):
            continue
        if f.get("in_bio_data_family") is False:
            continue
        # Skip entries explicitly marked as NOT in family (added by override/required_persons logic)
        note_check = (f.get("note") or "").lower()
        if "не в family" in note_check or "not in family" in note_check:
            continue
        # Support both field-name conventions
        relation = f.get("label") or f.get("relation") or f.get("role") or ""
        name = f.get("value") or f.get("name") or ""
        note = f.get("note") or f.get("detail")
        if not name or not name.strip():
            continue
        if relation.strip() in ("?", "", "-"):
            continue
        relation_label = relation.strip().capitalize() if relation.strip() else "Родственник"
        dedup_key = (relation_label.lower(), name.lower())
        if dedup_key in seen:
            continue
        seen.add(dedup_key)
        if note:
            lines.append(_bullet(f"**{relation_label}** — {name}  _({note})_"))
        else:
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
    # v62a-044d: strip duplicate "## Основные даты жизни" heading from content
    content = (ch01.get("content") or "").strip()
    if content:
        # Remove a leading ## heading that duplicates the section title already rendered above
        import re as _re
        content_clean = _re.sub(
            r'^##\s+(?:Основные\s+даты\s+жизни|[^\n]+)\n*', '', content, count=1
        ).strip()
        if content_clean:
            out.extend(["### Дополнительный текст ch_01", "", content_clean, ""])

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


def _build_summary(book: dict, reports: dict | None = None) -> list[str]:
    """Task 047: расширенная сводка — для быстрого сравнения версий.

    reports: dict с опциональными отчётами:
        - pin_coverage_json: dict
        - style_checks_json: dict
        - chronology_json: dict
        - discourse_markers_json: dict
        - timeline_anchors_json: dict
        - pin_list_depth_json: dict
    """
    import re as _re
    reports = reports or {}
    chapters = book.get("chapters") or []
    callouts = book.get("callouts") or []
    notes = book.get("historical_notes") or []

    total_chars = 0
    per_chapter = []
    for ch in chapters:
        chid = ch.get("id", "?")
        chars = len(ch.get("content") or "")
        per_chapter.append(f"  - **{chid}:** {chars:,} chars".replace(",", " "))
        total_chars += chars

    ch01 = next((c for c in chapters if c.get("id") == "ch_01"), {}) or {}
    bio = ch01.get("bio_data") or {}
    family_count = len(bio.get("family") or [])
    awards_count = len(bio.get("awards") or [])
    timeline_json = bio.get("timeline") or ch01.get("timeline") or []
    timeline_json_count = len(timeline_json)

    # Detect markdown timeline periods in ch_01 content
    ch01_content = ch01.get("content") or ""
    markdown_periods = _re.findall(r'\*\*\d{4}(?:[–\-]\d{4})?\.\s+[^*]+\*\*', ch01_content)
    timeline_md_count = len(markdown_periods)

    # Count inline historical notes (***...*** pattern)
    inline_hist = len(_re.findall(r'\*{3}[^*]+\*{3}', ch01_content))
    for ch in chapters:
        if ch.get("id") == "ch_01":
            continue
        text = ch.get("content") or ""
        inline_hist += len(_re.findall(r'\*{3}[^*]+\*{3}', text))

    # Subsection counts
    ch02 = next((c for c in chapters if c.get("id") == "ch_02"), None)
    ch02_sections = len(_re.findall(r'^##\s+', (ch02 or {}).get("content", ""), _re.MULTILINE)) if ch02 else 0

    out = [
        "# Сводка по книге",
        "",
        "## Объём",
        f"- **Total chars:** {total_chars:,} (target 20K+)".replace(",", " "),
        *per_chapter,
        "",
        "## Структура",
        f"- **Глав:** {len(chapters)} (ch_01..ch_04 + epilogue)",
        f"- **ch_02 подсекций (## headers):** {ch02_sections}",
        "",
        "## Bio_data (паспортичка)",
        f"- **family:** {family_count} записей",
        f"- **awards:** {awards_count} наград",
        f"- **timeline JSON:** {timeline_json_count} периодов" + (" ⚠️ пуст" if timeline_json_count == 0 else ""),
        f"- **timeline markdown (ch_01 bold):** {timeline_md_count} периодов",
        "",
        "## Дополнительные элементы",
        f"- **Callouts:** {len(callouts)}",
        f"- **Historical notes (field):** {len(notes)}" + (" ⚠️" if len(notes) == 0 else ""),
        f"- **Historical notes (inline ***):** {inline_hist}",
        "",
    ]

    # Pin-list coverage
    pin_cov = reports.get("pin_coverage_json") or {}
    if pin_cov and pin_cov.get("summary"):
        s = pin_cov["summary"]
        out += [
            "## Pin-list coverage",
            f"- **Episodes full:** {s.get('full',0)} / {s.get('total',0)}",
            f"- **Episodes partial:** {s.get('partial',0)} / {s.get('total',0)}",
            f"- **Episodes skipped:** {s.get('skipped',0)} / {s.get('total',0)}",
            "",
        ]

    # Quality flags
    quality_lines = ["## Quality flags"]
    style = reports.get("style_checks_json") or {}
    ep_stop = style.get("epilogue_stop_phrases") or {}
    narr_stop = style.get("narrative_stop_phrases") or {}
    chron = reports.get("chronology_json") or {}
    disc = reports.get("discourse_markers_json") or {}
    ta = reports.get("timeline_anchors_json") or {}
    depth = reports.get("pin_list_depth_json") or {}

    def _flag(label, val, ok_val=0, ok_sym="✅", fail_sym="⚠️"):
        sym = ok_sym if val == ok_val else fail_sym
        return f"- {sym} {label}: {val}"

    quality_lines.append(_flag("Epilogue stop phrases errors", ep_stop.get("errors_count", "?"), ok_sym="✅", fail_sym="❌"))
    quality_lines.append(_flag("Narrative stop phrases warnings", narr_stop.get("warnings_count", "?"), ok_sym="✅", fail_sym="⚠️"))
    quality_lines.append(_flag("Chronological consistency errors", chron.get("errors_count", "?"), ok_sym="✅", fail_sym="❌"))
    if disc.get("markers_found"):
        ch02_dm = disc["markers_found"].get("ch_02", 0)
        th_ch02 = disc.get("thresholds", {}).get("ch_02", 8)
        quality_lines.append(f"- {'✅' if ch02_dm >= th_ch02 else '⚠️'} Discourse markers ch_02: {ch02_dm} (min {th_ch02})")
    if ta:
        found = len(ta.get("anchors_found", []))
        total_a = found + len(ta.get("anchors_missing", []))
        src = "markdown" if any(p.get("source") == "markdown" for p in ta.get("anchors_found_details", [{}])) else "json/content"
        quality_lines.append(f"- {'✅' if ta.get('period_count_ok') else '⚠️'} Timeline anchors: {found}/{total_a} found")
    quality_lines.append(_flag("Pin-list depth errors", depth.get("errors_count", "?"), ok_sym="✅", fail_sym="❌"))

    out += quality_lines + ["", "---", ""]
    return out


# ──────────────────────────────────────────────────────────────────
# Task 052c — Contributors section (v62a scripted, pin-list source)
# ──────────────────────────────────────────────────────────────────


def _parse_contributors_from_pin_list(pin_list_path: str | None) -> list[dict]:
    """Parse Contributors table from known_episodes_<subject>.md.

    Reads the markdown table under '## Contributors' section.
    Returns list of {full_name, relation_to_subject, interview_role, notes}.
    """
    if not pin_list_path:
        return []
    import re as _re
    path = Path(pin_list_path)
    if not path.exists():
        print(f"[CONTRIBUTORS] ⚠️ pin-list not found: {pin_list_path}", file=sys.stderr)
        return []

    text = path.read_text(encoding="utf-8")
    # Find the Contributors section — match any ## heading containing "Contributors"
    sec_match = _re.search(
        r'##[^\n]*Contributors[^\n]*\n(.*?)(?=\n##\s|\Z)', text, _re.DOTALL | _re.IGNORECASE
    )
    if not sec_match:
        print("[CONTRIBUTORS] ⚠️ Contributors section not found in pin-list", file=sys.stderr)
        return []

    section_text = sec_match.group(1)
    # Parse markdown table rows: | col1 | col2 | ... |
    rows = []
    header_seen = False
    col_names = []
    for line in section_text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if not header_seen:
            # First row = header
            col_names = [c.lower().replace(" ", "_") for c in cells]
            header_seen = True
            continue
        if all(set(c) <= set("|-: ") for c in cells):
            continue  # separator row
        if len(cells) < 2:
            continue
        row = {}
        for i, name in enumerate(col_names):
            row[name] = cells[i] if i < len(cells) else ""
        rows.append(row)

    contributors = []
    for row in rows:
        full_name = row.get("full_name") or row.get("name") or ""
        if not full_name or full_name == "?":
            continue
        contributors.append({
            "full_name": full_name,
            "relation_to_subject": row.get("relation_to_subject") or row.get("relation") or "",
            "interview_role": row.get("interview_role") or row.get("role") or "",
            "notes": row.get("notes") or "",
        })
    return contributors


def append_contributors_section(lines: list[str], pin_list_path: str | None) -> list[str]:
    """Task 052c: append 'Кто работал над этой Главой' section from pin-list Contributors.

    Pure scripted — no GW involvement. Reads pin-list, renders clean section.
    Returns new list of lines with section appended.
    """
    contributors = _parse_contributors_from_pin_list(pin_list_path)
    if not contributors:
        print("[CONTRIBUTORS] ⚠️ No contributors found — section skipped", file=sys.stderr)
        return lines

    section = [
        "",
        "---",
        "",
        "## Кто работал над этой Главой",
        "",
    ]
    for c in contributors:
        name = c["full_name"]
        parts = []
        if c["relation_to_subject"]:
            parts.append(c["relation_to_subject"])
        if c["interview_role"]:
            parts.append(c["interview_role"])
        detail = ", ".join(parts) if parts else ""
        if detail:
            section.append(f"- **{name}** — {detail}")
        else:
            section.append(f"- **{name}**")
    section.append("")
    print(f"[CONTRIBUTORS] Appended {len(contributors)} contributors from pin-list")
    return lines + section


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


def build_gate1_text(book: dict, fact_map: dict | None = None,
                     reports: dict | None = None,
                     pin_list_path: str | None = None) -> str:
    """Task 047: book_FINAL → Markdown с расширенной сводкой.

    Args:
        book: распакованный book_FINAL (через _unwrap_book)
        fact_map: опционально для fallback bio_data
        reports: dict с отчётами для сводки (pin_coverage_json, style_checks_json, etc.)
        pin_list_path: путь к known_episodes_<subject>.md для Contributors секции (task 052c)

    Returns:
        Markdown текст готовый к чтению.
    """
    lines: list[str] = []

    # 1. Расширенная сводка (task 047)
    lines.extend(_build_summary(book, reports))

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

    # 4. Contributors section (task 052c — scripted from pin-list)
    lines = append_contributors_section(lines, pin_list_path)

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
    parser.add_argument(
        "--reports-dir", default=None,
        help="Task 047: directory with stage3 JSON reports (pin_coverage, style_checks, etc.)"
    )
    parser.add_argument(
        "--prefix", default=None,
        help="Task 047: filename prefix to auto-locate reports in --reports-dir"
    )
    parser.add_argument(
        "--pin-list", default=None,
        help="Task 052c: path to known_episodes_<subject>.md for Contributors section"
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

    # Task 047: load auxiliary reports for extended summary
    reports: dict = {}
    if args.reports_dir and args.prefix:
        _rd = Path(args.reports_dir)
        _report_keys = {
            "pin_coverage_json": f"{args.prefix}_pin_coverage_",
            "style_checks_json": f"{args.prefix}_style_checks_",
            "chronology_json": f"{args.prefix}_chronology_check_",
            "discourse_markers_json": f"{args.prefix}_discourse_markers_",
            "timeline_anchors_json": f"{args.prefix}_timeline_anchors_",
            "pin_list_depth_json": f"{args.prefix}_pin_list_depth_",
        }
        for key, prefix in _report_keys.items():
            _candidates = sorted(_rd.glob(f"{prefix}*.json"))
            if _candidates:
                try:
                    with open(_candidates[-1], encoding="utf-8") as f:
                        reports[key] = json.load(f)
                    print(f"[047] loaded {key}: {_candidates[-1].name}")
                except Exception as e:
                    print(f"[WARN] could not load {key}: {e}", file=sys.stderr)

    md = build_gate1_text(book, fact_map, reports, pin_list_path=args.pin_list)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")

    chars = len(md)
    print(f"[OK] Gate-1 full text -> {out_path} ({chars:,} chars)".replace(",", " "))


if __name__ == "__main__":
    main()
