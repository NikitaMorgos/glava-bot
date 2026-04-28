import json, os
from pathlib import Path

ROOT = Path('/opt/glava')
# Ищем все call1 файлы по дате
call1_files = sorted((ROOT / 'exports').glob('karakulina_stage4_cover_designer_call1_*.json'))
print(f'Найдено call1 файлов: {len(call1_files)}')
for f in call1_files[-3:]:
    print(f'\n=== {f.name} ===')
    d = json.loads(f.read_text('utf-8'))
    pg = d.get('portrait_generation', {})
    print('prompt:', pg.get('prompt', 'НЕТ')[:400])
    print('reference_photos:', pg.get('reference_photos', []))
    print('replicate_model:', pg.get('model', pg.get('replicate_model', 'N/A')))
    print('style:', pg.get('style', 'N/A'))
