#!/usr/bin/env python3
import json, sys, pathlib
sys.stdout.reconfigure(encoding='utf-8')

layout  = json.load(open('exports/karakulina_layout_20260404.json', encoding='utf-8'))
photos_dir = pathlib.Path('exports/karakulina_photos')
manifest = json.load(open(photos_dir / 'manifest.json', encoding='utf-8'))

# Build id→filename map from manifest
id_map = {}
for p in manifest:
    if not p.get('exclude'):
        idx = p.get('index', 0)
        id_map[f'photo_{idx:03d}'] = p['filename']
        id_map[f'photo_{idx}'] = p['filename']
        id_map[p['filename']] = p['filename']

print(f"Manifest photos: {len(id_map)//2}")
print(f"Photo IDs: {sorted(set(k for k in id_map if k.startswith('photo_')))}")
print()

for page in layout['pages']:
    pn = page['page_number']
    ptype = page['type']
    has_photo_elem = False
    for e in page.get('elements', []):
        if e.get('type') in ('photo', 'image'):
            has_photo_elem = True
            pid = e.get('photo_id', '')
            found = pid in id_map
            fname = id_map.get(pid, 'NOT FOUND')
            if not found:
                # Try fuzzy match
                num_part = pid.replace('photo_', '').lstrip('0') or '0'
                fuzzy = [k for k in id_map if num_part in k]
                fname = fuzzy[0] if fuzzy else 'NOT FOUND'
                found = bool(fuzzy)
            print(f"p{pn:02d} [{ptype:16s}] photo_id={pid!r:18s} layout={e.get('layout','?'):12s} -> {fname} {'✓' if found else '✗ MISSING'}")

    if not has_photo_elem and ptype not in ('cover', 'blank', 'toc'):
        texts = [e.get('text', '') for e in page.get('elements', []) if e.get('type') == 'paragraph']
        total_chars = sum(len(t) for t in texts)
        if total_chars < 300:
            print(f"p{pn:02d} [{ptype:16s}] NO PHOTO - only {total_chars} chars of text → possible empty space")
