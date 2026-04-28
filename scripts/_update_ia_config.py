import json

with open('/opt/glava/prompts/pipeline_config.json', 'r', encoding='utf-8') as f:
    cfg = json.load(f)

cfg['interview_architect']['prompt_file'] = '11_interview_architect_v4.md'
cfg['interview_architect']['_uploaded_filename'] = '11_interview_architect_v4.md'

with open('/opt/glava/prompts/pipeline_config.json', 'w', encoding='utf-8') as f:
    json.dump(cfg, f, ensure_ascii=False, indent=2)

print('Updated:', cfg['interview_architect'])
