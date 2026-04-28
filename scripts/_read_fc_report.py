#!/usr/bin/env python3
import json
from pathlib import Path

fc2 = Path('/opt/glava/exports/karakulina_full_20260413_042555/karakulina_phase_b_fc_report_iter2_20260413_044442.json')
d = json.loads(fc2.read_text())
errs = d.get('errors', [])
print(f"Вердикт: {d.get('verdict','?').upper()}")
print(f"Всего ошибок: {len(errs)}")
print()
for e in errs:
    sev = e.get('severity','?')
    typ = e.get('type','?')
    ch  = e.get('chapter_id','?')
    desc = e.get('description','')[:100]
    fix  = e.get('suggested_fix','')[:80]
    print(f"[{sev}][{typ}] {ch}")
    print(f"  Описание: {desc}")
    print(f"  Правка:   {fix}")
    print()
