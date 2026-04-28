import json
from pathlib import Path

data = json.load(open("/opt/glava/exports/karakulina_book_draft_final_20260326_134328.json"))
bd = data.get("book_draft", data)
fixes = 0

for ch in bd["chapters"]:
    c = ch.get("content", "")
    # Ищем расширение цитаты о муравье
    needle = "\u2014 \u0432\u0441\u0435\u0433\u0434\u0430 \u0432 \u0440\u0430\u0431\u043e\u0442\u0435, \u0432\u0441\u0435\u0433\u0434\u0430 \u0432 \u0437\u0430\u0431\u043e\u0442\u0430\u0445."
    if needle in c and "\u043c\u0443\u0440\u0430\u0432\u0435\u0439" in c:
        idx = c.find(needle)
        print("FOUND:", repr(c[max(0,idx-5):idx+len(needle)]))
        c = c[:idx] + "." + c[idx+len(needle):]
        ch["content"] = c
        fixes += 1
        print(f"[FIX 1] \u0423\u0431\u0440\u0430\u043b\u0438 \u0440\u0430\u0441\u0448\u0438\u0440\u0435\u043d\u0438\u0435 \u0432 {ch['id']}")

print(f"\u041f\u0440\u0430\u0432\u043e\u043a: {fixes}")
total = sum(len(ch.get("content","")) for ch in bd.get("chapters",[]))
print(f"\u0421\u0438\u043c\u0432\u043e\u043b\u043e\u0432: {total}")
json.dump(data, open("/opt/glava/exports/karakulina_book_draft_final_20260326_134328.json","w"), ensure_ascii=False, indent=2)
print("done")
