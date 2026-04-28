import json
d = json.load(open("/opt/glava/exports/test_fact_map_korolkova_v1.json"))
print("top-level keys:", list(d.keys()))
# Проверим вложенность
for k, v in d.items():
    if isinstance(v, dict):
        print(f"  {k} (dict): {list(v.keys())[:6]}")
    elif isinstance(v, list):
        print(f"  {k} (list): {len(v)} items")
    else:
        print(f"  {k}: {str(v)[:80]}")
