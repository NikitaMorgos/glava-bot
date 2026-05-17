#!/usr/bin/env python3
import json, sys
fm = json.load(open('/opt/glava/checkpoints/karakulina/fact_map.json', encoding='utf-8'))
ps = fm.get('persons', [])
for p in ps[:25]:
    print(json.dumps({'name': p.get('name'), 'relation': p.get('relation')}, ensure_ascii=False))
print(f"\nTotal persons: {len(ps)}")
# Check bio_data in ghostwriter checkpoint
try:
    gw = json.load(open('/opt/glava/checkpoints/karakulina/ghostwriter.json', encoding='utf-8'))
    content = gw.get('content', {})
    chapters = content.get('chapters', [])
    for ch in chapters:
        if ch.get('id') == 'ch_01':
            bio = ch.get('bio_data', {})
            family = bio.get('family', [])
            print(f"\nbio_data.family ({len(family)} entries):")
            for f in family:
                print(json.dumps(f, ensure_ascii=False))
except Exception as e:
    print(f"GW checkpoint error: {e}")
