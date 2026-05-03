#!/usr/bin/env python3
import json

for ck_name in ['layout_text_approved.json', 'layout_bio_approved.json']:
    ck_path = f'/opt/glava/checkpoints/karakulina/{ck_name}'
    try:
        with open(ck_path) as f:
            d = json.load(f)
        was = d.get('approved')
        d['approved'] = True
        with open(ck_path, 'w') as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
        print(f'{ck_name}: {was} -> True')
    except FileNotFoundError:
        print(f'{ck_name}: NOT FOUND')
