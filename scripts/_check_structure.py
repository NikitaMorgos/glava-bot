import json
d = json.load(open("/opt/glava/exports/karakulina_book_draft_v3_20260327_062706.json"))
print("keys:", list(d.keys()))
chs = d.get("chapters", [])
print("chapters:", len(chs))
if chs:
    print("chapter[0] keys:", list(chs[0].keys()))
    # check content field
    c0 = chs[0].get("content","")
    print("content len:", len(c0))
    print("content[:200]:", c0[:200])
