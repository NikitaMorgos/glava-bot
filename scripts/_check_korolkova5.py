import json
d = json.load(open("/opt/glava/exports/korolkova_fact_map_v2.json"))
print("timeline:", len(d.get("timeline", [])))
print("character_traits:", len(d.get("character_traits", [])))
print("quotes:", len(d.get("quotes", [])))
print("gaps:", len(d.get("gaps", [])))
print()
print("first 5 timeline events:")
for e in d.get("timeline", [])[:5]:
    print(" ", json.dumps(e, ensure_ascii=False)[:150])
print()
s = d.get("subject", {})
print("subject:", json.dumps(s, ensure_ascii=False))
