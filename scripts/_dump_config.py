import json
c = json.load(open('/opt/glava/prompts/pipeline_config.json'))
for k, v in c.items():
    if isinstance(v, dict) and 'model' in v:
        print(f"{k:20}: max_tokens={v.get('max_tokens','?'):6}  temp={v.get('temperature','?'):5}  prompt={v.get('prompt_file','?')}")
