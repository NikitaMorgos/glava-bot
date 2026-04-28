#!/usr/bin/env python3
"""Re-run steps 3+4 (Completeness Auditor + Name Normalizer) on existing v36a artifacts."""
import json
import os
import sys

sys.path.insert(0, "/opt/glava")
import anthropic
from pipeline_utils import (
    load_config,
    run_completeness_auditor,
    apply_completeness_enrichment,
)
from scripts.normalize_named_entities import normalize_named_entities

V36A = "/opt/glava/exports/v36a"
TS = "20260428_060949"
# Загружаем FE-checkpoint — clean fact_map до Name Normalizer первого прогона
CHECKPOINT = "/opt/glava/checkpoints/karakulina/fact_map.json"

cfg = load_config()
client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

cleaned = open(f"{V36A}/karakulina_combined_cleaned_{TS}.txt", encoding="utf-8").read()
fact_map = json.load(open(CHECKPOINT, encoding="utf-8"))
# checkpoint обёрнут в {"stage":..., "content": <fact_map>}
if "content" in fact_map:
    fact_map = fact_map["content"]

print(f"[RERUN] Loaded cleaned ({len(cleaned):,} chars), FE checkpoint persons={len(fact_map.get('persons', []))}")

# Step 3: Completeness Auditor — переиспользуем уже готовый результат (без нового LLM-вызова)
AUDIT_V2 = f"{V36A}/karakulina_completeness_audit_{TS}_v2.json"
audit_result = json.load(open(AUDIT_V2, encoding="utf-8"))
print(f"[STEP 3] Загружен готовый audit_result из {AUDIT_V2}")
print(f"  auto_enrich: persons={len(audit_result.get('auto_enrich',{}).get('persons',[]))}, "
      f"events={len(audit_result.get('auto_enrich',{}).get('timeline',[]))}")
fact_map, enrichment_stats = apply_completeness_enrichment(fact_map, audit_result)
print(f"  После merge: persons={len(fact_map.get('persons', []))}")

# Сохраняем CA-enriched fact_map до NN (для диагностики)
pre_nn_path = f"{V36A}/karakulina_fact_map_pre_nn_{TS}.json"
with open(pre_nn_path, "w", encoding="utf-8") as f:
    json.dump(fact_map, f, ensure_ascii=False, indent=2)
print(f"[SAVED] {pre_nn_path} (CA-enriched, перед NN)")

# Step 4: Name Normalizer (fixed: STOP_TOKENS + transitivity)
print("\n>>> STEP 4: NAME NORMALIZER")
fact_map, merged_pairs = normalize_named_entities(fact_map, cleaned)
normalization_stats = {"merged_pairs": merged_pairs, "normalized_count": len(merged_pairs)}

fm_path = f"{V36A}/karakulina_fact_map_full_{TS}_v2.json"
with open(fm_path, "w", encoding="utf-8") as f:
    json.dump(fact_map, f, ensure_ascii=False, indent=2)
print(f"[SAVED] {fm_path}")

# Stats
persons = fact_map.get("persons", [])
print(f"\n[STATS] persons={len(persons)}, timeline={len(fact_map.get('timeline', []))}, "
      f"traits={len(fact_map.get('character_traits', []))}, gaps={len(fact_map.get('gaps', []))}")
print(f"[PERSONS]")
for p in persons:
    print(f"  {p.get('id')} | {p.get('name')} | rel={p.get('relation_to_subject', '')} | aliases={p.get('aliases', [])}")

# Check acceptance criteria
person_names_lower = {p.get("name", "").lower() for p in persons}
all_aliases = {a.lower() for p in persons for a in (p.get("aliases") or [])}
all_names = person_names_lower | all_aliases

tatyana_found = any("татьян" in n for n in all_names)
print(f"\n[CHECK] Татьяна в persons[]: {'YES' if tatyana_found else 'NO'}")

# Auditor auto_enrich summary
ae = audit_result.get("auto_enrich", {})
lg = audit_result.get("log_only_gaps", {})
notes = audit_result.get("processing_notes", {})
print(f"[CHECK] Auditor auto_enrich: persons={len(ae.get('persons',[]))}, "
      f"events={len(ae.get('timeline',[]))}, locs={len(ae.get('locations',[]))}, "
      f"traits={len(ae.get('character_traits',[]))}")
print(f"[CHECK] Auditor log_only: persons={len(lg.get('missing_persons',[]))}, "
      f"events={len(lg.get('missing_events',[]))}")
if notes.get("summary"):
    print(f"[CHECK] Auditor summary: {notes['summary']}")

# Merged pairs
if merged_pairs:
    print(f"\n[NAME NORMALIZER] Слито {len(merged_pairs)} пар:")
    for pair in merged_pairs:
        print(f"  [{pair['field']}] '{pair['merged']}' → '{pair['canonical']}' "
              f"(overlap={pair['overlap']}, shared={pair.get('shared_variants', [])})")
else:
    print("[NAME NORMALIZER] Нет слитых пар")

print("\n[DONE]")
