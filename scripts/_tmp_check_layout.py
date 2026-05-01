import json
with open("/opt/glava/exports/karakulina_v37_iter1_layout_pages_20260430_064737.json") as f:
    layout = json.load(f)
pages = layout.get("pages", [])
print("pages:", len(pages))
for p in pages[:5]:
    elems = p.get("elements", [])
    page_ch = p.get("chapter_id", "")
    para_elems = [e for e in elems if e.get("type") == "paragraph"]
    elem_chs = [e.get("chapter_id", "") for e in para_elems]
    print("  type=%s page_ch=%r elem_chs[:3]=%r" % (p.get("type"), page_ch, elem_chs[:3]))
print("---")
# count elements with vs without chapter_id
no_ch = sum(1 for p in pages for e in p.get("elements", []) if e.get("type") == "paragraph" and not e.get("chapter_id"))
with_ch = sum(1 for p in pages for e in p.get("elements", []) if e.get("type") == "paragraph" and e.get("chapter_id"))
print("paragraph elements WITHOUT chapter_id:", no_ch)
print("paragraph elements WITH chapter_id:", with_ch)
