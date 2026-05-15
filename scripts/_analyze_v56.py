#!/usr/bin/env python3
"""v56 полный чек-лист: pin-list CA v1.2, task 035/036, огурцы-цитата, char words."""
import json
import re
import sys
from pathlib import Path

ROOT = Path("/opt/glava")
V = "v56"
S1_DIR = ROOT / f"exports/karakulina_{V}"
S2_DIR = ROOT / f"exports/stage2_{V}"
S3_DIR = ROOT / f"exports/stage3_{V}"
RUNS_DIR = ROOT / f"collab/runs/karakulina_{V}"

def latest(directory, pattern):
    matches = sorted(directory.glob(pattern))
    return matches[-1] if matches else None

fm_path   = latest(S1_DIR, "karakulina_fact_map_full_*.json")
fm_tr1    = latest(S1_DIR, "karakulina_fact_map_TR1_*.json")
audit_path = latest(S1_DIR, "karakulina_completeness_audit_*.json")
book_s3   = latest(S3_DIR, f"{V}_book_FINAL_stage3_*.json") or latest(S3_DIR, f"karakulina_{V}_book_FINAL_stage3_*.json")
pres_path = latest(S3_DIR, f"karakulina_{V}_le_structural_preservation_*.json")
text_path = RUNS_DIR / f"karakulina_{V}_text_FULL.md"

for label, p in [("fact_map_full", fm_path), ("audit", audit_path), ("book_s3", book_s3), ("preservation", pres_path)]:
    if not p or not p.exists():
        print(f"[WARN] {label} not found ({p})")

print("=" * 60)
print(f"v56 SPLIT-EXTRACT + PIN-LIST DIAGNOSTICS")
print("=" * 60)

if fm_path and fm_path.exists():
    fm = json.loads(fm_path.read_text("utf-8"))
    timeline = fm.get("timeline", [])
    persons  = fm.get("persons", [])
    print(f"fact_map_full: {fm_path.name}")
    print(f"  timeline: {len(timeline)} events  |  persons: {len(persons)}")

if fm_tr1 and fm_tr1.exists():
    fm1 = json.loads(fm_tr1.read_text("utf-8"))
    t1  = fm1.get("timeline", [])
    p1  = fm1.get("persons", [])
    print(f"fact_map_TR1:  {fm_tr1.name}")
    print(f"  timeline: {len(t1)} events  |  persons: {len(p1)}")
    print(f"Phase B added: +{len(timeline)-len(t1)} events, +{len(persons)-len(p1)} persons")

# ── CA v1.2 pin-list результаты ──────────────────────────────────────────────
print()
print("=" * 60)
print("CA v1.2 PIN-LIST РЕЗУЛЬТАТЫ")
print("=" * 60)
if audit_path and audit_path.exists():
    audit = json.loads(audit_path.read_text("utf-8"))
    ae = audit.get("auto_enrich", {})
    ae_tl = ae.get("timeline", [])
    ae_ps = ae.get("persons", [])
    pin_tl = [e for e in ae_tl if e.get("was_in_pin_list")]
    pin_ps = [p for p in ae_ps if p.get("was_in_pin_list")]
    new_tl = [e for e in ae_tl if not e.get("was_in_pin_list")]
    new_ps = [p for p in ae_ps if not p.get("was_in_pin_list")]

    print(f"auto_enrich.timeline: {len(ae_tl)} events")
    print(f"  был в pin-list (was_in_pin_list=true): {len(pin_tl)}")
    print(f"  новых (не из pin-list): {len(new_tl)}")
    for e in pin_tl:
        sq = e.get("source_quote", "")[:80]
        print(f"  [PIN✅] {e.get('id')} «{e.get('title','')}»")
        print(f"         цитата: {sq!r}")
    for e in new_tl:
        print(f"  [NEW]  {e.get('id')} «{e.get('title','')}»")

    print(f"\nauto_enrich.persons: {len(ae_ps)} persons")
    print(f"  был в pin-list: {len(pin_ps)}")
    for p in pin_ps:
        print(f"  [PIN✅] {p.get('id')} {p.get('name')} — {p.get('relation_to_subject','')}")
    for p in new_ps:
        print(f"  [NEW]  {p.get('id')} {p.get('name')} — {p.get('relation_to_subject','')}")

    lop = audit.get("log_only_gaps", {})
    me  = lop.get("missing_events", [])
    pin_me = [e for e in me if e.get("was_in_pin_list")]
    print(f"\nlog_only_gaps.missing_events: {len(me)} ({len(pin_me)} was_in_pin_list)")
    for e in pin_me:
        print(f"  [MISS-PIN] {e.get('keyword','')!r} — {e.get('reason_low_confidence','')[:70]}")
    print(f"\nprocessing_notes: {audit.get('processing_notes', {}).get('summary','')[:120]}")
else:
    print("(audit file not found)")

# ── BOOK_FINAL_STAGE3 ЧЕКЛИСТ ────────────────────────────────────────────────
print()
print("=" * 60)
print("BOOK_FINAL_STAGE3 ЧЕК-ЛИСТ (task 035 + 036 + Этап 1)")
print("=" * 60)

if book_s3 and book_s3.exists():
    book = json.loads(book_s3.read_text("utf-8"))
    book_inner = book.get("book_final", book)
    chapters = book_inner.get("chapters", [])
    full_text = " ".join(ch.get("content","") for ch in chapters)
    full_lower = full_text.lower()

    # 1. Огурцы — с точной цитатой
    print("\n1. Огурцы Молдавия 1990:")
    ogurcy_found = "огурц" in full_lower or "молдав" in full_lower
    if ogurcy_found:
        idx = full_lower.find("огурц") if "огурц" in full_lower else full_lower.find("молдав")
        citation = full_text[max(0,idx-100):idx+200].strip()
        print(f"   ✅ НАЙДЕНЫ")
        print(f"   Цитата: «...{citation}...»")
        # Проверяем на искажение (инверсию — негативный контекст к позитивному событию)
        context_window = full_text[max(0,idx-150):idx+250].lower()
        inversion_markers = ["тяжело", "горько", "к сожален", "несмотря", "хотя", "однако", "трагич", "боль", "потерял"]
        inversions = [m for m in inversion_markers if m in context_window]
        if inversions:
            print(f"   ⚠️  ВОЗМОЖНОЕ ИСКАЖЕНИЕ: найдены маркеры {inversions}")
        else:
            print(f"   ✅ Искажений не обнаружено в контексте")
    else:
        print("   ❌ ОТСУТСТВУЮТ")

    # 2. Счётчик 1977
    print("\n2. Счётчик 1977:")
    if "счётчик" in full_lower or "счетчик" in full_lower:
        idx = full_lower.find("счётчик") if "счётчик" in full_lower else full_lower.find("счетчик")
        cit = full_text[max(0,idx-60):idx+120].strip()
        print(f"   ✅ НАЙДЕН: «...{cit}...»")
    else:
        print("   ❌ ОТСУТСТВУЕТ")

    # 3. Нинвана
    print("\n3. Нинвана Полсачева:")
    if "нинван" in full_lower:
        idx = full_lower.find("нинван")
        cit = full_text[max(0,idx-60):idx+100].strip()
        print(f"   ✅ НАЙДЕНА: «...{cit}...»")
    else:
        print("   ❌ ОТСУТСТВУЕТ")

    # 4. Шарлотка
    print("\n4. Шарлотка:")
    if "шарлотк" in full_lower:
        idx = full_lower.find("шарлотк")
        cit = full_text[max(0,idx-60):idx+100].strip()
        print(f"   ✅ НАЙДЕНА: «...{cit}...»")
    else:
        print("   ❌ ОТСУТСТВУЕТ")

    # 5. Characteristic words (task 036)
    char_words = [
        ("выковыривал",         ["выковыривал"]),
        ("зарубиться на пустом",["зарубиться"]),
        ("зажиточные ребята",   ["зажиточн"]),
        ("движуха",             ["движух"]),
        ("рукастый",            ["рукаст"]),
    ]
    print("\n5. Characteristic words (task 036, нужно ≥3):")
    cw_count = 0
    for name, kws in char_words:
        found = any(kw in full_lower for kw in kws)
        cw_count += found
        print(f"   {'✅' if found else '❌'} {name}")
    verdict = "✅ PASS" if cw_count >= 3 else "❌ FAIL"
    print(f"   Итого: {cw_count}/5  {verdict}")

    # СТОП-фразы
    print("\n   СТОП-фразы:")
    for phrase in ["болью отозвалось", "трагически"]:
        found = phrase in full_lower
        print(f"   {'❌ НАЙДЕНО (BAD)' if found else '✅ OK (absent)'} — {phrase!r}")

    # 6. ch_04 первый абзац
    print("\n6. ch_04 первый абзац (ЗАПРЕТ 8):")
    ch04 = next((ch for ch in chapters if ch.get("id") in ("ch_04","chapter_4")), None)
    if ch04:
        para = ch04.get("content","").strip().split("\n\n")[0]
        print(f"   «{para[:250]}»")
        has_concrete = any(c.isdigit() for c in para[:100])
        print(f"   {'✅ конкретный (год/цифра)' if has_concrete else '❌ абстрактный'}")
    else:
        print("   (ch_04 не найдена)")

    # ch_01 timeline структурное
    ch01 = next((ch for ch in chapters if ch.get("id") in ("ch_01","chapter_1")), None)
    if ch01:
        tl01 = ch01.get("timeline", [])
        print(f"\n   ch_01 timeline[]: {len(tl01)} этапов {'✅' if tl01 else '❌ (пустой)'}")

# ── LE STRUCTURAL PRESERVATION ───────────────────────────────────────────────
print()
print("=" * 60)
print("LE STRUCTURAL PRESERVATION")
print("=" * 60)
if pres_path and pres_path.exists():
    pres = json.loads(pres_path.read_text("utf-8"))
    rc = pres.get("chapters_with_restored_fields")
    restorations = pres.get("restorations", [])
    print(f"chapters_with_restored_fields: {rc}")
    for r in restorations:
        print(f"  {r.get('chapter_id')}: {r.get('restored_fields')}")
    if not restorations:
        print("  ✅ LE держит структуру (нет восстановлений)")
else:
    print("(файл не найден)")

# ── text_FULL summary ────────────────────────────────────────────────────────
print()
print("=" * 60)
print("text_FULL.md (первые 25 строк)")
print("=" * 60)
if text_path.exists():
    lines = text_path.read_text("utf-8").split("\n")
    for line in lines[:25]:
        print(f"  {line}")
else:
    print("(text_FULL.md не найден)")

print(f"\n✅ Анализ v56 завершён")
