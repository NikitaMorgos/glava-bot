import json

# Check final book structure
book = json.load(open('/tmp/fc_iter3_v32.json', encoding='utf-8'))
print("FC iter3 top-level keys:", list(book.keys()))
print("stats:", book.get('stats', {}))
print()

# Check warnings content
for w in book.get('warnings', []):
    print("WARNING:", json.dumps(w, ensure_ascii=False)[:200])
