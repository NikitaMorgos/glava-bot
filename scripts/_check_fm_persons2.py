import json, sys

out = []
for label, fpath in [('v40a', 'collab/runs/karakulina_v40/fact_map_v40a.json'), ('v40b', 'collab/runs/karakulina_v40/fact_map_v40b.json'), ('v40c', 'collab/runs/karakulina_v40/fact_map_v40c.json')]:
    with open(fpath, encoding='utf-8') as f:
        data = json.load(f)
    persons = data.get('persons', [])
    out.append(f'{label}: {len(persons)} persons')
    for p in persons:
        name = p.get('name','?')
        rel = p.get('relation','?')
        out.append(f'  {name} ({rel})')
    out.append('')

# Also check bio_data
out.append('=== bio_data.family per fact_map ===')
for label, fpath in [('v40a', 'collab/runs/karakulina_v40/fact_map_v40a.json'), ('v40b', 'collab/runs/karakulina_v40/fact_map_v40b.json')]:
    with open(fpath, encoding='utf-8') as f:
        data = json.load(f)
    bio = data.get('bio_data', {})
    family = bio.get('family', [])
    out.append(f'{label} bio_data.family ({len(family)} entries):')
    for item in family:
        out.append(f'  {item}')
    out.append('')

with open('scripts/_fm_persons_report.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))
print('Written to scripts/_fm_persons_report.txt')
