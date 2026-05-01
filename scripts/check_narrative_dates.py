#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_narrative_dates.py — диагностический скрипт.

Находит ВСЕ упомянутые в нарративе книги годы/периоды/декады,
сверяет с fact_map.timeline. Помечает датировки, которые не имеют
подтверждения в fact_map → потенциальные галлюцинации Ghostwriter.

Это диагностика, не фикс. Цель — понять масштаб проблемы:
единичный случай или паттерн.

Использование:
    python scripts/check_narrative_dates.py \
        --book   <book_FINAL_*.json> \
        --fact-map <fact_map_*.json> \
        [--output <report.json>]
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Iterable

# UTF-8 для Windows-консоли
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ─────────────────────────────────────────────────────────────────
# Извлечение датировок
# ─────────────────────────────────────────────────────────────────

# Конкретный год: 1920, 1933, 1945 (ищем 19XX и 20XX, исключаем номера)
YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2})\b")
# Диапазон: 1920–1933, 1941-1945 (en/em/ascii dash)
RANGE_RE = re.compile(r"\b(19\d{2}|20\d{2})\s*[–—-]\s*(19\d{2}|20\d{2})\b")
# Десятилетие/декада: «90-е», «80-х», «1960-х», «60-е годы»
DECADE_RE = re.compile(r"\b(?:(?:19|20)?\d{2}0)[\-‒–—]?[ехх][\.,\s]?(?:\s*годы?\s*|\s*годах\s*)?", re.IGNORECASE)


def collect_book_paragraphs(book: dict) -> list[tuple[str, str, int, str]]:
    """Возвращает [(chapter_id, chapter_title, paragraph_idx, text), ...]"""
    out = []
    for ch in book.get("chapters", []):
        cid = ch.get("id", "")
        ctitle = ch.get("title", "")
        paras = ch.get("paragraphs") or []
        for i, p in enumerate(paras):
            text = p.get("text", "") if isinstance(p, dict) else str(p)
            if text:
                out.append((cid, ctitle, i, text))
        # Если paragraphs пуст, но есть content
        if not paras and ch.get("content"):
            out.append((cid, ctitle, 0, ch["content"]))
    return out


def collect_callouts_and_notes(book: dict) -> list[tuple[str, str, str]]:
    """Возвращает [(kind, id, text), ...] для callouts и historical_notes."""
    out = []
    for c in book.get("callouts", []):
        out.append(("callout", c.get("id", ""), c.get("text", "")))
    for h in book.get("historical_notes", []):
        text = h.get("text") or h.get("content") or ""
        out.append(("historical_note", h.get("id", ""), text))
    return out


def extract_dates_from_text(text: str) -> dict:
    """Возвращает {'years': [...], 'ranges': [(y1,y2), ...], 'decades': [...]}"""
    dates = {"years": set(), "ranges": set(), "decades": set()}

    # Сначала диапазоны (чтобы не считать 1920 и 1933 в "1920–1933" дважды)
    for m in RANGE_RE.finditer(text):
        y1, y2 = int(m.group(1)), int(m.group(2))
        dates["ranges"].add((y1, y2))

    # Десятилетия
    for m in DECADE_RE.finditer(text):
        dates["decades"].add(m.group(0).strip())

    # Одиночные годы (исключаем те что уже в диапазонах)
    years_in_ranges = set()
    for y1, y2 in dates["ranges"]:
        years_in_ranges.update(range(y1, y2 + 1))
    for m in YEAR_RE.finditer(text):
        y = int(m.group(1))
        if y not in years_in_ranges:
            dates["years"].add(y)

    return {"years": sorted(dates["years"]),
            "ranges": sorted(dates["ranges"]),
            "decades": sorted(dates["decades"])}


# ─────────────────────────────────────────────────────────────────
# Извлечение из fact_map.timeline
# ─────────────────────────────────────────────────────────────────

def collect_factmap_years(fact_map: dict) -> set[int]:
    """Все годы упомянутые в fact_map: timeline.date.year, period диапазоны, character_traits."""
    years = set()

    # timeline events
    for ev in fact_map.get("timeline", []):
        d = ev.get("date") or {}
        if d.get("year"):
            years.add(int(d["year"]))
        # period: "1920-1933" или "ГГГГ"
        period = ev.get("period")
        if isinstance(period, str):
            for m in RANGE_RE.finditer(period):
                y1, y2 = int(m.group(1)), int(m.group(2))
                years.update(range(y1, y2 + 1))
            for m in YEAR_RE.finditer(period):
                years.add(int(m.group(1)))

    # subject birth/death
    subj = fact_map.get("subject", {})
    if subj.get("birth_year"):
        years.add(int(subj["birth_year"]))
    if subj.get("death_year"):
        years.add(int(subj["death_year"]))

    # persons birth/death
    for p in fact_map.get("persons", []):
        for k in ("birth_year", "death_year"):
            if p.get(k):
                try:
                    years.add(int(p[k]))
                except (ValueError, TypeError):
                    pass

    # character_traits.evidence — могут содержать годы
    for t in fact_map.get("character_traits", []):
        ev = t.get("evidence", "") or ""
        for m in YEAR_RE.finditer(ev):
            years.add(int(m.group(1)))

    # quotes
    for q in fact_map.get("quotes", []):
        text = q.get("text", "") or ""
        for m in YEAR_RE.finditer(text):
            years.add(int(m.group(1)))

    return years


def factmap_supports_decade(decade_str: str, factmap_years: set[int]) -> bool:
    """Проверяет: «90-е» поддержано если в fact_map есть год из 1990–1999."""
    # Извлечь десятилетие как число
    m = re.search(r"(\d+)0", decade_str)
    if not m:
        return False
    base = int(m.group(0))
    if base < 100:
        # «90-е» без века — попробуем 1990 и 2090
        candidates = [1900 + base, 2000 + base]
    else:
        candidates = [base]
    for c in candidates:
        for y in range(c, c + 10):
            if y in factmap_years:
                return True
    return False


# ─────────────────────────────────────────────────────────────────
# Главная проверка
# ─────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", required=True)
    ap.add_argument("--fact-map", required=True)
    ap.add_argument("--output", default=None)
    args = ap.parse_args()

    book = json.loads(Path(args.book).read_text(encoding="utf-8"))
    # Stage 3 оборачивает в "book_final"; Stage 2 — без обёртки
    if "book_final" in book and "chapters" not in book:
        book = book["book_final"]
    fact_map = json.loads(Path(args.fact_map).read_text(encoding="utf-8"))

    factmap_years = collect_factmap_years(fact_map)

    issues = []   # подозрительные датировки
    confirmed = []  # подтверждённые

    # 1. Параграфы
    for cid, ctitle, idx, text in collect_book_paragraphs(book):
        d = extract_dates_from_text(text)
        for y in d["years"]:
            entry = {
                "where": f"{cid}.paragraph[{idx}]",
                "type": "year",
                "value": y,
                "in_factmap": y in factmap_years,
                "context": _snippet(text, str(y)),
            }
            (confirmed if entry["in_factmap"] else issues).append(entry)
        for y1, y2 in d["ranges"]:
            both_in = y1 in factmap_years and y2 in factmap_years
            entry = {
                "where": f"{cid}.paragraph[{idx}]",
                "type": "range",
                "value": f"{y1}-{y2}",
                "in_factmap": both_in,
                "context": _snippet(text, f"{y1}"),
            }
            (confirmed if entry["in_factmap"] else issues).append(entry)
        for dec in d["decades"]:
            supported = factmap_supports_decade(dec, factmap_years)
            entry = {
                "where": f"{cid}.paragraph[{idx}]",
                "type": "decade",
                "value": dec,
                "in_factmap": supported,
                "context": _snippet(text, dec.split("-")[0] if "-" in dec else dec[:4]),
            }
            (confirmed if entry["in_factmap"] else issues).append(entry)

    # 2. Callouts и historical_notes (HN исторические — там ожидаемы исторические годы)
    for kind, oid, text in collect_callouts_and_notes(book):
        if kind == "historical_note":
            # Историч. справки могут упоминать события которые НЕ в биографии — это by-design
            continue
        d = extract_dates_from_text(text)
        for y in d["years"]:
            entry = {
                "where": f"{kind}[{oid}]",
                "type": "year",
                "value": y,
                "in_factmap": y in factmap_years,
                "context": _snippet(text, str(y)),
            }
            (confirmed if entry["in_factmap"] else issues).append(entry)

    # ─── Печать отчёта ───
    print(f"\n{'='*70}")
    print(f"  ДАТИРОВКИ В НАРРАТИВЕ — СВЕРКА С FACT_MAP")
    print(f"{'='*70}\n")
    print(f"Fact_map содержит годов: {len(factmap_years)}")
    print(f"  диапазон: {min(factmap_years) if factmap_years else '-'} — {max(factmap_years) if factmap_years else '-'}\n")
    print(f"Найдено датировок в нарративе: {len(confirmed) + len(issues)}")
    print(f"  ✅ подтверждены fact_map: {len(confirmed)}")
    print(f"  ⚠️  НЕ подтверждены:       {len(issues)}\n")

    if issues:
        print(f"{'─'*70}")
        print(f"  ⚠️  ПОТЕНЦИАЛЬНЫЕ ГАЛЛЮЦИНАЦИИ ДАТИРОВКИ")
        print(f"{'─'*70}\n")
        for i, e in enumerate(issues, 1):
            print(f"{i}. [{e['type']}] {e['value']}  @ {e['where']}")
            print(f"   контекст: ...{e['context']}...")
            print()
    else:
        print("✅ Все датировки в нарративе подтверждены fact_map.\n")

    if args.output:
        out = {
            "factmap_years_count": len(factmap_years),
            "factmap_years_min": min(factmap_years) if factmap_years else None,
            "factmap_years_max": max(factmap_years) if factmap_years else None,
            "narrative_dates_total": len(confirmed) + len(issues),
            "confirmed_count": len(confirmed),
            "unconfirmed_count": len(issues),
            "unconfirmed": issues,
            "confirmed": confirmed,
        }
        Path(args.output).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[SAVED] {args.output}")


def _snippet(text: str, marker: str, radius: int = 60) -> str:
    pos = text.find(marker)
    if pos == -1:
        return text[:120]
    s = max(0, pos - radius)
    e = min(len(text), pos + len(marker) + radius)
    return text[s:e].replace("\n", " ")


if __name__ == "__main__":
    main()
