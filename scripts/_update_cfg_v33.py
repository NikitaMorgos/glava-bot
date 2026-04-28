import json
from pathlib import Path

cfg_path = Path('/opt/glava/prompts/pipeline_config.json')
c = json.load(open(cfg_path))

c['ghostwriter']['_notes'] = 'v2.12 (2026-04-22): АБСОЛЮТНЫЕ ЗАПРЕТЫ пп.6-7: timeline обязателен, historical_notes только в массиве, запрет раздражалась-на-подарки. Файл: 03_ghostwriter_v2.6.md'
c['fact_checker']['_notes'] = 'v2.5 (2026-04-22): single_episode_generalization (раздражалась), пустые historical_notes=critical, ***triple*** в content=critical, ch_01 всегда проверяется. Файл: 04_fact_checker_v2.md'

json.dump(c, open(cfg_path, 'w'), ensure_ascii=False, indent=2)

for role in ('ghostwriter', 'fact_checker'):
    r = c[role]
    print(f"{role}: {r['prompt_file']} temp={r['temperature']} | {r['_notes'][:60]}")
