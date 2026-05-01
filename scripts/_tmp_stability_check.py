import json

with open("/opt/glava/exports/karakulina_v38a/v38_stability_report.json") as f:
    r = json.load(f)
print("stability_score:", r.get("stability_score", 0) * 100, "%")
print("total_a:", r.get("total_a"), "total_b:", r.get("total_b"), "match:", r.get("match_count"))
print("only_in_a:", r.get("only_in_a"))
print("only_in_b:", r.get("only_in_b"))

# normalization log  
with open("/opt/glava/exports/karakulina_v38a/karakulina_normalization_log_20260430_113308.json") as f:
    norm_list = json.load(f)
# It's a list
print(f"\nnormalization log type: list, len={len(norm_list)}")
for entry in norm_list[:10]:
    if isinstance(entry, dict):
        if entry.get("action") == "REJECTED":
            print(f"  REJECTED: {entry.get('a')} <-> {entry.get('b')} reason={entry.get('reason')}")
        elif entry.get("action") == "MERGED":
            print(f"  MERGED: {entry.get('a')} <-> {entry.get('b')}")
