#!/usr/bin/env python3
"""Анализ v55: split-extract diagnostics и task 035/036 checklist."""
import json
import re
import sys
from pathlib import Path

ROOT = Path("/opt/glava")

# fact_map_full
fm_path = sorted((ROOT / "exports/karakulina_v55").glob("karakulina_fact_map_full_*.json"))[-1]
_tr1_paths = sorted((ROOT / "exports/karakulina_v55").glob("karakulina_fact_map_TR1_*.json"))
fm_tr1_path = _tr1_paths[-1] if _tr1_paths else None
book_s3_path = sorted((ROOT / "exports/stage3_v55").glob("karakulina_v55_book_FINAL_stage3_*.json"))[-1]
pres_path = sorted((ROOT / "exports/stage3_v55").glob("karakulina_v55_le_structural_preservation_*.json"))[-1]
text_path = ROOT / "collab/runs/karakulina_v55/karakulina_v55_text_FULL.md"

fm = json.loads(fm_path.read_text("utf-8"))
timeline = fm.get("timeline", [])
persons = fm.get("persons", [])

print("=" * 60)
print("SPLIT-EXTRACT DIAGNOSTICS")
print("=" * 60)
print(f"fact_map_full: {fm_path.name}")
print(f"  timeline events: {len(timeline)}")
print(f"  persons:         {len(persons)}")

if fm_tr1_path:
    fm_tr1 = json.loads(fm_tr1_path.read_text("utf-8"))
    tl1 = fm_tr1.get("timeline", [])
    p1 = fm_tr1.get("persons", [])
    print(f"\nfact_map_TR1 (Phase A): {fm_tr1_path.name}")
    print(f"  timeline events: {len(tl1)}")
    print(f"  persons:         {len(p1)}")
    tr2_events_count = len(timeline) - len(tl1)
    tr2_persons_count = len(persons) - len(p1)
    print(f"\nPhase B (TR2) добавил: events={max(tr2_events_count,0)}, persons={max(tr2_persons_count,0)}")
else:
    print("  (fact_map_TR1 не найден)")

# Маркеры эпизодов в fact_map
print()
print("─" * 40)
print("МАРКЕРЫ В fact_map_full (timeline):")
markers = {
    "огурцы Молдавия": ["огурц", "молдав"],
    "счётчик 1977":    ["счётчик", "счетчик"],
    "Нинвана":         ["нинван"],
    "шарлотка":        ["шарлотк"],
    "Соседка тётя Маша":["маша", "соседк"],
}
for name, kws in markers.items():
    found_events = [
        e for e in timeline
        if any(kw.lower() in (e.get("title","") + " " + e.get("description","")).lower() for kw in kws)
    ]
    if found_events:
        for fe in found_events:
            pb = fe.get("phase_b_source", False)
            print(f"  ✅ {name}: [{fe.get('id')}] \"{fe.get('title','')[:50]}\" (phase_b={pb})")
    else:
        print(f"  ❌ {name}: ОТСУТСТВУЕТ в timeline")

# Персоны из TR2
print()
print("─" * 40)
print("ПЕРСОНЫ phase_b_source в persons[]:")
pb_persons = [p for p in persons if p.get("phase_b_source") or p.get("source") == "phase_b"]
for p in pb_persons:
    print(f"  [{p.get('id')}] {p.get('name')} — {p.get('relation_to_subject','')}")
if not pb_persons:
    print("  (Нет персон с пометкой phase_b_source — маркировка не реализована или всё вмержено)")

# book_FINAL_stage3 checks
print()
print("=" * 60)
print("BOOK_FINAL_STAGE3 CHECKLIST")
print("=" * 60)
book = json.loads(book_s3_path.read_text("utf-8"))
book_inner = book.get("book_final", book)
chapters = book_inner.get("chapters", [])
full_text = " ".join(ch.get("content","") for ch in chapters).lower()

task035_items = [
    ("Огурцы Молдавия 1990", ["огурц", "молдав"]),
    ("Счётчик 1977",          ["счётчик", "счетчик"]),
    ("Нинвана Полсачева",     ["нинван"]),
    ("Шарлотка",              ["шарлотк"]),
]
print("task 035 (TR2 эпизоды в книге):")
passed = 0
for name, kws in task035_items:
    found = any(kw in full_text for kw in kws)
    print(f"  {'✅' if found else '❌'} {name}")
    passed += found
print(f"  Итого: {passed}/4")

task036_char = [
    ("выковыривал",           ["выковыривал"]),
    ("зарубиться на пустом",  ["зарубиться"]),
    ("зажиточные ребята",     ["зажиточн"]),
    ("движуха",               ["движух"]),
    ("рукастый",              ["рукаст"]),
]
print("\ntask 036 — characteristic words (нужно ≥3):")
cw_count = 0
for name, kws in task036_char:
    found = any(kw in full_text for kw in kws)
    print(f"  {'✅' if found else '❌'} {name}")
    cw_count += found
print(f"  Итого characteristic words: {cw_count}/5 {'✅' if cw_count >= 3 else '❌'}")

stop_phrases = [
    ("болью отозвалось", ["болью отозвалось"]),
    ("трагически",       ["трагически"]),
]
print("\ntask 036 — СТОП-фразы (должны отсутствовать):")
for name, kws in stop_phrases:
    found = any(kw in full_text for kw in kws)
    status = "❌ НАЙДЕНО (BAD)" if found else "✅ OK (absent)"
    print(f"  {status} — {name}")

zapret9 = re.findall(r'\w+ по \w+, \w+, \w+', full_text)
print(f"\ntask 036 ЗАПРЕТ 9 (X по Y, Z, W): {'❌ ' + str(zapret9[:2]) if zapret9 else '✅ OK'}")

# ch_04 первый абзац
ch04 = next((ch for ch in chapters if ch.get("id") == "ch_04" or ch.get("chapter_id") == "ch_04"), None)
if ch04:
    first_para = ch04.get("content","").strip().split("\n\n")[0][:200]
    print(f"\nch_04 первый абзац (ЗАПРЕТ 8):")
    print(f"  {first_para!r}")
    plastic_markers = ["жизнь", "важн", "определил", "формировал", "непростой", "судьб"]
    has_concrete = any(c.isdigit() for c in first_para)  # года/цифры = конкретность
    has_name = any(n in first_para.lower() for n in ["каракулин", "валентин", "таня", "татьян"])
    print(f"  Конкретность: {'✅ (имя/год найдены)' if has_concrete or has_name else '❌ (только абстракции?)'}")

# ch_01 timeline
ch01 = next((ch for ch in chapters if ch.get("id") == "ch_01" or ch.get("chapter_id") == "ch_01"), None)
if ch01:
    tl = ch01.get("timeline", [])
    print(f"\nch_01 timeline[] (структурное): {len(tl)} этапов {'✅' if tl else '❌ (пустой)'}")

# LE structural preservation
print()
print("=" * 60)
print("LE STRUCTURAL PRESERVATION")
print("=" * 60)
pres = json.loads(pres_path.read_text("utf-8"))
restored_chs = pres.get("chapters_with_restored_fields", [])
restorations = pres.get("restorations", [])
if isinstance(restored_chs, list):
    print(f"chapters_with_restored_fields: {len(restored_chs)} — {restored_chs}")
else:
    print(f"chapters_with_restored_fields: {restored_chs}")
for r in restorations:
    print(f"  {r.get('chapter_id')}: restored={r.get('restored_fields')}")
if not restorations:
    print("  (нет восстановлений — LE держит структуру ✅)")

# text_FULL summary
if text_path.exists():
    text_full = text_path.read_text("utf-8")
    print()
    print("=" * 60)
    print("text_FULL.md summary:")
    for line in text_full.split("\n")[:30]:
        print(f"  {line}")
else:
    print("\ntext_FULL.md: не найден")

print("\n✅ Анализ завершён")
