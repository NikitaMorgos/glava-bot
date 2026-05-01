import json
with open("/opt/glava/exports/karakulina_v38a/karakulina_normalization_log_20260430_113308.json") as f:
    norm_list = json.load(f)
print(f"normalization log: {len(norm_list)} entries")
for i, entry in enumerate(norm_list):
    print(f"\n[{i}] {json.dumps(entry, ensure_ascii=False, indent=2)[:500]}")
