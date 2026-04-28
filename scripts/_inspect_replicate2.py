import json
from pathlib import Path

ROOT = Path('/opt/glava')
call1_files = sorted((ROOT / 'exports').glob('karakulina_stage4_cover_designer_call1_*.json'))
# Показать все ключи первого файла
f = call1_files[0]
d = json.loads(f.read_text('utf-8'))
print(f'=== {f.name} ===')
print('keys:', list(d.keys()))
print(json.dumps(d, ensure_ascii=False, indent=2)[:2000])
