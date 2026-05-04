#!/usr/bin/env python3
import json, sys

# Check fact_map checkpoint
ck = json.load(open('/opt/glava/checkpoints/karakulina/fact_map.json'))
content = ck.get('content', ck)
ps = content.get('persons', [])
print(f'fact_map checkpoint: approved_at={ck.get("approved_at", "N/A")}, persons={len(ps)}')

# Check the input fact_map from last Stage 1 run
import glob, os
fms = sorted(glob.glob('/opt/glava/exports/karakulina_input_fact_map_checkpoint_*.json'))
if fms:
    last_fm = fms[-1]
    fm2 = json.load(open(last_fm))
    c2 = fm2.get('content', fm2)
    p2 = c2.get('persons', [])
    print(f'Last input fact_map: {os.path.basename(last_fm)}, persons={len(p2)}')
    for p in p2[:5]:
        print(f'  {json.dumps({"name": p.get("name"), "relation": p.get("relation")}, ensure_ascii=False)}')

# Check what transcript is available
transcripts = sorted(glob.glob('/opt/glava/exports/*transcript*'))
print('\nTranscripts:')
for t in transcripts[-5:]:
    print(f'  {os.path.basename(t)}')

# Check pipeline_config for Stage 2 script
cfg = json.load(open('/opt/glava/prompts/pipeline_config.json'))
gw_cfg = cfg.get('ghostwriter', {})
print(f'\nGhostwriter: model={gw_cfg.get("model")}, prompt={gw_cfg.get("prompt_file")}')
