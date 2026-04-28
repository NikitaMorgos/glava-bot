import json
fm = json.load(open('/opt/glava/checkpoints/karakulina/fact_map.json'))
hits = []
for e in fm.get('timeline', []):
    s = json.dumps(e, ensure_ascii=False)
    if '1977' in s or 'Маргос' in s or 'замуж' in s or 'свадьб' in s:
        hits.append(e)
print(json.dumps(hits, ensure_ascii=False, indent=2))
