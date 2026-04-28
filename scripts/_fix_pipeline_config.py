import json

cfg_path = '/opt/glava/pipeline_config.json'
c = json.load(open(cfg_path))

# Fix ghostwriter: v2.6.md with temperature 0.4
c['ghostwriter']['prompt_file'] = '03_ghostwriter_v2.6.md'
c['ghostwriter']['temperature'] = 0.4
c['ghostwriter']['_notes'] = 'v2.10 (2026-04-14): anti-hallucination rules, symbolization ban, hist notes rules. Temp 0.4 for precision.'

# Fix fact_checker: v2.md (v2.4)
c['fact_checker']['prompt_file'] = '04_fact_checker_v2.md'
c['fact_checker']['_notes'] = 'v2.4 (2026-04-14): framing_distortion pattern, bio_data completeness rules'

# Fix fact_extractor: v3.3
c['fact_extractor']['prompt_file'] = '02_fact_extractor_v3.3.md'

json.dump(c, open(cfg_path, 'w'), ensure_ascii=False, indent=2)
print('Updated pipeline_config.json:')
for role in ('ghostwriter', 'fact_checker', 'fact_extractor', 'historian'):
    cfg = c.get(role, {})
    if cfg:
        print(f"  {role}: prompt={cfg.get('prompt_file','?')} temp={cfg.get('temperature','?')}")
