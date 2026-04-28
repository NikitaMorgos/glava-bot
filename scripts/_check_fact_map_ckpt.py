import json, sys

path = sys.argv[1] if len(sys.argv) > 1 else "/opt/glava/checkpoints/karakulina/fact_map.json"
d = json.load(open(path))
subj = d.get("subject", {})
print("name:", subj.get("name", "?"))
print("birth_year:", subj.get("birth_year", "?"))
print("death_year:", subj.get("death_year", "?"))
print("timeline events:", len(d.get("timeline", [])))
print("persons:", len(d.get("persons", [])))
print("quotes:", len(d.get("quotes", [])))
print("locations:", len(d.get("locations", [])))
print("character_traits:", len(d.get("character_traits", [])))
gaps = d.get("gaps", [])
print("gaps:", len(gaps))
print("Keys:", list(d.keys()))
