import json
c = json.load(open('/opt/glava/prompts/pipeline_config.json'))
roles = ['fact_extractor','ghostwriter','fact_checker','historian','literary_editor','proofreader']
for r in roles:
    if r in c:
        print(f"{r:20}: prompt={c[r]['prompt_file']:30} temp={c[r].get('temperature','?')}")
