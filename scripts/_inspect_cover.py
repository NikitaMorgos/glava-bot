import json, sys

# 1. Cover elements в layout
d = json.load(open('exports/karakulina_stage4_layout_iter3_20260401_124806.json'))
cover = next(p for p in d['pages'] if p['type'] == 'cover')
print('=== COVER elements ===')
for e in cover['elements']:
    print(json.dumps(e, ensure_ascii=False))

# 2. Replicate-промпт из call1 Cover Designer
print()
print('=== COVER DESIGNER CALL1 (portrait_generation) ===')
try:
    c1 = json.load(open('exports/karakulina_stage4_cover_designer_call1_20260401_124806.json'))
    pg = c1.get('portrait_generation', {})
    print('prompt:', pg.get('prompt', 'N/A')[:500])
    print('reference_photos:', pg.get('reference_photos', []))
    print('style:', pg.get('style', 'N/A'))
except Exception as e:
    print('Ошибка:', e)

# 3. call2 — что получилось
print()
print('=== COVER DESIGNER CALL2 (verdict) ===')
try:
    c2 = json.load(open('exports/karakulina_stage4_cover_designer_call2_a1_20260331_093807.json'))
    print('verdict:', c2.get('portrait_verdict', 'N/A'))
    fc = c2.get('final_cover_composition', {})
    print('cover_surname:', fc.get('cover_surname', 'N/A'))
    print('cover_first_name:', fc.get('cover_first_name', 'N/A'))
except Exception as e:
    print('Ошибка:', e)
