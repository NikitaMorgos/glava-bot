import json
b = json.load(open("/opt/glava/exports/karakulina_v34_run_20260423_060319/karakulina_book_draft_v6_20260423_061026.json"))
ch01 = next(c for c in b["chapters"] if c.get("id")=="ch_01")
print("ch_01 top-level keys:", list(ch01.keys()))
print("timeline top-level:", len(ch01.get("timeline") or []), "этапов")
bio = ch01.get("bio_data") or {}
print("bio_data keys:", list(bio.keys()))
print("timeline in bio_data:", "timeline" in bio)

# Check Kaposhvara canonical form in fact_map
fm = json.load(open("/opt/glava/exports/karakulina_v34_run_20260423_060319/karakulina_fact_map_full_20260423_060320.json"))
for loc in fm.get("locations", []):
    n = loc.get("name","")
    if "апош" in n.lower() or "апаш" in n.lower():
        print("FACT_MAP location:", n, "aliases:", loc.get("aliases",[]))
