import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

out = Path('collab/runs/karakulina_v58')

# Fix: check v58c files
pc = json.loads((out / 'karakulina_v58c_pin_coverage_20260517_134304.json').read_text('utf-8'))
s = pc.get('summary', {})
print('=== TASK 041: PIN COVERAGE (v58c) ===')
print(f'full={s.get("full", 0)}, partial={s.get("partial", 0)}, skipped={s.get("skipped", 0)}, total={s.get("total", 0)}')
print(f'char_words: {s.get("characteristic_words_found",0)}/{s.get("characteristic_words_total",0)}')
print()
print('Full coverage episodes:')
for ep in pc.get('episodes', []):
    if ep.get('coverage') == 'full':
        print(f'  FULL: {ep.get("title","?")[:60]} [{ep.get("episode_id","?")}]')
print()
print('Partial coverage:')
for ep in pc.get('episodes', []):
    if ep.get('coverage') == 'partial':
        print(f'  PARTIAL({ep.get("markers_found","?")}/{ep.get("markers_total","?")}): {ep.get("title","?")[:60]}')
print()
print('Skipped (0 markers found):')
for ep in pc.get('episodes', []):
    if ep.get('coverage') == 'skipped':
        print(f'  SKIP: {ep.get("title","?")[:60]}')

# Task 044 v58c
ro = json.loads((out / 'karakulina_v58c_relation_overrides_applied_20260517_134304.json').read_text('utf-8'))
print()
print('=== TASK 044 (v58c) ===')
print(f'Corrections: {len(ro.get("corrections", []))}')
pn = json.loads((out / 'karakulina_v58c_persona_notes_enforced_20260517_134304.json').read_text('utf-8'))
print(f'Persona notes changes: {pn.get("changes_count", 0)}')

# Task 043 v58c
sc = json.loads((out / 'karakulina_v58c_style_checks_20260517_134304.json').read_text('utf-8'))
stops = sc.get('epilogue_stop_phrases', {})
print()
print('=== TASK 043 (v58c) ===')
print(f'Stop errors={stops.get("errors_count",0)}, warnings={stops.get("warnings_count",0)}')
for h in stops.get('issues', []):
    print(f'  [{h["severity"]}] {h["chapter_id"]}: "{h["phrase"]}"')

# Task 045 v58c
ta = json.loads((out / 'karakulina_v58c_timeline_anchors_20260517_134304.json').read_text('utf-8'))
print()
print('=== TASK 045 (v58c) ===')
print(json.dumps(ta, ensure_ascii=False, indent=2)[:600])
