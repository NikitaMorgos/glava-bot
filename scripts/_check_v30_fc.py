import json, glob

# FC report for v30
run = '/opt/glava/collab/runs/karakulina_v30_20260420_122027'
exports = '/opt/glava/exports/karakulina_v30_run_20260420_122027'

# Find FC report
candidates = (
    glob.glob(f'{exports}/*fc_report*.json') +
    glob.glob(f'{run}/*fc_report*.json') +
    glob.glob('/opt/glava/exports/*v30*fc_report*.json')
)
print("FC reports found:", candidates)

if candidates:
    d = json.load(open(candidates[0]))
    errors = d.get('errors', [])
    warnings = d.get('warnings', [])
    all_items = errors + warnings
    print(f"errors: {len(errors)}, warnings: {len(warnings)}")
    
    keywords = ['выков', 'symbol', 'огурц', 'подар', 'чемодан', 'валер', 'драм', 'характер', 'framing']
    print("\n--- Keyword matches ---")
    for item in all_items:
        text = json.dumps(item, ensure_ascii=False).lower()
        if any(k in text for k in keywords):
            print(f"[{item.get('severity','?')}] {item.get('type','?')}: {str(item.get('what_is_written', item.get('description','')))[:150]}")
    
    print("\n--- All items ---")
    for item in all_items:
        desc = item.get('what_is_written') or item.get('description') or ''
        print(f"[{item.get('severity','?')}] {item.get('type','?')}: {str(desc)[:100]}")
