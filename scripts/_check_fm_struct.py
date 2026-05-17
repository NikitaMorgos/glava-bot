#!/usr/bin/env python3
import json
fm = json.load(open('/opt/glava/exports/karakulina_input_fact_map_checkpoint_20260503_194138.json'))
content = fm.get('content', fm)
ps = content.get('persons', [])
print('persons:', len(ps))
for p in ps[:5]:
    print(json.dumps({'name': p.get('name'), 'relation': p.get('relation')}, ensure_ascii=False))
