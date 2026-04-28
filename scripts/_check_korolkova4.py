import json
d = json.load(open("/opt/glava/exports/korolkova_fact_map_v2.json"))
print("top-level keys:", list(d.keys()))
s = d.get("subject", {})
print("subject:", json.dumps(s, ensure_ascii=False, indent=2)[:400])
print("\nevents count:", len(d.get("events", [])))
print("first 3 events:")
for e in d.get("events", [])[:3]:
    print(" ", json.dumps(e, ensure_ascii=False)[:120])
print("\npersons count:", len(d.get("persons", [])))
print("first 3 persons:")
for p in d.get("persons", [])[:3]:
    print(" ", json.dumps(p, ensure_ascii=False)[:120])
