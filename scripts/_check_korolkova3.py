import json
d = json.load(open("/opt/glava/exports/test_fact_map_korolkova_v1.json"))
s = d.get("subject", {})
print("name:", s.get("name", "?"))
print("birth_year:", s.get("birth_year", "?"))
print("birth_place:", s.get("birth_place", "?"))
print("death_year:", s.get("death_year", "?"))
print()
print("persons:")
for p in d.get("persons", []):
    print(f"  {p.get('name','?')} - {p.get('relation','?')}")
print()
print("timeline (first 3):")
for e in d.get("timeline", [])[:3]:
    print(f"  {e.get('year','?')}: {e.get('event','?')[:80]}")
print()
# Read first 300 chars of transcript
with open("/opt/glava/exports/korolkova_cleaned_transcript.txt", encoding="utf-8") as f:
    txt = f.read(500)
print("transcript start:", txt)
