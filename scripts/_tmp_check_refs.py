import json, sys

# Check paragraph_ref values in layout vs BookIndex keys
with open("/opt/glava/exports/karakulina_v37_iter1_layout_pages_20260430_064737.json") as f:
    layout = json.load(f)

with open("/opt/glava/exports/karakulina_v37_input_proofreader_checkpoint_20260430_064737.json") as f:
    book = json.load(f)

# Collect layout refs
layout_refs = []
for page in layout.get("pages", []):
    ch = page.get("chapter_id", "")
    for e in page.get("elements", []):
        if e.get("type") == "paragraph":
            ref = e.get("paragraph_ref") or e.get("paragraph_id") or ""
            ch_e = e.get("chapter_id") or ch
            layout_refs.append((ch_e, ref))

print("Layout paragraph refs (first 15):", layout_refs[:15])
print("Total layout para refs:", len(layout_refs))

# Check BookIndex building
sys.path.insert(0, "/opt/glava")
sys.path.insert(0, "/opt/glava/scripts")
from pipeline_utils import prepare_book_for_layout
from pdf_renderer import BookIndex

book_prepared = prepare_book_for_layout(book)
bi = BookIndex(book_prepared)

print("\nBookIndex chapters:", list(bi._index.keys()) if hasattr(bi, "_index") else "no _index attr")

# Try to look up first few refs from layout
print("\nLookup test:")
for ch_id, ref in layout_refs[:10]:
    text = bi.get(ch_id, ref)
    status = "FOUND" if text else "MISSING"
    print(f"  get({ch_id!r}, {ref!r}) -> {status}: {(text or '')[:60]!r}")
