import json, glob, os
from pathlib import Path

run_dir = sorted(glob.glob('/opt/glava/exports/karakulina_v32_run_*'))[-1]
print(f"Run dir: {run_dir}")
print()

# Stage 2 manifest
s2m = sorted(glob.glob(f'{run_dir}/karakulina_stage2_run_manifest_*.json'))
if s2m:
    m = json.load(open(s2m[0]))
    cfg = m.get('active_prompts', {})
    notes = m.get('notes', {})
    print("=== Stage 2 manifest ===")
    for role, info in cfg.items():
        if isinstance(info, dict):
            print(f"  {role}: {info.get('prompt_file','?')} temp={info.get('temperature','?')}")
    print(f"  skip_historian: {notes.get('skip_historian','?')}")
    print(f"  max_fc_iterations: {notes.get('max_fc_iterations','?')}")
    print()

# Stage 3 artifacts
s3 = sorted(glob.glob(f'/opt/glava/exports/karakulina_v32_book_FINAL_stage3_*.json'))
if s3:
    print(f"Stage 3 FINAL: {os.path.basename(s3[0])} ({os.path.getsize(s3[0])//1024}KB)")

# FC iterations
for i in range(1, 4):
    fc = sorted(glob.glob(f'{run_dir}/karakulina_fc_report_iter{i}_*.json'))
    if fc:
        r = json.load(open(fc[0]))
        errs = [e for e in r.get('errors',[]) if e.get('severity') in ('critical','major')]
        print(f"FC iter{i}: {r.get('verdict','?')} | critical+major: {len(errs)}")

# Phase B artifacts
pb = sorted(glob.glob(f'{run_dir}/*phase_b*.json'))
print(f"\nPhase B artifacts: {[os.path.basename(f) for f in pb]}")
