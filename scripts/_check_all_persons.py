#!/usr/bin/env python3
import json
fm = json.load(open('/opt/glava/exports/karakulina_input_fact_map_checkpoint_20260503_194138.json'))
content = fm.get('content', fm)
ps = content.get('persons', [])
print(f'Total persons: {len(ps)}')
print('\nAll persons with relation:')
for p in ps:
    print(json.dumps({'name': p.get('name'), 'relation': p.get('relation')}, ensure_ascii=False))

# Check bio_data from ghostwriter checkpoint
gw = json.load(open('/opt/glava/checkpoints/karakulina/ghostwriter.json'))
gw_content = gw.get('content', gw)
chapters = gw_content.get('chapters', [])
for ch in chapters:
    if ch.get('id') == 'ch_01':
        bio = ch.get('bio_data', {})
        family = bio.get('family', [])
        print(f'\nGW bio_data.family ({len(family)} entries):')
        for f in family:
            print(json.dumps(f, ensure_ascii=False))
