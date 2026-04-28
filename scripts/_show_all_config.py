import json
c = json.load(open('/opt/glava/pipeline_config.json'))
for role in ('ghostwriter', 'fact_checker', 'historian', 'fact_extractor', 'literary_editor', 'proofreader', 'layout_designer'):
    cfg = c.get(role, {})
    if cfg:
        print(f"{role}: prompt={cfg.get('prompt_file','?')} temp={cfg.get('temperature','?')}")
