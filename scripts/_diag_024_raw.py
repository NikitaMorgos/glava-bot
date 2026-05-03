#!/usr/bin/env python3
"""Check raw structure of chapter_start pages."""
import json

LAYOUT = "/opt/glava/exports/karakulina_reuse_layout_pages_20260501_080607.json"

with open(LAYOUT) as f:
    data = json.load(f)

pages = data if isinstance(data, list) else data.get("pages", [])
print(f"Total pages: {len(pages)}")
print(f"First page keys: {list(pages[0].keys()) if pages else 'none'}")
print()

# Show first chapter_start page raw
for i, p in enumerate(pages):
    if p.get("type") == "chapter_start":
        print(f"CHAPTER_START at index {i}:")
        print(json.dumps(p, ensure_ascii=False, indent=2))
        print()
        # Show next 2 pages
        for j in range(i+1, min(i+3, len(pages))):
            np = pages[j]
            print(f"NEXT PAGE index {j} type={np.get('type')} ch={np.get('chapter_id')} elems={len(np.get('elements',[]))}")
            for e in np.get("elements", [])[:5]:
                estr = str(e)[:120]
                print(f"  - {e.get('type')}: {estr}")
        print()
        break  # Just first one

# Also check page_index field - maybe it uses a different field name
print("Looking for page number fields:")
for p in pages[:3]:
    print({k: v for k, v in p.items() if k not in ("elements",)})
