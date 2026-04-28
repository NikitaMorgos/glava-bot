import json
from pathlib import Path

cfg_path = Path('/opt/glava/prompts/pipeline_config.json')
c = json.load(open(cfg_path))

# Fix ghostwriter: temp 0.6 -> 0.4, confirm v2.6.md
c['ghostwriter']['temperature'] = 0.4
c['ghostwriter']['prompt_file'] = '03_ghostwriter_v2.6.md'
c['ghostwriter']['_notes'] = 'v2.11 (2026-04-21): АБСОЛЮТНЫЕ ЗАПРЕТЫ в начале промпта. Temp 0.4 для точности.'

# Confirm fact_checker is v2.md (already correct)
c['fact_checker']['prompt_file'] = '04_fact_checker_v2.md'
c['fact_checker']['_notes'] = 'v2.4 (2026-04-14): framing_distortion pattern, symbolization check.'

json.dump(c, open(cfg_path, 'w'), ensure_ascii=False, indent=2)

print('Updated prompts/pipeline_config.json:')
for role in ('ghostwriter', 'fact_checker', 'historian', 'fact_extractor'):
    cfg = c.get(role, {})
    if cfg:
        print(f"  {role}: prompt={cfg.get('prompt_file','?')} temp={cfg.get('temperature','?')}")
