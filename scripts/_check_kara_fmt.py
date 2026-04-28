import json
d = json.load(open("/opt/glava/exports/test_fact_map_karakulina_v5.json"))
print("keys:", list(d.keys()))
print("events:", len(d.get("events", [])))
print("timeline:", len(d.get("timeline", [])))
s = d.get("subject", {})
print("subject keys:", list(s.keys()))
print("subject full_name:", s.get("full_name", "NOT FOUND"))
print("subject name:", s.get("name", "NOT FOUND"))
