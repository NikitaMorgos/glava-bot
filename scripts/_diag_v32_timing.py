import json, glob, os, re
from pathlib import Path

run_dir = sorted(glob.glob('/opt/glava/exports/karakulina_v32_run_*'))[-1]

# Stage 2 manifest for timing
s2m = sorted(glob.glob(f'{run_dir}/karakulina_stage2_run_manifest_*.json'))
if s2m:
    m = json.load(open(s2m[0]))
    notes = m.get('notes', {})
    print("S2 notes:", json.dumps(notes, ensure_ascii=False, indent=2))

# Stage 1 manifest
s1m = sorted(glob.glob(f'{run_dir}/karakulina_stage1_full_run_manifest_*.json'))
if s1m:
    m1 = json.load(open(s1m[0]))
    print("S1 ts:", m1.get('timestamp'))

# Log timings
log = open(f'{run_dir}/run.log').read()

# Extract role timings from log
patterns = {
    'Cleaner':         r'Cleaner.*?за (\d+\.?\d*)с',
    'FactExtractor':   r'FactExtractor.*?за (\d+\.?\d*)с|Fact.Extractor.*?за (\d+\.?\d*)с|Готово за (\d+\.?\d*)с.*fact_map',
    'Historian':       r'\[HISTORIAN\].*?за (\d+\.?\d*)с|Историк.*?(\d+\.?\d*)с',
    'GW1':             r'Ghostwriter.*pass1.*?(\d+\.?\d*)с|Писатель.*?(\d+\.?\d*)с',
    'Stage1_start':    r'STAGE 1',
    'Stage2_start':    r'STAGE 2',
    'Stage3_start':    r'stage3|Stage 3|Этап 3',
}

# Simple grep approach
for label in ['Cleaner', 'Fact Extractor', 'HISTORIAN', 'GHOSTWRITER', 'FACT_CHECKER', 'LITERARY EDITOR', 'Proofreader', 'Literary']:
    matches = re.findall(rf'\[{label}[^\]]*\].*?за (\d+\.?\d*)с', log)
    if matches:
        print(f"{label}: {matches}")

# Find all "за Nс" lines
timing_lines = [l for l in log.split('\n') if 'за ' in l and 'с |' in l]
for tl in timing_lines[:20]:
    print(tl.strip())
