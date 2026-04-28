import re
from pathlib import Path

log = (Path('/opt/glava/collab/runs/karakulina_v31_20260421_042318') / 'run.log').read_text(errors='replace')

patterns = {
    'Cleaner':           r'(?:Cleaner|Клинер).*?за (\d+[\.,]\d+)с',
    'FactExtractor':     r'(?:Фактолог|Fact[\s_]?[Ee]xtractor).*?за (\d+[\.,]\d+)с',
    'Historian':         r'(?:Историк|[Hh]istorian).*?за (\d+[\.,]\d+)с',
    'Ghostwriter':       r'(?:Писатель|[Gg]hostwriter).*?за (\d+[\.,]\d+)с',
    'FactChecker':       r'(?:Фактчекер|Fact[\s_]?[Cc]hecker).*?за (\d+[\.,]\d+)с',
    'LiteraryEditor':    r'(?:Лит[\.\s]?ред|Literary[\s_]?[Ee]ditor).*?за (\d+[\.,]\d+)с',
    'Proofreader':       r'(?:Корректор|[Pp]roofreader).*?за (\d+[\.,]\d+)с',
}

print("Timings from log:")
for role, pat in patterns.items():
    m = re.findall(pat, log)
    print(f"  {role}: {m}")

# FC verdicts
fc_v = re.findall(r'Итерация (\d+).*?(PASS|FAIL).*?Critical\+Major: (\d+)', log)
print("\nFC verdicts by iteration:", fc_v)

# DONE markers
done = re.findall(r'(?:Phase B завершён|DONE:.*karakulina)', log)
print("DONE markers:", done)

# Stage markers from run.log
stage_markers = re.findall(r'>>> (STAGE \d+|PHASE [AB]):', log)
print("Stage markers:", stage_markers)
