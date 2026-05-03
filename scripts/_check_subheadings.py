#!/usr/bin/env python3
"""Check which pages in v40 layout contain subheading elements."""
import json

LAYOUT = "/opt/glava/exports/karakulina_reuse_layout_pages_20260501_080607.json"

with open(LAYOUT) as f:
    data = json.load(f)

pages = data if isinstance(data, list) else data.get("pages", [])

print("Pages with subheading elements:")
for p in pages:
    elems = p.get("elements", [])
    sh_elems = [e for e in elems if e.get("type") in ("subheading", "section_header")]
    if sh_elems:
        pnum = p.get("page_number", "?")
        chid = p.get("chapter_id", "?")
        ptype = p.get("type", "?")
        print(f"  page={pnum} type={ptype} ch={chid}:")
        for e in sh_elems:
            ref = e.get("subheading_ref") or e.get("paragraph_ref") or e.get("text","")
            print(f"    subheading_ref={ref}")

# Also check book_FINAL for subheading texts
import glob
book_files = sorted(glob.glob("/opt/glava/exports/karakulina_book_FINAL_20260417_*.json"))
if book_files:
    with open(book_files[-1]) as f:
        book = json.load(f)
    chapters = book.get("chapters", [])
    print(f"\nbook_FINAL subheadings (from {book_files[-1]}):")
    for ch in chapters:
        chid = ch.get("id", "?")
        for p in ch.get("paragraphs", []):
            if p.get("type") == "subheading":
                pid = p.get("id", "?")
                txt = p.get("text", "")[:80]
                print(f"  {chid}/{pid}: {txt}")
