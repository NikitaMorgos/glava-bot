#!/usr/bin/env python3
import json
from pathlib import Path

fc2 = Path('/opt/glava/exports/karakulina_full_20260413_042555/karakulina_phase_b_fc_report_iter2_20260413_044442.json')
d = json.loads(fc2.read_text())
print(json.dumps(d.get('errors', [])[:3], ensure_ascii=False, indent=2))
print()
print("summary:", d.get('summary', d.get('comment', '')))
