import json
d = json.load(open('/opt/glava/exports/karakulina_book_FINAL_stage3_20260412_132158.json'))
print("Top keys:", list(d.keys())[:10])
chs = d.get('chapters') or d.get('book', {}).get('chapters')
print("chapters count:", len(chs) if chs else 'not found')
if not chs:
    for k, v in d.items():
        print(k, type(v))
