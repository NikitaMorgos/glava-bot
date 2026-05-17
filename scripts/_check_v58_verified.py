import json
from pathlib import Path

out = Path('collab/runs/karakulina_v58')

# Task 044
ro = json.loads((out / 'karakulina_v58b_relation_overrides_applied_20260517_133149.json').read_text('utf-8'))
print('=== TASK 044: RELATION OVERRIDES ===')
corrections = ro.get('corrections', [])
print(f'Corrections count: {len(corrections)}')
for c in corrections:
    print(f'  {c}')

pn = json.loads((out / 'karakulina_v58b_persona_notes_enforced_20260517_133149.json').read_text('utf-8'))
print(f'Persona notes changes: {pn.get("changes_count", 0)}')
for l in pn.get('log', [])[:5]:
    print(f'  {l}')

# Task 045
ta = json.loads((out / 'karakulina_v58b_timeline_anchors_20260517_133149.json').read_text('utf-8'))
print()
print('=== TASK 045: TIMELINE ANCHORS ===')
v = ta.get('validation', ta)
print(f'anchors_found: {v.get("anchors_found", [])}')
print(f'anchors_missing: {v.get("anchors_missing", [])}')
print(f'merges: {v.get("merges", [])}')
print(f'periods: {v.get("periods_count", "?")} / {v.get("min_periods", 7)}')

# Task 043
sc = json.loads((out / 'karakulina_v58b_style_checks_20260517_133149.json').read_text('utf-8'))
print()
print('=== TASK 043: STYLE CHECKS ===')
stops = sc.get('epilogue_stop_phrases', {})
print(f'Stop-phrase errors: {stops.get("errors_count", 0)}, warnings: {stops.get("warnings_count", 0)}')
for h in stops.get('issues', [])[:5]:
    print(f'  [{h["severity"]}] [{h["chapter_id"]}] {h["phrase"]}')
awk = sc.get('awkward_formulation', {})
print(f'Awkward formulation: {awk.get("issues_count", 0)} issues')

# Task 038
gc = json.loads((out / 'karakulina_v58b_gw_grounding_check_20260517_133149.json').read_text('utf-8'))
print()
print('=== TASK 038: GW GROUNDING CHECK ===')
print(f'critical_errors: {gc.get("critical_errors", 0)}')
print(f'hn_grounding: {gc.get("historical_note_grounding", {})}')
print(f'motivation: {gc.get("motivation_attributions", {})}')

# Task 041
pc = json.loads((out / 'karakulina_v58b_pin_coverage_20260517_133149.json').read_text('utf-8'))
print()
print('=== TASK 041: PIN COVERAGE ===')
s = pc.get('summary', {})
print(f'full={s.get("full", 0)}, partial={s.get("partial", 0)}, skipped={s.get("skipped", 0)}, total={s.get("total", 0)}')
print('Skipped episodes:')
for ep in pc.get('episodes', []):
    if ep.get('coverage') == 'skipped':
        print(f'  SKIP: {ep.get("title","?")} [{ep.get("episode_id","?")}]')
