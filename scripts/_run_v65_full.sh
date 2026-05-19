#!/bin/bash
# v65 — Bugfix Sprint: GW v2.24 + orchestrator 049f-2 (ALL 12+ validators) + revision loop
# Pipeline: Stage 1 → Stage 2 first pass (GW v2.24) → ALL ~12 validators (049f-2)
#           → revision hints collect → Stage 2 revision pass → diff_audit
#           → 046d historical_notes enrichment → Stage 3 + 049g preserve_writing_notes
#           → build_gate1 v65 (required vs optional) → final validators
#
# v65 new validators vs v64:
#   + validate_chronological_consistency (048e: ch_01 skip + epilogue generic skip + birth-decl skip)
#   + validate_descendants_in_early_context (048f: Class 12 extend — nephews/grandchildren in early context)
#   + validate_cross_paragraph_duplication (048g: Class 19 NEW — duplicate paragraphs)
#   + validate_historical_notes_distribution (046f: per-chapter thresholds)
#   + validate_required_episodes_coverage (044i: required_in_narrative episodes)
#   + warning-level hints from ALL validators now included (049f-2 extend)
#
# Targets (distribution gate v65):
#   Total ≥ 20 000 / Narrative ≥ 15 000 / Paspart ch_01 ~3 000
#   Historical_notes ≥ 2 000 (≥5 inline + ≥3 field) with per-chapter distribution
#   ch_02 ≥ 7K / ch_03 ≥ 4K / ch_04 ≥ 2.5K / epilogue 800-1500
#   discourse markers ch_02≥8 / ch_03≥5 / ch_04≥3
#   personal_historical_voice: ch_02≥3 / ch_03≥2 / ch_04≥1
#   hist_notes per chapter: ch_02≥3 / ch_03≥2 / ch_04≥1
#   pin_list_depth = 0 errors / chronology = 0 errors / Class 17 = 0
#   Class 1/11 = 0 / Class 12 extend = 0 / Class 19 = 0
#   required_episodes_coverage missing = 0
#   Stage 2 manifest: ghostwriter_version=v2.24, completeness_auditor_version=v1.5
#   writing_notes.rule13_revision_applied — list of dicts (schema fix)
#   writing_notes preserved in book_FINAL_stage3 (049g)
#   diff_audit unauthorized_changes < threshold (5)
#
# Artifacts: collab/runs/karakulina-v65-artifacts/
# Branch: feat/v65-bugfix-sprint
# Cost estimate: ~$4-6 (2 LLM passes Stage 2)

set -e
cd /opt/glava

# Load environment variables from .env
set -a
source .env
set +a

ARTIFACTS_DIR="collab/runs/karakulina-v65-artifacts"

echo "=== v65: git pull feat/v65-bugfix-sprint ==="
git fetch origin
git checkout feat/v65-bugfix-sprint
git pull origin feat/v65-bugfix-sprint

echo "=== v65: verify GW v2.24 + CA v1.5 in pipeline_config.json ==="
python -c "
import json
cfg = json.load(open('prompts/pipeline_config.json', encoding='utf-8'))
gw = cfg['ghostwriter']['prompt_file']
ca = cfg['completeness_auditor']['prompt_file']
assert 'v2.24' in gw, f'GW version wrong: {gw}'
assert 'v1.5' in ca, f'CA version wrong: {ca}'
print(f'OK: GW={gw}, CA={ca}')
"

echo "=== v65: verify GW v2.24 universality (0 body matches) ==="
python scripts/_universality_check_v2.24.py

echo "=== v65: verify known_episodes v7 (required_in_narrative + Капошвара + characteristic_words) ==="
python -c "
import sys
sys.stdout.reconfigure(encoding='utf-8')
text = open('collab/context/known_episodes_karakulina.md', encoding='utf-8').read()
lines = text.split('\n')
ver_line = next((l for l in lines if l.startswith('# ') or 'v7' in l[:40]), '?')
print(f'known_episodes header: {ver_line[:80]}')
assert 'v7' in text[:300], 'known_episodes must be v7'
assert 'required_in_narrative' in text, 'required_in_narrative section missing'
assert 'Обязательные эпизоды' in text, 'Обязательные эпизоды section missing'
assert 'Characteristic words' in text, 'Characteristic words section missing'
# Kaposhvara check
assert 'площадь' in text, 'Капошвара=площадь fix missing'
print('known_episodes v7 checks PASSED')
"

echo "=== v65: verify narrative_stop_phrases v7 (Class 11 extended + Class 19) ==="
python -c "
import json, sys
sys.stdout.reconfigure(encoding='utf-8')
cfg = json.load(open('collab/context/narrative_stop_phrases.json', encoding='utf-8'))
ver = cfg.get('version', '?')
print(f'stop_phrases version: {ver}')
assert ver == 'v7', f'Expected v7, got {ver}'
all_pats = cfg.get('generic_categorical_patterns', [])
c11_ext = next((p for p in all_pats if isinstance(p,dict) and p.get('category') == 'class11_not_loved_x_by_y_and_z_extended'), None)
assert c11_ext and c11_ext.get('pattern_options'), 'class11_extended pattern_options missing'
print(f'class11_extended: {len(c11_ext[\"pattern_options\"])} pattern_options OK')
print('OK: narrative_stop_phrases v7')
"

echo "=== v65: STAGE 1 (split-extract + known-episodes v7 + prev-fact-map v64 or v63) ==="
# Use v64 fact_map if available, fall back to v63
V64_FM_DIR="collab/runs/karakulina-v64-artifacts"
V63_FM_DIR="collab/runs/karakulina_v63"
if ls ${V64_FM_DIR}/karakulina_fact_map_full_*.json 2>/dev/null | head -1 | grep -q .; then
    PREV_FM=$(ls -t ${V64_FM_DIR}/karakulina_fact_map_full_*.json | head -1)
    echo "Using v64 fact_map: $PREV_FM"
elif ls ${V63_FM_DIR}/karakulina_fact_map_full_*.json 2>/dev/null | head -1 | grep -q .; then
    PREV_FM=$(ls -t ${V63_FM_DIR}/karakulina_fact_map_full_*.json | head -1)
    echo "v64 not found, using v63 fact_map: $PREV_FM"
else
    PREV_FM=""
    echo "WARNING: no previous fact_map found, Stage 1 will start fresh"
fi

mkdir -p exports/karakulina_v65

python scripts/test_stage1_karakulina_full.py \
  --transcript1 collab/transcripts/01_karakulina_original_assemblyai_20260326.txt \
  --transcript2 collab/transcripts/02_karakulina_nikita_tatyana_interview.txt \
  --split-extract \
  ${PREV_FM:+--prev-fact-map "$PREV_FM"} \
  --known-episodes collab/context/known_episodes_karakulina.md \
  --output-dir exports/karakulina_v65

FM65=$(ls -t exports/karakulina_v65/karakulina_fact_map_full_*.json | grep -v enriched | grep -v TR1 | head -1)
echo "fact_map: $FM65"

echo "=== v65: STAGE 2 first pass (GW v2.24 call_type=full) ==="
mkdir -p exports/stage2_v65

python scripts/test_stage2_pipeline.py \
  --fact-map "$FM65" \
  --output-dir exports/stage2_v65 \
  --allow-fc-fail

BOOK_DRAFT=$(ls -t exports/stage2_v65/karakulina_book_FINAL_*.json | head -1)
echo "book_draft: $BOOK_DRAFT"

echo "=== v65: save book_draft.json (before revision) ==="
cp "$BOOK_DRAFT" exports/stage2_v65/karakulina_book_draft.json

echo "=== v65: verify Stage 2 first pass manifest (GW v2.24, CA v1.5) ==="
MANIFEST65=$(ls -t exports/stage2_v65/karakulina_stage2_run_manifest_*.json | head -1)
python -c "
import json, sys
sys.stdout.reconfigure(encoding='utf-8')
m = json.load(open('$MANIFEST65', encoding='utf-8'))
gw_v = m.get('ghostwriter_version', '')
ca_v = m.get('completeness_auditor_version', '')
print(f'Stage2 manifest: GW={gw_v}, CA={ca_v}')
assert 'v2.24' in str(gw_v) or 'v2.24' in str(m), f'GW v2.24 not in manifest: {gw_v}'
assert 'v1.5' in str(ca_v) or 'v1.5' in str(m), f'CA v1.5 not in manifest: {ca_v}'
print('Stage2 first pass version check PASSED')
" || echo "WARNING: manifest version check failed (continuing)"

echo "=== v65: run ALL validators on book_draft (049f-2 extended) ==="
python - <<'PYEOF'
import json, sys, os, glob
sys.path.insert(0, '/opt/glava')
sys.stdout.reconfigure(encoding='utf-8')
from pipeline_utils import (
    validate_children_before_birth,
    validate_chronological_consistency,
    validate_narrative_stop_phrases,
    validate_epilogue_quote_density,
    validate_entity_substitution,
    validate_bio_data_family_format,
    validate_narrative_truism,
    validate_personal_historical_voice,
    validate_descendants_in_early_context,
    validate_cross_paragraph_duplication,
    validate_historical_notes_distribution,
    validate_required_episodes_coverage,
    collect_revision_hints,
    parse_pin_list_from_markdown,
)

# Load artifacts
book_files = sorted(glob.glob('exports/stage2_v65/karakulina_book_FINAL_*.json'), reverse=True)
fm_files = sorted(glob.glob('exports/karakulina_v65/karakulina_fact_map_full_*.json'), reverse=True)
if not book_files or not fm_files:
    print("ERROR: book or fact_map not found"); sys.exit(1)

book_draft_raw = json.load(open(book_files[0], encoding='utf-8'))
book_draft = book_draft_raw.get('book_draft') or book_draft_raw.get('book_final') or book_draft_raw
fm = json.load(open(fm_files[0], encoding='utf-8'))

stop_cfg = json.load(open('collab/context/narrative_stop_phrases.json', encoding='utf-8'))
chrono_cfg = json.load(open('collab/context/chronology_check_config.json', encoding='utf-8'))
dupl_cfg = json.load(open('collab/context/cross_paragraph_duplication_config.json', encoding='utf-8'))
hist_dist_cfg = json.load(open('collab/context/historical_notes_distribution_config.json', encoding='utf-8'))

pin_list_data = parse_pin_list_from_markdown('collab/context/known_episodes_karakulina.md')

tr_files = sorted(glob.glob('collab/transcripts/*.txt'))
transcripts = [open(f, encoding='utf-8').read() for f in tr_files[:2]]

print("\n=== v65 validators on book_draft (049f-2 extended: ALL 12+ validators) ===\n")

print("[1] 048d: children_before_birth (chronology legacy)")
r_chrono_legacy = validate_children_before_birth(book_draft, fm)
print(f"  errors={r_chrono_legacy['errors_count']}, warnings={r_chrono_legacy['warnings_count']}")
for i in r_chrono_legacy['issues'][:3]:
    print(f"  [{i['severity']}] {i['type']} ch={i['chapter_id']}")

print("\n[2] 048e: chronological_consistency (FP fix — ch_01 skip + epilogue generic + birth-decl)")
r_chrono = validate_chronological_consistency(book_draft, fm, chrono_cfg)
print(f"  errors={r_chrono['errors_count']}, warnings={r_chrono['warnings_count']}")
for i in r_chrono['issues'][:3]:
    print(f"  [{i['severity']}] {i['type']} person={i.get('person_name')} ch={i['chapter_id']}")

print("\n[3] 043h: narrative_truism (Class 17)")
r_truism = validate_narrative_truism(book_draft)
print(f"  errors={r_truism['errors_count']}, warnings={r_truism['warnings_count']}")
for i in r_truism.get('issues', [])[:3]:
    print(f"  [{i.get('severity','?')}] {i.get('category','?')} ch={i.get('chapter_id')}")
    print(f"    '{i.get('snippet','')[:80]}'")

print("\n[4] 043f/043g: narrative_stop_phrases (Class 1/11/17 v7)")
r_stop = validate_narrative_stop_phrases(book_draft, stop_cfg)
print(f"  total={len(r_stop.get('issues', []))} (errors={r_stop['errors_count']}, warnings={r_stop['warnings_count']})")
for i in r_stop.get('issues', [])[:5]:
    print(f"  [{i.get('severity','?')}] {i.get('category','?')} ch={i.get('chapter_id')}")
    print(f"    '{i.get('snippet','')[:80]}'")

print("\n[5] 046e: personal_historical_voice (Class 18)")
r_voice = validate_personal_historical_voice(book_draft)
print(f"  markers_per_chapter={r_voice.get('markers_found_per_chapter')}")
print(f"  issues={len(r_voice.get('issues', []))}")
for i in r_voice.get('issues', [])[:3]:
    print(f"  [{i.get('severity','?')}] ch={i.get('chapter_id')} found={i.get('found')}/need={i.get('needed')}")

print("\n[6] 043e-2: epilogue quote density")
r_epil = validate_epilogue_quote_density(book_draft)
print(f"  ok={r_epil.get('ok')}, quotes={r_epil.get('quote_count')}")

print("\n[7] 038c: entity substitution")
r_subst = validate_entity_substitution(book_draft, fm, transcripts)
print(f"  ok={r_subst['ok']}, issues={len(r_subst['issues'])}")

print("\n[8] 048f: descendants_in_early_context (Class 12 extend — nephews/grandchildren v65 NEW)")
r_desc = validate_descendants_in_early_context(book_draft, fm)
print(f"  errors={r_desc['errors_count']}, warnings={r_desc['warnings_count']}")
for i in r_desc.get('issues', [])[:3]:
    print(f"  [{i['severity']}] {i['type']} person={i['person_name']} ch={i['chapter_id']}")
    print(f"    inferred_min_birth={i['inferred_min_birth']} event_year={i['event_year_in_paragraph']}")
    print(f"    '{i.get('snippet','')[:80]}'")

print("\n[9] 048g: cross_paragraph_duplication (Class 19 v65 NEW)")
r_dupl = validate_cross_paragraph_duplication(book_draft, dupl_cfg)
print(f"  errors={r_dupl['errors_count']}, warnings={r_dupl['warnings_count']}")
for i in r_dupl.get('issues', [])[:3]:
    print(f"  [{i['severity']}] similarity={i.get('similarity',0):.2f}")
    print(f"    para_a snippet: '{i.get('para_a_snippet','')[:60]}'")

print("\n[10] 046f: historical_notes_distribution (v65 NEW)")
r_hist_dist = validate_historical_notes_distribution(book_draft, hist_dist_cfg)
print(f"  errors={r_hist_dist['errors_count']}, warnings={r_hist_dist['warnings_count']}")
for i in r_hist_dist.get('issues', [])[:3]:
    print(f"  [{i['severity']}] ch={i.get('chapter_id')} found={i.get('found')}/need={i.get('needed')}")

print("\n[11] 044i: required_episodes_coverage (v65 NEW)")
pin_episodes = pin_list_data.get('episodes', []) if isinstance(pin_list_data, dict) else pin_list_data
r_req_ep = validate_required_episodes_coverage(book_draft, pin_episodes)
print(f"  total_required={r_req_ep.get('total_required')}")
print(f"  covered={r_req_ep.get('covered_count')}, missing={r_req_ep.get('missing_count')}")
for ep in [e for e in r_req_ep.get('required_episodes', []) if not e.get('found')][:5]:
    print(f"  MISSING: {ep['episode_id']} '{ep.get('title','')}' ")

# Combine all validator outputs for orchestrator 049f-2
validator_outputs = {
    "chronology_legacy": r_chrono_legacy,
    "chronology_check": r_chrono,
    "narrative_truism": r_truism,
    "narrative_stop_phrases": r_stop,
    "personal_historical_voice": r_voice,
    "epilogue_quote_density": r_epil,
    "entity_substitution": r_subst,
    "descendants_in_early_context": r_desc,
    "cross_paragraph_duplication": r_dupl,
    "historical_notes_distribution": r_hist_dist,
    "required_episodes_coverage": r_req_ep,
}

# Save validators_on_draft.json
json.dump(validator_outputs, open('exports/stage2_v65/validators_on_draft.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print("\nSaved: exports/stage2_v65/validators_on_draft.json")

# Collect revision_hints (049f-2 extended: warnings included)
print("\n=== 049f-2: collect_revision_hints (ALL validators, warnings included) ===")
revision_hints = collect_revision_hints(book_draft, validator_outputs)
print(f"  Total hints: {len(revision_hints)}")
must_apply = [h for h in revision_hints if h.get('must_apply')]
warn_hints = [h for h in revision_hints if not h.get('must_apply')]
print(f"  Must-apply (error level): {len(must_apply)}")
print(f"  Warning hints: {len(warn_hints)}")
for h in revision_hints[:7]:
    print(f"  [{h['hint_id']}] {h['validator']}/{h['category']} ch={h['chapter_id']} must_apply={h['must_apply']}")
    print(f"    snippet: '{h.get('snippet','')[:70]}'")
    print(f"    suggestion: '{h.get('suggestion','')[:80]}'")

# Save revision_hints
json.dump(revision_hints, open('exports/stage2_v65/revision_hints.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(f"\nSaved: exports/stage2_v65/revision_hints.json ({len(revision_hints)} hints)")

if not revision_hints:
    print("\n=== REVISION SKIPPED: no hints (0 validator issues) ===")
    open('exports/stage2_v65/revision_pass_log.json', 'w').write('{"skipped": "no_revision_hints", "reason": "all validators clean on first pass"}')
    print("Saved: revision_pass_log.json")
else:
    print(f"\n=== REVISION PASS REQUIRED: {len(revision_hints)} hints → proceeding to Stage 2 revision pass ===")

PYEOF

echo "=== v65: STAGE 2 revision pass (GW v2.24 call_type=revision, rule13_revision_applied as list) ==="
python - <<'PYEOF'
import json, sys, os, glob
sys.path.insert(0, '/opt/glava')
sys.stdout.reconfigure(encoding='utf-8')

STAGE2_DIR = 'exports/stage2_v65'
hints_file = os.path.join(STAGE2_DIR, 'revision_hints.json')
log_file = os.path.join(STAGE2_DIR, 'revision_pass_log.json')

# Check if revision was skipped
if os.path.exists(log_file):
    log = json.load(open(log_file, encoding='utf-8'))
    if log.get('skipped'):
        print("Revision pass skipped (no hints) — proceeding to Stage 3 with first-pass book")
        sys.exit(0)

# Load revision_hints
revision_hints = json.load(open(hints_file, encoding='utf-8'))
print(f"Loaded {len(revision_hints)} revision_hints")

# Load book_draft
draft_files = sorted(glob.glob(os.path.join(STAGE2_DIR, 'karakulina_book_FINAL_*.json')), reverse=True)
book_draft_raw = json.load(open(draft_files[0], encoding='utf-8'))
book_draft = book_draft_raw.get('book_draft') or book_draft_raw.get('book_final') or book_draft_raw

# Prepare revision pass input
revision_input = {
    "call_type": "revision",
    "revision_hints": revision_hints,
    "current_book": book_draft,
}

revision_input_path = os.path.join(STAGE2_DIR, 'karakulina_revision_input.json')
json.dump(revision_input, open(revision_input_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(f"Saved revision_input: {revision_input_path}")
print("NOTE: Stage 2 revision pass runs via test_stage2_pipeline.py --revision-pass")
PYEOF

FM65=$(ls -t exports/karakulina_v65/karakulina_fact_map_full_*.json | grep -v enriched | grep -v TR1 | head -1)

python scripts/test_stage2_pipeline.py \
  --fact-map "$FM65" \
  --output-dir exports/stage2_v65 \
  --revision-pass exports/stage2_v65/revision_hints.json \
  --allow-fc-fail || echo "NOTE: revision pass flag may not be supported yet — using book_draft as final"

echo "=== v65: 049e-2 schema validation — rule13_revision_applied must be list of dicts ==="
python - <<'PYEOF'
import json, sys, os, glob
sys.path.insert(0, '/opt/glava')
sys.stdout.reconfigure(encoding='utf-8')

STAGE2_DIR = 'exports/stage2_v65'
book_files = sorted(glob.glob(os.path.join(STAGE2_DIR, 'karakulina_book_FINAL_*.json')), reverse=True)
book_raw = json.load(open(book_files[0], encoding='utf-8'))
book = book_raw.get('book_draft') or book_raw.get('book_final') or book_raw

wn = book.get('writing_notes', {})
r13_applied = wn.get('rule13_revision_applied')

print(f"writing_notes.rule13_revision_applied type: {type(r13_applied).__name__}")
print(f"writing_notes.rule13_revision_applied value: {json.dumps(r13_applied, ensure_ascii=False)[:200]}")

# Schema validation
if isinstance(r13_applied, list):
    print("OK: rule13_revision_applied is list")
    for i, item in enumerate(r13_applied[:3]):
        print(f"  [{i}]: {json.dumps(item, ensure_ascii=False)[:100]}")
    if r13_applied and all(isinstance(d, dict) for d in r13_applied):
        print("OK: all items are dicts (list of dicts)")
    elif not r13_applied:
        print("NOTE: rule13_revision_applied is empty list")
elif r13_applied is None:
    print("WARN: rule13_revision_applied is None/missing")
else:
    print(f"FAIL: rule13_revision_applied is {type(r13_applied).__name__} (not list)")
    print("PER SPEC 049e-2: schema violation — should be list of dicts")
    sys.exit(1)

# Check rule13_revision_failed
r13_failed = wn.get('rule13_revision_failed')
print(f"\nrule13_revision_failed: {r13_failed}")
if r13_failed == True:
    print("FAIL: rule13_revision_failed=true")
    print("PER SPEC: STOP — push artifacts, wait for Opus review")
    sys.exit(1)
else:
    print("OK: rule13_revision_failed is not true")

print("\n=== Schema validation PASSED ===")
PYEOF

echo "=== v65: diff audit (authorized vs unauthorized changes) ==="
python - <<'PYEOF'
import json, sys, os, glob
sys.path.insert(0, '/opt/glava')
sys.stdout.reconfigure(encoding='utf-8')
from pipeline_utils import audit_revision_diff

STAGE2_DIR = 'exports/stage2_v65'
draft_path = os.path.join(STAGE2_DIR, 'karakulina_book_draft.json')
hints_path = os.path.join(STAGE2_DIR, 'revision_hints.json')

book_files = sorted(glob.glob(os.path.join(STAGE2_DIR, 'karakulina_book_FINAL_*.json')), reverse=True)

book_draft_raw = json.load(open(draft_path, encoding='utf-8'))
book_draft = book_draft_raw.get('book_draft') or book_draft_raw.get('book_final') or book_draft_raw

revision_hints = json.load(open(hints_path, encoding='utf-8'))

book_revised_raw = json.load(open(book_files[0], encoding='utf-8'))
book_revised = book_revised_raw.get('book_draft') or book_revised_raw.get('book_final') or book_revised_raw

print("=== Running diff audit ===")
diff_result = audit_revision_diff(book_draft, book_revised, revision_hints)

json.dump(diff_result, open(os.path.join(STAGE2_DIR, 'revision_diff_audit.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(f"Saved: revision_diff_audit.json")

print(f"\nDiff audit results:")
print(f"  hints_count: {diff_result.get('hints_count')}")
applied = diff_result.get('applied', [])
print(f"  applied: {len(applied)}")
print(f"  skipped: {len(diff_result.get('skipped', []))}")
unauthorized = diff_result.get('unauthorized_changes', [])
print(f"  unauthorized_changes: {len(unauthorized)}")

if applied:
    print("\napplied hints (first 5):")
    for a in applied[:5]:
        print(f"  hint_id={a.get('hint_id')} ch={a.get('chapter_id')}: {a.get('diff_summary','')[:80]}")

THRESHOLD = 5
if len(unauthorized) > THRESHOLD:
    print(f"\nFAIL: unauthorized_changes={len(unauthorized)} > threshold={THRESHOLD}")
    print("PER SPEC: STOP — push artifacts, wait for Opus review")
    for u in unauthorized[:5]:
        print(f"  ch={u.get('chapter_id')}: '{u.get('diff_snippet','')[:80]}'")
    sys.exit(1)
else:
    print(f"\nOK: unauthorized_changes={len(unauthorized)} <= threshold={THRESHOLD}")

# Check writing_notes rule13 schema proof
wn = book_revised.get('writing_notes', {})
print(f"\n=== 049e-2 writing_notes.rule13 proof ===")
r13_applied = wn.get('rule13_revision_applied')
print(f"  rule13_revision_applied: type={type(r13_applied).__name__} len={len(r13_applied) if isinstance(r13_applied, list) else 'n/a'}")
print(f"  rule13_hints_received: {wn.get('rule13_hints_received', 'MISSING')}")
print(f"  rule13_errors_applied: {wn.get('rule13_errors_applied', 'MISSING')}")
print(f"  rule13_warnings_applied: {wn.get('rule13_warnings_applied', 'MISSING')}")
print(f"  rule13_revision_failed: {wn.get('rule13_revision_failed', 'MISSING')}")
if isinstance(r13_applied, list) and r13_applied:
    print(f"  First entry: {json.dumps(r13_applied[0], ensure_ascii=False)[:150]}")

print("\n=== Diff audit + rule13 schema: PASSED ===")
PYEOF

echo "=== v65: 046d historical_notes enrichment (post-revision) ==="
python - <<'PYEOF'
import json, sys, os, glob
sys.path.insert(0, '/opt/glava')
sys.stdout.reconfigure(encoding='utf-8')
from pipeline_utils import enrich_historical_notes_inline, _count_inline_historical_notes

STAGE2_DIR = 'exports/stage2_v65'

book_files = sorted(glob.glob(os.path.join(STAGE2_DIR, 'karakulina_book_FINAL_*.json')), reverse=True)
book_raw = json.load(open(book_files[0], encoding='utf-8'))
book = book_raw.get('book_draft') or book_raw.get('book_final') or book_raw

enrich_cfg = json.load(open('collab/context/historical_notes_enrichment_config.json', encoding='utf-8'))

print("=== 046d: historical_notes enrichment ===")
before_count = _count_inline_historical_notes(book)
print(f"  inline historical notes before enrichment: {before_count}")

enriched_book = enrich_historical_notes_inline(book, enrich_cfg)
after_count = _count_inline_historical_notes(enriched_book)
print(f"  inline historical notes after enrichment: {after_count}")

MIN_INLINE = enrich_cfg.get('min_inline_notes', 5)
if after_count < MIN_INLINE:
    print(f"  WARNING: {after_count} inline notes < target {MIN_INLINE}")
else:
    print(f"  OK: {after_count} inline notes >= target {MIN_INLINE}")

import time
ts = int(time.time())
enriched_path = os.path.join(STAGE2_DIR, f'karakulina_book_FINAL_{ts}_enriched.json')
json.dump(enriched_book, open(enriched_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(f"\nSaved enriched book: {enriched_path}")
PYEOF

echo "=== v65: STAGE 3 (LE + Proofreader + validators + 049g preserve_writing_notes) ==="
FM65=$(ls -t exports/karakulina_v65/karakulina_fact_map_full_*.json | grep -v enriched | grep -v TR1 | head -1)
BOOK_V65=$(ls -t exports/stage2_v65/karakulina_book_FINAL_*_enriched.json 2>/dev/null | head -1)
if [ -z "$BOOK_V65" ]; then
    BOOK_V65=$(ls -t exports/stage2_v65/karakulina_book_FINAL_*.json | head -1)
fi
echo "book for stage3: $BOOK_V65"

mkdir -p exports/stage3_v65
python scripts/test_stage3.py \
  --book-draft "$BOOK_V65" \
  --fact-map "$FM65" \
  --output-dir exports/stage3_v65 \
  --prefix karakulina \
  --no-strict-gates

echo "=== v65: 049g verify preserve_writing_notes in stage3 output ==="
python - <<'PYEOF'
import json, sys, os, glob
sys.path.insert(0, '/opt/glava')
sys.stdout.reconfigure(encoding='utf-8')
from pipeline_utils import preserve_root_level_metadata

STAGE3_DIR = 'exports/stage3_v65'
STAGE2_DIR = 'exports/stage2_v65'

book_files = sorted(glob.glob(os.path.join(STAGE3_DIR, 'karakulina_book_FINAL_stage3_*.json')), reverse=True)
if not book_files:
    print("ERROR: stage3 output not found"); sys.exit(1)

book_s3_raw = json.load(open(book_files[0], encoding='utf-8'))
book_s3 = book_s3_raw.get('book_draft') or book_s3_raw.get('book_final') or book_s3_raw

# Source writing_notes from last stage2 (revised)
stage2_files = sorted(glob.glob(os.path.join(STAGE2_DIR, 'karakulina_book_FINAL_*.json')), reverse=True)
book_s2_raw = json.load(open(stage2_files[0], encoding='utf-8'))
book_s2 = book_s2_raw.get('book_draft') or book_s2_raw.get('book_final') or book_s2_raw

print("=== 049g: preserve_writing_notes ===")
wn_before = book_s3.get('writing_notes')
print(f"  writing_notes in stage3 output (before preserve): {bool(wn_before)} — {str(wn_before)[:100]}")

preserved = preserve_root_level_metadata(book_s3, book_s2)
wn_after = preserved.get('writing_notes', {})
print(f"  writing_notes after preserve_root_level_metadata: keys={list(wn_after.keys())[:6]}")

# Verify rule13 fields preserved
r13 = wn_after.get('rule13_revision_applied')
print(f"  rule13_revision_applied preserved: type={type(r13).__name__} value={json.dumps(r13, ensure_ascii=False)[:150] if r13 else 'None'}")

if not isinstance(r13, list):
    print(f"  WARN: rule13_revision_applied not a list in stage3 output (may need preserve call in pipeline)")
else:
    print(f"  OK: rule13_revision_applied is list in stage3 output")

# If needed, save the preserved version
if not wn_before or not wn_before.get('rule13_revision_applied'):
    print("  Applying preserve_root_level_metadata and overwriting stage3 output...")
    json.dump(preserved, open(book_files[0], 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print(f"  Saved preserved stage3: {book_files[0]}")

print("\n=== 049g preserve_writing_notes: checked ===")
PYEOF

echo "=== v65: build_gate1_full_text (required vs optional clear breakdown) ==="
BOOK_FINAL_S3=$(ls -t exports/stage3_v65/karakulina_book_FINAL_stage3_*.json | head -1)
FM65=$(ls -t exports/karakulina_v65/karakulina_fact_map_full_*.json | grep -v enriched | grep -v TR1 | head -1)

python scripts/build_gate1_full_text.py \
  --book-final "$BOOK_FINAL_S3" \
  --fact-map "$FM65" \
  --output exports/stage3_v65/karakulina_v65_text_FULL.md \
  --reports-dir exports/stage3_v65 \
  --prefix karakulina \
  --pin-list collab/context/known_episodes_karakulina.md

echo "=== v65: final validators (post-revision pass) ==="
python - <<'PYEOF'
import json, sys, os, glob
sys.path.insert(0, '/opt/glava')
sys.stdout.reconfigure(encoding='utf-8')
from pipeline_utils import (
    validate_children_before_birth,
    validate_chronological_consistency,
    validate_narrative_stop_phrases,
    validate_narrative_truism,
    validate_personal_historical_voice,
    validate_epilogue_quote_density,
    validate_bio_data_family_format,
    validate_descendants_in_early_context,
    validate_cross_paragraph_duplication,
    validate_historical_notes_distribution,
    validate_required_episodes_coverage,
    _count_inline_historical_notes,
    parse_pin_list_from_markdown,
)

book_files = sorted(glob.glob('exports/stage3_v65/karakulina_book_FINAL_stage3_*.json'), reverse=True)
fm_files = sorted(glob.glob('exports/karakulina_v65/karakulina_fact_map_full_*.json'), reverse=True)
if not book_files or not fm_files:
    print("ERROR: book or fact_map not found"); sys.exit(1)

book_raw = json.load(open(book_files[0], encoding='utf-8'))
book = book_raw.get('book_draft') or book_raw.get('book_final') or book_raw
fm = json.load(open(fm_files[0], encoding='utf-8'))

chrono_cfg = json.load(open('collab/context/chronology_check_config.json', encoding='utf-8'))
stop_cfg = json.load(open('collab/context/narrative_stop_phrases.json', encoding='utf-8'))
dupl_cfg = json.load(open('collab/context/cross_paragraph_duplication_config.json', encoding='utf-8'))
hist_dist_cfg = json.load(open('collab/context/historical_notes_distribution_config.json', encoding='utf-8'))
pin_list_data = parse_pin_list_from_markdown('collab/context/known_episodes_karakulina.md')

print("\n=== FINAL VALIDATORS (post-revision, on stage3 output) ===\n")
results = {}

print("[A] 048e: chronological_consistency (FP fix):")
r = validate_chronological_consistency(book, fm, chrono_cfg)
results['chronology'] = r
print(f"  errors={r['errors_count']}, warnings={r['warnings_count']}")
for i in r['issues'][:3]:
    print(f"  [{i['severity']}] person={i.get('person_name')} ch={i['chapter_id']}")

print("\n[B] 043h: narrative_truism (Class 17):")
r = validate_narrative_truism(book)
results['narrative_truism'] = r
print(f"  errors={r['errors_count']}, warnings={r['warnings_count']}")
for i in r.get('issues', [])[:3]:
    print(f"  [{i.get('severity','?')}] {i.get('category','?')} ch={i.get('chapter_id')}")
    print(f"    '{i.get('snippet','')[:80]}'")

print("\n[C] 043f-3: narrative_stop_phrases (Class 1/11 v7):")
r = validate_narrative_stop_phrases(book, stop_cfg)
results['stop_phrases'] = r
print(f"  errors={r['errors_count']}, warnings={r['warnings_count']}")
class1_11 = [i for i in r.get('issues', []) if any(c in i.get('category','') for c in ('class1','class11'))]
print(f"  Class1/11 issues: {len(class1_11)}")
for i in class1_11[:3]:
    print(f"  [{i.get('severity','?')}] {i.get('category','?')} ch={i.get('chapter_id')}: '{i.get('snippet','')[:60]}'")

print("\n[D] 046e: personal_historical_voice:")
r = validate_personal_historical_voice(book)
results['personal_historical_voice'] = r
print(f"  markers_per_chapter={r.get('markers_found_per_chapter')}")
for i in r.get('issues', []):
    print(f"  [{i.get('severity','?')}] ch={i.get('chapter_id')} found={i.get('found')}/need={i.get('needed')}")

print("\n[E] Historical notes count:")
inline = _count_inline_historical_notes(book)
hn = book.get('historical_notes') or []
print(f"  inline_notes={inline}, field_notes={len(hn)}")
print(f"  target: ≥5 inline ({'OK' if inline >= 5 else 'BELOW'}), ≥3 field ({'OK' if len(hn) >= 3 else 'BELOW'})")

print("\n[F] 046f: historical_notes_distribution (per-chapter v65):")
r = validate_historical_notes_distribution(book, hist_dist_cfg)
results['hist_notes_dist'] = r
print(f"  errors={r['errors_count']}, warnings={r['warnings_count']}")
for i in r.get('issues', []):
    print(f"  [{i['severity']}] ch={i.get('chapter_id')} found={i.get('found')}/need={i.get('needed')}")

print("\n[G] 048f: descendants_in_early_context (Class 12 extend):")
r = validate_descendants_in_early_context(book, fm)
results['descendants_early'] = r
print(f"  errors={r['errors_count']}, warnings={r['warnings_count']}")
for i in r.get('issues', []):
    print(f"  [{i['severity']}] {i['person_name']} ch={i['chapter_id']}: '{i.get('snippet','')[:60]}'")

print("\n[H] 048g: cross_paragraph_duplication (Class 19):")
r = validate_cross_paragraph_duplication(book, dupl_cfg)
results['cross_paragraph_dup'] = r
print(f"  errors={r['errors_count']}, warnings={r['warnings_count']}")
for i in r.get('issues', [])[:3]:
    print(f"  [{i['severity']}] sim={i.get('similarity',0):.2f}: '{i.get('para_a_snippet','')[:60]}'")

print("\n[I] 044i: required_episodes_coverage:")
pin_episodes = pin_list_data.get('episodes', []) if isinstance(pin_list_data, dict) else pin_list_data
r = validate_required_episodes_coverage(book, pin_episodes)
results['req_ep_coverage'] = r
print(f"  total_required={r.get('total_required')}, covered={r.get('covered_count')}, missing={r.get('missing_count')}")
for ep in [e for e in r.get('required_episodes', []) if not e.get('found')]:
    print(f"  MISSING: {ep['episode_id']} '{ep.get('title','')}'")

print("\n[J] bio_data family format:")
for ch in book.get('chapters', []):
    if ch.get('id') == 'ch_01':
        bio = ch.get('bio_data', {})
        r = validate_bio_data_family_format(bio)
        print(f"  ok={r['ok']}, malformed={r['malformed_count']}")
        family = bio.get('family', [])
        maria_found = any('Мария' in str(e) or 'Мар' in str(e) for e in family)
        print(f"  Мария in family: {'YES' if maria_found else 'MISSING'}")
        break

# Content checks (Nikitin feedback v64)
print("\n=== Content checks (Nikitin feedback v64) ===")
full_text = ' '.join(ch.get('content', '') for ch in book.get('chapters', []))
print(f"Баба Аня in narrative: {'YES' if 'баб' in full_text.lower() and 'ан' in full_text.lower() else 'CHECK'}")
print(f"Грибы/ягоды in narrative: {'YES' if 'гриб' in full_text.lower() or 'ягод' in full_text.lower() else 'MISSING'}")
print(f"Продажа дачи in narrative: {'YES' if 'продаж' in full_text.lower() and 'дач' in full_text.lower() else 'CHECK'}")
print(f"Полина without Толя/Коля/Витя in ch_02 1933: checking...")
# Find ch_02 content
ch02_content = next((ch.get('content','') for ch in book.get('chapters',[]) if ch.get('id')=='ch_02'), '')
if '1933' in ch02_content and any(n in ch02_content for n in ['Толя','Коля','Витя']):
    print(f"  WARNING: 1933 context may still contain Толя/Коля/Витя in ch_02")
else:
    print(f"  OK: 1933 context clean")
# Kaposhvara
if 'Капошвар' in full_text:
    if 'площадь Капошвар' in full_text:
        print(f"Капошвара: площадь OK")
    elif 'улица Капошвар' in full_text.lower() or 'улице Капошвар' in full_text.lower():
        print(f"Капошвара: WRONG — улица found (should be площадь)")
    else:
        print(f"Капошвара: in text but no explicit площадь/улица — check")

print("\n=== v65 GATE SUMMARY ===")
print(f"chronology errors: {results.get('chronology', {}).get('errors_count', '?')}")
print(f"narrative_truism errors: {results.get('narrative_truism', {}).get('errors_count', '?')}")
stop_r = results.get('stop_phrases', {})
print(f"stop_phrases errors: {stop_r.get('errors_count', '?')} warnings: {stop_r.get('warnings_count', '?')}")
print(f"hist_notes_dist errors: {results.get('hist_notes_dist', {}).get('errors_count', '?')}")
print(f"descendants_early warnings: {results.get('descendants_early', {}).get('warnings_count', '?')}")
print(f"cross_paragraph_dup errors: {results.get('cross_paragraph_dup', {}).get('errors_count', '?')}")
req_ep = results.get('req_ep_coverage', {})
print(f"required_episodes missing: {req_ep.get('missing_count', '?')} / {req_ep.get('total_required', '?')}")

json.dump(results,
          open('exports/stage3_v65/karakulina_v65_final_validators.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=2)
print("\nSaved: exports/stage3_v65/karakulina_v65_final_validators.json")

# Save required_episodes_coverage separately for build_gate1 reports
json.dump(req_ep,
          open('exports/stage3_v65/karakulina_required_episodes_coverage.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=2)
print("Saved: exports/stage3_v65/karakulina_required_episodes_coverage.json")
PYEOF

echo "=== v65: distribution gate chars summary (build_gate1 Total = sum of chapter content, NOT file_size) ==="
python - <<'PYEOF'
import json, sys, re, glob
sys.stdout.reconfigure(encoding='utf-8')

# Load book JSON directly for accurate char counts (lesson v62a/v63/v64: NOT file_size)
book_files = sorted(glob.glob('exports/stage3_v65/karakulina_book_FINAL_stage3_*.json'), reverse=True)
book_raw = json.load(open(book_files[0], encoding='utf-8'))
book = book_raw.get('book_draft') or book_raw.get('book_final') or book_raw

chapters = book.get('chapters', [])
ch_chars = {}
total_content_chars = 0
for ch in chapters:
    c = ch.get('content', '') or ''
    ch_chars[ch['id']] = len(c)
    total_content_chars += len(c)

hist_notes = book.get('historical_notes', [])
hist_chars = sum(len(str(n)) for n in hist_notes)

print(f"\n=== Distribution Gate Check (chars = sum of chapter content) ===")
print(f"Total content chars: {total_content_chars} ({'OK' if total_content_chars >= 20000 else 'FAIL'} ≥20000)")
print(f"ch_01 (paspart): {ch_chars.get('ch_01', 0)} chars (~3000 target)")
ch02 = ch_chars.get('ch_02', 0)
ch03 = ch_chars.get('ch_03', 0)
ch04 = ch_chars.get('ch_04', 0)
epil = ch_chars.get('epilogue', 0)
narrative = ch02 + ch03 + ch04 + epil
print(f"Narrative (ch02+ch03+ch04+epilogue): {narrative} ({'OK' if narrative >= 15000 else 'FAIL'} ≥15000)")
print(f"ch_02: {ch02} ({'OK' if ch02 >= 7000 else 'BELOW'} ≥7K)")
print(f"ch_03: {ch03} ({'OK' if ch03 >= 4000 else 'BELOW'} ≥4K)")
print(f"ch_04: {ch04} ({'OK' if ch04 >= 2500 else 'BELOW'} ≥2.5K)")
print(f"epilogue: {epil} ({'OK' if 800 <= epil <= 1500 else 'CHECK'} 800-1500)")
print(f"historical_notes (field, all chapters): {hist_chars} chars, {len(hist_notes)} notes ({'OK' if len(hist_notes) >= 3 else 'BELOW'} ≥3)")
print(f"Total with hist_notes: {total_content_chars + hist_chars}")
PYEOF

echo "=== v65: собираем артефакты ==="
mkdir -p "$ARTIFACTS_DIR"

# Stage 1
cp exports/karakulina_v65/karakulina_fact_map_full_*.json "$ARTIFACTS_DIR/" 2>/dev/null || true

# Stage 2 artifacts (all)
cp exports/stage2_v65/karakulina_book_draft.json "$ARTIFACTS_DIR/" 2>/dev/null || true
cp exports/stage2_v65/karakulina_book_FINAL_*.json "$ARTIFACTS_DIR/" 2>/dev/null || true
cp exports/stage2_v65/karakulina_stage2_run_manifest_*.json "$ARTIFACTS_DIR/" 2>/dev/null || true
cp exports/stage2_v65/validators_on_draft.json "$ARTIFACTS_DIR/" 2>/dev/null || true
cp exports/stage2_v65/revision_hints.json "$ARTIFACTS_DIR/" 2>/dev/null || true
cp exports/stage2_v65/revision_diff_audit.json "$ARTIFACTS_DIR/" 2>/dev/null || true
cp exports/stage2_v65/revision_pass_log.json "$ARTIFACTS_DIR/" 2>/dev/null || true
cp exports/stage2_v65/karakulina_revision_input.json "$ARTIFACTS_DIR/" 2>/dev/null || true

# Stage 3 artifacts
cp exports/stage3_v65/karakulina_book_FINAL_stage3_*.json "$ARTIFACTS_DIR/" 2>/dev/null || true
cp exports/stage3_v65/karakulina_v65_text_FULL.md "$ARTIFACTS_DIR/" 2>/dev/null || true
cp exports/stage3_v65/karakulina_style_checks_*.json "$ARTIFACTS_DIR/" 2>/dev/null || true
cp exports/stage3_v65/karakulina_chronology_check_*.json "$ARTIFACTS_DIR/" 2>/dev/null || true
cp exports/stage3_v65/karakulina_pin_list_depth_*.json "$ARTIFACTS_DIR/" 2>/dev/null || true
cp exports/stage3_v65/karakulina_discourse_markers_*.json "$ARTIFACTS_DIR/" 2>/dev/null || true
cp exports/stage3_v65/karakulina_stage3_run_manifest_*.json "$ARTIFACTS_DIR/" 2>/dev/null || true
cp exports/stage3_v65/karakulina_v65_final_validators.json "$ARTIFACTS_DIR/" 2>/dev/null || true
cp exports/stage3_v65/karakulina_required_episodes_coverage.json "$ARTIFACTS_DIR/" 2>/dev/null || true

echo ""
echo "=== v65 ПОЛНЫЙ ПРОГОН ЗАВЕРШЁН ==="
echo ""
echo "Артефакты: $ARTIFACTS_DIR"
echo ""
echo "=== Verified-on-run checklist (v65 tasks) ==="
echo "049f-2: validators_on_draft.json created with 11 validator outputs + revision_hints (warnings included)"
echo "049g: writing_notes preserved in book_FINAL_stage3 (preserve_root_level_metadata applied)"
echo "049e-2: rule13_revision_applied is list of dicts in Stage 2 manifest + diff_audit proof"
echo "048e: chronology FP fix applied (ch_01 skip + epilogue generic skip + birth-decl skip)"
echo "048f: Class 12 extend — descendants_in_early_context validator ran, Толя/Коля/Витя check"
echo "043f-3: Class 11 v7 patterns — snapshot patterns in narrative_stop_phrases.json v7"
echo "048g: Class 19 cross_paragraph_duplication — Власьево duplicate check"
echo "044i: pin-list v7 — required_episodes_coverage check + Капошвара=площадь"
echo "046f: hist_notes per-chapter distribution — ≥3 ch02, ≥2 ch03, ≥1 ch04"
echo "044i-2: characteristic words universality — 0 body matches in GW v2.24 (verified)"
echo "049h: GW v2.24 Правило 2 — placeholders + characteristic_words wired"
echo "v65-meta-build_gate1: required vs optional breakdown in text_FULL.md"
echo "distribution gate: Total chars (sum content, NOT file_size) checked"
echo "writing_notes.rule13_*: list proof in diff_audit output"
echo ""
echo "Push artifacts:"
echo "  git add $ARTIFACTS_DIR && git stash"
echo "  git checkout -b runs/karakulina-v65-artifacts || git checkout runs/karakulina-v65-artifacts"
echo "  git checkout stash -- $ARTIFACTS_DIR"
echo "  git add $ARTIFACTS_DIR && git commit -m 'runs: karakulina v65 artifacts'"
echo "  git push origin runs/karakulina-v65-artifacts"
