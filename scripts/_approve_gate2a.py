#!/usr/bin/env python3
import json

ck_path = '/opt/glava/checkpoints/karakulina/layout_text_approved.json'
with open(ck_path) as f:
    d = json.load(f)
print('Before:', d.get('approved'))
d['approved'] = True
with open(ck_path, 'w') as f:
    json.dump(d, f, ensure_ascii=False, indent=2)
print('After:', d.get('approved'))
