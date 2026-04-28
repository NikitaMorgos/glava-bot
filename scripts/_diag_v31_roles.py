import json, re
from pathlib import Path

RUN = Path('/opt/glava/collab/runs/karakulina_v31_20260421_042318')
EXPORTS = Path('/opt/glava/exports/karakulina_v31_run_20260421_042318')
LOG = RUN / 'run.log'

log = LOG.read_text(errors='replace')

# Helper: extract timing from log lines
def find_in_log(pattern):
    matches = re.findall(pattern, log)
    return matches

print("=== STAGE 1 ===")
# Cleaner
cleaner = re.findall(r'[Cc]leaner.*?(\d+\.\d+)с|[Cc]leaner.*?готово', log)
print("Cleaner:", cleaner[:3])

# Fact Extractor
fe = re.findall(r'(?:Фактолог|Fact.?Extractor).*?за (\d+\.\d+)с.*?токены.*?in=(\d+).*?out=(\d+)', log)
fe_ver = re.findall(r'Загружен (02[_a-z0-9\.]*\.md)', log)
print("FactExtractor timing:", fe[:2])
print("FactExtractor prompt:", fe_ver)

print("\n=== STAGE 2 ===")
# Historian
hist = re.findall(r'(?:Историк|[Hh]istorian).*?за (\d+\.\d+)с', log)
hist_ver = re.findall(r'Загружен (02b[_a-z0-9\.]*\.md|07[_a-z0-9\.]*\.md)', log)
print("Historian timing:", hist[:2])
print("Historian prompt:", hist_ver)

# Ghostwriter
gw = re.findall(r'(?:Писатель|[Gg]hostwriter).*?за (\d+\.\d+)с.*?токены.*?in=(\d+).*?out=(\d+)', log)
gw_ver = re.findall(r'Загружен (03[_a-z0-9\.]*\.md)', log)
print("Ghostwriter timing:", gw[:3])
print("Ghostwriter prompt:", gw_ver)

# FC Stage 2
fc_s2 = re.findall(r'(?:Фактчекер|Fact.?[Cc]hecker).*?за (\d+\.\d+)с.*?итерация[= ]+(\d+)', log)
fc_s2_ver = re.findall(r'Загружен (04[_a-z0-9\.]*\.md)', log)
fc_s2_verdict = re.findall(r'\[FACT_CHECKER\] Итерация \d+: (\w+)', log)
print("FC timing:", fc_s2[:4])
print("FC prompt:", fc_s2_ver)
print("FC verdicts:", fc_s2_verdict)

print("\n=== STAGE 3 ===")
# Literary Editor
le = re.findall(r'(?:Лит.?ред|Literary.?[Ee]ditor).*?за (\d+\.\d+)с', log)
le_ver = re.findall(r'Загружен (05[_a-z0-9\.]*\.md)', log)
print("LitEditor:", le[:2], "prompt:", le_ver)

# Proofreader
pr = re.findall(r'(?:Корректор|[Pp]roofreader).*?за (\d+\.\d+)с', log)
pr_ver = re.findall(r'Загружен (06[_a-z0-9\.]*\.md)', log)
print("Proofreader:", pr[:2], "prompt:", pr_ver)

print("\n=== MANIFESTS ===")
# Check run manifests
for mf in ['run_manifest_s2.json', 'run_manifest_s3.json']:
    mf_path = RUN / mf
    if mf_path.exists():
        m = json.load(open(mf_path))
        print(f"\n{mf}:")
        for k in ('roles', 'agents', 'steps', 'stages'):
            if k in m:
                print(f"  {k}: {m[k]}")
        # Show all keys
        print(f"  keys: {list(m.keys())[:15]}")

# Phase B manifest
pb_mf = list(EXPORTS.glob('*phase_b_run_manifest*.json'))
if pb_mf:
    m = json.load(open(pb_mf[0]))
    print(f"\nPhase B manifest keys: {list(m.keys())[:15]}")
    for k in ('roles', 'agents', 'ghostwriter_prompt', 'fc_iterations'):
        if k in m:
            print(f"  {k}: {m[k]}")
