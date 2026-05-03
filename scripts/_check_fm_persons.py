import json

for label, fpath in [('v40a', 'collab/runs/karakulina_v40/fact_map_v40a.json'), ('v40b', 'collab/runs/karakulina_v40/fact_map_v40b.json'), ('v40c', 'collab/runs/karakulina_v40/fact_map_v40c.json')]:
    with open(fpath, encoding='utf-8') as f:
        data = json.load(f)
    persons = data.get('persons', [])
    print(f'{label}: {len(persons)} persons')
    for p in persons:
        name = p.get('name','?')
        rel = p.get('relation','?')
        print(f'  {name} ({rel})')
    print()
