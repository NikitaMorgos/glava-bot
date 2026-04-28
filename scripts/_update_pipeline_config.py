import json

with open('/opt/glava/prompts/pipeline_config.json') as f:
    cfg = json.load(f)

cfg['cover_designer']['prompt_file'] = '13_cover_designer_v2.md'
cfg['cover_designer']['_notes'] = (
    'v2.0 (2026-03-31): age-matching photo descriptions, 3-zone layout, '
    'year decoration removed, prompt matches actual photo age. '
    'Image gen: google/nano-banana-2 (replicate). Upgraded from v1.'
)

cfg['interview_architect']['prompt_file'] = '11_interview_architect_v2.md'
cfg['interview_architect']['_notes'] = (
    'v2.0 (2026-03-31): access_status filtering (skip deceased/unreachable), '
    'source_type + alternative_sources, observable behaviour for inner world, '
    'transcripts_summary. Upgraded from v1.'
)

cfg['fact_extractor']['prompt_file'] = '02_fact_extractor_v3.2.md'
cfg['fact_extractor']['_notes'] = (
    'v3.2 (2026-03-31): access_status for persons, detailed character traits, '
    '3-step chronology check, ASR direct speech detection, detailed locations. '
    'Upgraded from v3.1.'
)

cfg['_updated'] = '2026-03-31'

with open('/opt/glava/prompts/pipeline_config.json', 'w', encoding='utf-8') as f:
    json.dump(cfg, f, ensure_ascii=False, indent=2)

print('pipeline_config.json updated OK')
print('  cover_designer ->',  cfg['cover_designer']['prompt_file'])
print('  interview_architect ->', cfg['interview_architect']['prompt_file'])
print('  fact_extractor ->', cfg['fact_extractor']['prompt_file'])
