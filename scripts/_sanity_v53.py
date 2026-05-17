import json, sys, os, subprocess
os.chdir('/opt/glava')
sys.path.insert(0, '/opt/glava')

# 1. Active prompt versions
cfg = json.load(open('prompts/pipeline_config.json', encoding='utf-8'))
print('GW:', cfg['ghostwriter']['prompt_file'])
print('FC:', cfg['fact_checker']['prompt_file'])
print('LD:', cfg['layout_designer']['prompt_file'])

# 2. merge_revision_out_of_scope_chapters function exists
from pipeline_utils import merge_revision_out_of_scope_chapters
print('merge_revision_out_of_scope_chapters: OK')

# 3. EVIDENCE_MIN_SHARED_TOKENS still 2
from pipeline_utils import EVIDENCE_MIN_SHARED_TOKENS
print('EVIDENCE_MIN_SHARED_TOKENS:', EVIDENCE_MIN_SHARED_TOKENS)
