#!/usr/bin/env python3
import json

# Check checkpoint structure
ck = json.load(open('/opt/glava/checkpoints/karakulina/fact_map.json'))
top_keys = list(ck.keys())
print('Top-level keys:', top_keys[:10])
has_persons_top = 'persons' in ck
has_content = 'content' in ck
print(f'persons at top: {has_persons_top}, has content: {has_content}')
if has_persons_top:
    print(f'top-level persons count: {len(ck["persons"])}')
if has_content:
    c = ck['content']
    print(f'content keys: {list(c.keys())[:10]}')
    if 'persons' in c:
        print(f'content.persons count: {len(c["persons"])}')
