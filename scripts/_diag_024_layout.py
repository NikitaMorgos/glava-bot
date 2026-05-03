#!/usr/bin/env python3
"""
Диагностика Task 024: проверяет типы chapter_start страниц в v40 layout JSON.
Запускается на сервере: python3 /opt/glava/scripts/_diag_024_layout.py
"""
import json
import glob
import os

EXPORTS = "/opt/glava/exports"

# Ищем финальный reuse layout (gate2c)
candidates = sorted(glob.glob(f"{EXPORTS}/karakulina_reuse_layout_pages_20260501_*.json"))
# Также смотрим iter layout gate2a
iter_candidates = sorted(glob.glob(f"{EXPORTS}/karakulina_iter1_layout_pages_20260501_*.json"))
# Финальный iter layout (с патчами)
iter2_candidates = sorted(glob.glob(f"{EXPORTS}/karakulina_stage4_layout_iter1_20260501_*.json"))

all_files = candidates + iter_candidates + iter2_candidates
if not all_files:
    print("ОШИБКА: layout файлы v40 не найдены в", EXPORTS)
    exit(1)

for fname in all_files:
    print(f"\n{'='*60}")
    print(f"FILE: {os.path.basename(fname)}")
    print(f"{'='*60}")
    with open(fname) as f:
        data = json.load(f)

    pages = data if isinstance(data, list) else data.get("pages", [])
    print(f"Всего страниц: {len(pages)}")

    print("\nВсе page_index и их type:")
    for p in pages:
        ptype = p.get("type", "?")
        chid = p.get("chapter_id", "?")
        pidx = p.get("page_index", "?")
        elems = p.get("elements", [])
        elem_types = [e.get("type", "?") for e in elems]
        marker = " <<< chapter_start!" if ptype == "chapter_start" else ""
        marker2 = " <<< chapter_title!" if ptype == "chapter_title" else ""
        marker3 = " <<< cover!" if ptype == "cover" else ""
        if ptype in ("chapter_start", "chapter_title", "cover", "chapter_header"):
            print(f"  page={pidx:3} type={ptype:<20} ch={chid:<10} elems({len(elems)}): {elem_types}")
        else:
            # Show page type distribution
            pass

    # Summarize by type
    from collections import Counter
    type_counts = Counter(p.get("type", "?") for p in pages)
    print("\nРаспределение по типам страниц:")
    for t, cnt in sorted(type_counts.items()):
        print(f"  {t}: {cnt}")

    # Focus: chapter_start pages
    cs_pages = [p for p in pages if p.get("type") == "chapter_start"]
    print(f"\nСтраницы с type=chapter_start: {len(cs_pages)}")
    for p in cs_pages:
        pidx = p.get("page_index", "?")
        chid = p.get("chapter_id", "?")
        elems = p.get("elements", [])
        print(f"  page={pidx} ch={chid}: {len(elems)} элементов")
        for e in elems:
            etype = e.get("type", "?")
            ref = e.get("paragraph_ref") or e.get("subheading_ref") or e.get("text", "")[:50]
            print(f"    - {etype}: {ref}")

    # Focus: all first pages of chapters (page_index == first page where chapter_id changes)
    print("\nПервые страницы каждой главы (потенциальные chapter_start):")
    seen_chapters = set()
    for p in pages:
        chid = p.get("chapter_id", "")
        if chid and chid not in seen_chapters:
            seen_chapters.add(chid)
            pidx = p.get("page_index", "?")
            ptype = p.get("type", "?")
            elems = p.get("elements", [])
            elem_types = [e.get("type", "?") for e in elems]
            print(f"  ch={chid} first_page={pidx} type={ptype} elems({len(elems)}): {elem_types[:5]}")
