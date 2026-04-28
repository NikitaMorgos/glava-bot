import json
from pathlib import Path

RUN = Path('/opt/glava/collab/runs/karakulina_v31_20260421_042318')
EXPORTS = Path('/opt/glava/exports/karakulina_v31_run_20260421_042318')

for mf_name, path in [
    ('s2', RUN / 'run_manifest_s2.json'),
    ('s3', RUN / 'run_manifest_s3.json'),
]:
    m = json.load(open(path))
    print(f"\n=== Manifest {mf_name} ===")
    ap = m.get('active_prompts', {})
    print(f"active_prompts: {json.dumps(ap, ensure_ascii=False, indent=2)}")
    print(f"notes: {m.get('notes','')}")

pb_mf = sorted(EXPORTS.glob('*phase_b_run_manifest*.json'))
if pb_mf:
    m = json.load(open(pb_mf[0]))
    print(f"\n=== Phase B manifest ===")
    ap = m.get('active_prompts', {})
    print(f"active_prompts: {json.dumps(ap, ensure_ascii=False, indent=2)}")
    print(f"notes: {m.get('notes','')}")
