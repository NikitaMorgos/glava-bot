#!/usr/bin/env python3
import json

# Check v5 fact_map structure (the default)
fm5 = json.load(open('/opt/glava/exports/test_fact_map_karakulina_v5.json'))
print('v5 top-level keys:', list(fm5.keys())[:10])
print(f'v5 persons at top: {"persons" in fm5}, count: {len(fm5.get("persons", []))}')

# We need to extract content from checkpoint to use as fact_map
ck = json.load(open('/opt/glava/checkpoints/karakulina/fact_map.json'))
fm_from_ck = ck['content']
print(f'\nFrom checkpoint content: persons={len(fm_from_ck.get("persons", []))}')

# Save it as the fact_map input file for v42
import json
with open('/opt/glava/exports/karakulina_fact_map_v42_input.json', 'w', encoding='utf-8') as f:
    json.dump(fm_from_ck, f, ensure_ascii=False, indent=2)
print('Saved: karakulina_fact_map_v42_input.json')
