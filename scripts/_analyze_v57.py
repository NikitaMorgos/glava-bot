#!/usr/bin/env python3
"""Verified-on-run analysis for v57 (Batch 1: tasks 039, 040, 042)."""
import json
import re
import sys
from pathlib import Path

BASE = Path("/opt/glava/collab/runs/karakulina_v57")

def load(name):
    p = list(BASE.glob(f"*{name}*"))
    if not p:
        print(f"[MISSING] {name}")
        return {}
    return json.loads(p[0].read_text(encoding="utf-8"))


print("=" * 70)
print("VERIFIED-ON-RUN v57 — Batch 1 (tasks 039, 040, 042)")
print("=" * 70)

# ────────────────────────────────────────────────────────────────
# 042: subject_age enrichment
# ────────────────────────────────────────────────────────────────
print("\n=== TASK 042: Subject Age Enrichment ===")
fm_enriched = load("fact_map_enriched")
timeline = fm_enriched.get("timeline", [])
total = len(timeline)
with_year = [e for e in timeline if (e.get("date") or {}).get("year") is not None]
with_age  = [e for e in timeline if "subject_age" in e]
pct = round(100 * len(with_age) / len(with_year), 1) if with_year else 0
print(f"  Всего events: {total}")
print(f"  Events с known year: {len(with_year)}")
print(f"  Events с subject_age: {len(with_age)} ({pct}%)")
print("\n  Примеры (5 events):")
for e in with_age[:5]:
    yr = (e.get("date") or {}).get("year")
    print(f"    {e['id']} year={yr} → subject_age={e['subject_age']}  [{e.get('title','')[:40]}]")

# Конкретное наблюдение (формат Опуса)
if with_age:
    sample_e = next((e for e in with_age if e.get("id") == "event_007"), with_age[0])
    print(f"\n  VERIFIED: Открыл fact_map_v57_full_enriched, {sample_e['id']} ({sample_e.get('title','?')[:30]} {(sample_e.get('date') or {}).get('year','?')}) имеет subject_age={sample_e.get('subject_age','?')}; всего из {len(with_year)} events с known year, {len(with_age)} имеют subject_age ({pct}%).")
else:
    print("  VERIFIED: subject_age НЕ добавлен — ошибка!")

# ────────────────────────────────────────────────────────────────
# 040: topo normalize
# ────────────────────────────────────────────────────────────────
print("\n=== TASK 040: Topo Normalize ===")
topo_fm = load("topo_normalize_factmap")
topo_book = load("topo_normalize_report")
print(f"  fact_map normalize: {topo_fm}")
print(f"  book normalize: {topo_book}")

text_file = BASE / "karakulina_v57_text_FULL.md"
if text_file.exists():
    text = text_file.read_text(encoding="utf-8")
    for bad, label in [("Новомер", "Новомергородский"), ("Керсан", "Керсанов"), ("Капашвар", "Капашвара")]:
        count = len(re.findall(bad, text))
        status = "✅ 0 вхождений" if count == 0 else f"❌ {count} вхождений"
        print(f"  grep «{label}»: {status}")
    # Проверяем что канонические формы ЕСТЬ
    for good in ["Новомиргородский", "Кирсанов", "Капошвара"]:
        count = len(re.findall(good, text))
        print(f"  grep canonical «{good}»: {count} вхождений")
else:
    print("  text_FULL.md не найден")

# ────────────────────────────────────────────────────────────────
# 039: bio_data integrity
# ────────────────────────────────────────────────────────────────
print("\n=== TASK 039: Bio_data Integrity ===")
bio_report = load("bio_data_integrity")
print(f"  filtered_count: {bio_report.get('filtered_count', '?')}")
print(f"  issues_count:   {bio_report.get('issues_count', '?')}")
print(f"  filtered_non_family: {bio_report.get('filtered_non_family', [])}")
print(f"  required_field_issues: {bio_report.get('required_field_issues', [])}")

book_final = load("book_FINAL_stage3")
book_data = book_final.get("book_final", book_final)
chapters = book_data.get("chapters", [])
ch01 = next((c for c in chapters if c.get("id") == "ch_01"), {})
bio = ch01.get("bio_data", {})
family = bio.get("family", [])
awards = bio.get("awards", [])

print(f"\n  bio_data.family ({len(family)} записей):")
marfa = None
tyotya_masha = None
dmitry = None
for e in family:
    label = e.get("label", "?")
    value = e.get("value", "?")
    note = e.get("note", "")
    nv = e.get("needs_verification", False)
    print(f"    [{label}] {value}  note='{note}'  nv={nv}")
    if "марф" in value.lower() or "марф" in label.lower():
        marfa = e
    if "маш" in value.lower() and ("тёт" in label.lower() or "сосед" in label.lower()):
        tyotya_masha = e
    if "дмитр" in value.lower():
        dmitry = e

print(f"\n  awards: {[a.get('value', str(a)) if isinstance(a, dict) else a for a in awards]}")

print(f"\n  VERIFIED:")
print(f"    Марфа в family: {'✅ ДА' if marfa else '❌ НЕТ'}{' (needs_verification=True)' if marfa and marfa.get('needs_verification') else ''}")
print(f"    Тётя Маша НЕ в family: {'✅ ДА' if not tyotya_masha else '❌ ЕСТЬ'}")
if dmitry:
    note = dmitry.get("note", "")
    has_1978 = "1978" in note
    print(f"    Дмитрий есть с (ум. 1978): {'✅ ДА' if has_1978 else '⚠️ note=' + repr(note)}")
else:
    print("    Дмитрий: не найден")

# Ударник
awards_text = " ".join(
    (a.get("value") or a) if isinstance(a, dict) else str(a)
    for a in awards
).lower()
has_udarnik = "удар" in awards_text
print(f"    Ударник в bio_data.awards: {'✅ ДА' if has_udarnik else '⚠️ НЕТ (reported as issue)'}")

# Also check text_FULL for Семья section
if text_file.exists():
    text = text_file.read_text(encoding="utf-8")
    marfa_in_text = "Марфа" in text or "марфа" in text.lower()
    masha_family_in_text = bool(re.search(r"тёт[а-яё]* Маш[а-яё]*.*семь|семь.*тёт[а-яё]* Маш", text, re.IGNORECASE))
    print(f"\n  В text_FULL.md:")
    print(f"    Марфа упоминается: {'✅' if marfa_in_text else '❌'}")
    print(f"    Тётя Маша в контексте семьи: {'❌ (не найдено)' if not masha_family_in_text else '⚠️ НАЙДЕНО'}")

print("\n" + "=" * 70)
print("ИТОГОВЫЙ СТАТУС:")
print("  042: ✅ subject_age добавлен" if with_age else "  042: ❌ subject_age НЕ добавлен")
print("  040: ✅ gazeteer normalize отработал (Stage 1)" if topo_fm.get("replacements") else "  040: ⚠️ 0 замен на Stage 1")
print("  039: ✅ enforce(Марфа) + filter(0 удалено) + validate" if marfa else "  039: ❌ Марфа не добавлена")
print("=" * 70)
