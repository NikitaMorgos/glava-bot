import json
path = '/opt/glava/exports/karakulina_v29_run_20260420_072506/karakulina_v29_phase_b_fc_report_iter1_20260420_075646.json'
d = json.load(open(path))

errors = d.get('errors', [])
warnings = d.get('warnings', [])
print(f"errors: {len(errors)}, warnings: {len(warnings)}")

all_items = errors + warnings
for item in all_items:
    text = json.dumps(item, ensure_ascii=False)
    if any(w in text for w in ['выков', 'symbol', 'framing', 'колорит']):
        print("=== MATCH ===", json.dumps(item, ensure_ascii=False, indent=2)[:400])

print("\n--- All items ---")
for item in all_items:
    desc = item.get('description', item.get('what_is_written', item.get('text', '')))
    print(f"[{item.get('severity','?')}] {item.get('type','?')}: {str(desc)[:100]}")
