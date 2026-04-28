import json
d = json.load(open("/opt/glava/exports/test_fact_map_korolkova_v1.json"))
subj = d.get("subject", {})
print("subject:", subj.get("full_name", "?"), "|", subj.get("birth_year", "?"))
print("events:", len(d.get("events", [])))
print("persons:", len(d.get("persons", [])))
print("quotes:", len(d.get("quotes", [])))
import os
sz = os.path.getsize("/opt/glava/exports/korolkova_cleaned_transcript.txt")
print("transcript size:", sz, "bytes")
