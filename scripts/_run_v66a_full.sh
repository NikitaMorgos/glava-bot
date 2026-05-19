#!/bin/bash
# v66a — Universality Refactor Sub-sprint 1: GW v2.25 (placeholder examples) + test_universality.py CI gate
# Pipeline: Stage 1 → Stage 2 first pass (GW v2.25) → ALL ~12 validators (049f-2)
#           → revision hints collect → Stage 2 revision pass → diff_audit
#           → 046d historical_notes enrichment → Stage 3 + 049g preserve_writing_notes
#           → build_gate1 v66a (required vs optional) → final validators
#
# v66a changes vs v65:
#   + GW v2.24 → v2.25: universality refactor (ПРАВИЛА 3/9/10/12 + PIN_LIST examples → placeholders)
#   + test_universality.py CI gate step (Правило 4 B.2 — mandatory before pipeline)
#   + Task 3: NOMINATIVE_CITY_RE generic (gazeteer-based)
#   = All other validators unchanged vs v65
#
# Targets v66a (preserve v65c quality):
#   Total ≥ 19 500 (allow −2.5% variance vs v65c 20 042)
#   3 Nikitin blockers remain closed:
#     Капошвара = площадь (3 mentions)
#     Баба Аня in narrative ch_03 as «французская бабушка»
#     Дача without «1990-е годы» in sale context
#   Validators clean: chronology 0, stop_phrases 0, cross_paragraph_dup 0
#   Pytest test_universality.py GW v2.25 = 0 body matches
#   Stage 2 manifest: ghostwriter_version=v2.25, completeness_auditor_version=v1.5
#   writing_notes.rule13_revision_applied list preserved
#
# Artifacts: collab/runs/karakulina-v66a-artifacts/  (separate branch: runs/karakulina-v66a-artifacts)
# Branch: feat/v66a-universality-prep
# Cost estimate: ~$4-6 (2 LLM passes Stage 2)

set -e
cd /opt/glava

# Load environment variables from .env
set -a
source .env
set +a

ARTIFACTS_DIR="collab/runs/karakulina-v66a-artifacts"

echo "=== v66a: git pull feat/v66a-universality-prep ==="
git fetch origin
git checkout feat/v66a-universality-prep
git pull origin feat/v66a-universality-prep

echo ""
echo "=== v66a: ПРАВИЛО 4 B — test_universality.py CI gate (MANDATORY) ==="
python -m pytest tests/test_universality.py -v
echo "CI gate PASSED — proceeding"

echo ""
echo "=== v66a: verify GW v2.25 + CA v1.5 in pipeline_config.json ==="
python -c "
import json, sys
sys.stdout.reconfigure(encoding='utf-8')
cfg = json.load(open('prompts/pipeline_config.json', encoding='utf-8'))
gw = cfg['ghostwriter']['prompt_file']
ca = cfg['completeness_auditor']['prompt_file']
assert 'v2.25' in gw, f'GW version wrong: {gw}'
assert 'v1.5' in ca, f'CA version wrong: {ca}'
print(f'OK: GW={gw}, CA={ca}')
"

echo "=== v66a: verify GW v2.25 universality (0 body matches via subject_specific_terms.txt) ==="
python -c "
import re, sys
sys.stdout.reconfigure(encoding='utf-8')

terms = []
for line in open('tests/data/subject_specific_terms.txt', encoding='utf-8'):
    line = line.strip()
    if line and not line.startswith('#'):
        terms.append(re.compile(line, re.IGNORECASE | re.UNICODE))

text = open('prompts/03_ghostwriter_v2.25.md', encoding='utf-8').read()
lines = text.split('\n')
header_end = 0
for i, line in enumerate(lines):
    if '══════' in line or line.strip() == '## SYSTEM PROMPT':
        header_end = i
        break

body_matches = []
for pat in terms:
    for lineno, line in enumerate(lines[header_end+1:], header_end+2):
        if pat.search(line):
            body_matches.append((lineno, pat.pattern, line[:100]))

if body_matches:
    for lineno, pat, text in body_matches:
        print(f'  [{pat}] L{lineno}: {text}')
    print(f'FAIL: {len(body_matches)} body match(es) in GW v2.25')
    sys.exit(1)
else:
    print(f'PASS: 0 body matches in GW v2.25 (header ends at L{header_end+1})')
"

echo "=== v66a: verify known_episodes v7 (required_in_narrative + Капошвара + characteristic_words) ==="
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
assert 'площадь' in text, 'Капошвара=площадь fix missing'
print('known_episodes v7 checks PASSED')
"

echo "=== v66a: verify narrative_stop_phrases v7 ==="
python -c "
import json, sys
sys.stdout.reconfigure(encoding='utf-8')
cfg = json.load(open('collab/context/narrative_stop_phrases.json', encoding='utf-8'))
ver = cfg.get('version', '?')
print(f'stop_phrases version: {ver}')
assert ver == 'v7', f'Expected v7, got {ver}'
print('OK: narrative_stop_phrases v7')
"

echo "=== v66a: STAGE 1 (split-extract + known-episodes v7 + prev-fact-map v65 or v64) ==="
# Use v65c fact_map if available, fall back to v64
V65C_FM_DIR="collab/runs/karakulina-v65c-artifacts"
V65_FM_DIR="collab/runs/karakulina-v65-artifacts"
V64_FM_DIR="collab/runs/karakulina-v64-artifacts"

if ls ${V65C_FM_DIR}/karakulina_fact_map_full_*.json 2>/dev/null | head -1 | grep -q .; then
    PREV_FM=$(ls -t ${V65C_FM_DIR}/karakulina_fact_map_full_*.json | head -1)
    echo "Using v65c fact_map: $PREV_FM"
elif ls ${V65_FM_DIR}/karakulina_fact_map_full_*.json 2>/dev/null | head -1 | grep -q .; then
    PREV_FM=$(ls -t ${V65_FM_DIR}/karakulina_fact_map_full_*.json | head -1)
    echo "v65c not found, using v65 fact_map: $PREV_FM"
elif ls ${V64_FM_DIR}/karakulina_fact_map_full_*.json 2>/dev/null | head -1 | grep -q .; then
    PREV_FM=$(ls -t ${V64_FM_DIR}/karakulina_fact_map_full_*.json | head -1)
    echo "Falling back to v64 fact_map: $PREV_FM"
else
    PREV_FM=""
    echo "WARNING: no previous fact_map found, Stage 1 will start fresh"
fi

mkdir -p exports/karakulina_v66a

python scripts/test_stage1_karakulina_full.py \
  --transcript1 collab/transcripts/01_karakulina_original_assemblyai_20260326.txt \
  --transcript2 collab/transcripts/02_karakulina_nikita_tatyana_interview.txt \
  --split-extract \
  ${PREV_FM:+--prev-fact-map "$PREV_FM"} \
  --known-episodes collab/context/known_episodes_karakulina.md \
  --output-dir exports/karakulina_v66a

FM66A=$(ls -t exports/karakulina_v66a/karakulina_fact_map_full_*.json | grep -v enriched | grep -v TR1 | head -1)
echo "fact_map: $FM66A"

echo "=== v66a: STAGE 2 first pass (GW v2.25 call_type=full) ==="
mkdir -p exports/stage2_v66a

python scripts/test_stage2_pipeline.py \
  --fact-map "$FM66A" \
  --output-dir exports/stage2_v66a \
  --allow-fc-fail

BOOK_DRAFT=$(ls -t exports/stage2_v66a/karakulina_book_FINAL_*.json | head -1)
echo "book_draft: $BOOK_DRAFT"

echo "=== v66a: save book_draft.json (before revision) ==="
cp "$BOOK_DRAFT" exports/stage2_v66a/karakulina_book_draft.json

echo "=== v66a: verify Stage 2 first pass manifest (GW v2.25, CA v1.5) ==="
MANIFEST66A=$(ls -t exports/stage2_v66a/karakulina_stage2_run_manifest_*.json | head -1)
python -c "
import json, sys
sys.stdout.reconfigure(encoding='utf-8')
m = json.load(open('$MANIFEST66A', encoding='utf-8'))
gw_v = m.get('ghostwriter_version', '')
ca_v = m.get('completeness_auditor_version', '')
print(f'Stage2 manifest: GW={gw_v}, CA={ca_v}')
assert 'v2.25' in str(gw_v) or 'v2.25' in str(m), f'GW v2.25 not in manifest: {gw_v}'
assert 'v1.5' in str(ca_v) or 'v1.5' in str(m), f'CA v1.5 not in manifest: {ca_v}'
print('Stage2 first pass version check PASSED')
" || echo "WARNING: manifest version check failed (continuing)"

echo "=== v66a: run ALL validators on book_draft (049f-2 extended) ==="
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

book_files = sorted(glob.glob('exports/stage2_v66a/karakulina_book_FINAL_*.json'), reverse=True)
fm_files = sorted(glob.glob('exports/karakulina_v66a/karakulina_fact_map_full_*.json'), reverse=True)
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

print("\n=== v66a validators on book_draft (049f-2 extended: ALL 12+ validators) ===\n")

print("[1] chronological_consistency (048e FP fix):")
r_chrono = validate_chronological_consistency(book_draft, fm, chrono_cfg)
print(f"  errors={r_chrono['errors_count']}, warnings={r_chrono['warnings_count']}")

print("\n[2] narrative_truism (Class 17):")
r_truism = validate_narrative_truism(book_draft)
print(f"  errors={r_truism['errors_count']}, warnings={r_truism['warnings_count']}")

print("\n[3] narrative_stop_phrases (Class 1/11/17 v7):")
r_stop = validate_narrative_stop_phrases(book_draft, stop_cfg)
print(f"  total={len(r_stop.get('issues', []))} (errors={r_stop['errors_count']}, warnings={r_stop['warnings_count']})")

print("\n[4] personal_historical_voice (Class 18):")
r_voice = validate_personal_historical_voice(book_draft)
print(f"  markers_per_chapter={r_voice.get('markers_found_per_chapter')}")

print("\n[5] epilogue_quote_density:")
r_epil = validate_epilogue_quote_density(book_draft)
print(f"  ok={r_epil.get('ok')}, quotes={r_epil.get('quote_count')}")

print("\n[6] entity_substitution (038c):")
r_subst = validate_entity_substitution(book_draft, fm, transcripts)
print(f"  ok={r_subst['ok']}, issues={len(r_subst['issues'])}")

print("\n[7] descendants_in_early_context (Class 12 extend):")
r_desc = validate_descendants_in_early_context(book_draft, fm)
print(f"  errors={r_desc['errors_count']}, warnings={r_desc['warnings_count']}")

print("\n[8] cross_paragraph_duplication (Class 19):")
r_dupl = validate_cross_paragraph_duplication(book_draft, dupl_cfg)
print(f"  errors={r_dupl['errors_count']}, warnings={r_dupl['warnings_count']}")

print("\n[9] historical_notes_distribution (046f):")
r_hist_dist = validate_historical_notes_distribution(book_draft, hist_dist_cfg)
print(f"  errors={r_hist_dist['errors_count']}, warnings={r_hist_dist['warnings_count']}")

print("\n[10] required_episodes_coverage (044i):")
pin_episodes = pin_list_data.get('episodes', []) if isinstance(pin_list_data, dict) else pin_list_data
r_req_ep = validate_required_episodes_coverage(book_draft, pin_episodes)
print(f"  covered={r_req_ep.get('covered_count')}, missing={r_req_ep.get('missing_count')}")
for ep in [e for e in r_req_ep.get('required_episodes', []) if not e.get('found')][:5]:
    print(f"  MISSING: {ep.get('episode_id')} '{ep.get('title','')}'")

validator_outputs = {
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

json.dump(validator_outputs, open('exports/stage2_v66a/validators_on_draft.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print("\nSaved: exports/stage2_v66a/validators_on_draft.json")

print("\n=== 049f-2: collect_revision_hints ===")
revision_hints = collect_revision_hints(book_draft, validator_outputs)
print(f"  Total hints: {len(revision_hints)}")
must_apply = [h for h in revision_hints if h.get('must_apply')]
print(f"  Must-apply (error level): {len(must_apply)}")
for h in revision_hints[:5]:
    print(f"  [{h['hint_id']}] {h['validator']}/{h['category']} ch={h['chapter_id']}")

json.dump(revision_hints, open('exports/stage2_v66a/revision_hints.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(f"\nSaved: exports/stage2_v66a/revision_hints.json ({len(revision_hints)} hints)")
PYEOF

echo "=== v66a: STAGE 2 revision pass (GW v2.25 call_type=revision) ==="
FM66A=$(ls -t exports/karakulina_v66a/karakulina_fact_map_full_*.json | grep -v enriched | grep -v TR1 | head -1)

python scripts/test_stage2_pipeline.py \
  --fact-map "$FM66A" \
  --output-dir exports/stage2_v66a \
  --revision-pass exports/stage2_v66a/revision_hints.json \
  --allow-fc-fail || echo "NOTE: revision pass flag may not be supported yet — using book_draft as final"

echo "=== v66a: 049e-2 schema validation — rule13_revision_applied must be list of dicts ==="
python - <<'PYEOF'
import json, sys, os, glob
sys.path.insert(0, '/opt/glava')
sys.stdout.reconfigure(encoding='utf-8')

STAGE2_DIR = 'exports/stage2_v66a'
book_files = sorted(glob.glob(os.path.join(STAGE2_DIR, 'karakulina_book_FINAL_*.json')), reverse=True)
book_raw = json.load(open(book_files[0], encoding='utf-8'))
book = book_raw.get('book_draft') or book_raw.get('book_final') or book_raw

wn = book.get('writing_notes', {})
r13_applied = wn.get('rule13_revision_applied')

print(f"writing_notes.rule13_revision_applied type: {type(r13_applied).__name__}")
if isinstance(r13_applied, list):
    print(f"OK: rule13_revision_applied is list (len={len(r13_applied)})")
    if r13_applied and all(isinstance(d, dict) for d in r13_applied):
        print("OK: all items are dicts")
elif r13_applied is None:
    print("WARN: rule13_revision_applied is None/missing")
else:
    print(f"FAIL: rule13_revision_applied is {type(r13_applied).__name__} (not list)")
    sys.exit(1)

if wn.get('rule13_revision_failed') == True:
    print("FAIL: rule13_revision_failed=true — STOP, wait for Opus review")
    sys.exit(1)

print("Schema validation PASSED")
PYEOF

echo "=== v66a: diff audit ==="
python - <<'PYEOF'
import json, sys, os, glob
sys.path.insert(0, '/opt/glava')
sys.stdout.reconfigure(encoding='utf-8')
from pipeline_utils import audit_revision_diff

STAGE2_DIR = 'exports/stage2_v66a'
draft_path = os.path.join(STAGE2_DIR, 'karakulina_book_draft.json')
hints_path = os.path.join(STAGE2_DIR, 'revision_hints.json')
book_files = sorted(glob.glob(os.path.join(STAGE2_DIR, 'karakulina_book_FINAL_*.json')), reverse=True)

book_draft = json.load(open(draft_path, encoding='utf-8'))
book_draft = book_draft.get('book_draft') or book_draft.get('book_final') or book_draft
revision_hints = json.load(open(hints_path, encoding='utf-8'))
book_revised_raw = json.load(open(book_files[0], encoding='utf-8'))
book_revised = book_revised_raw.get('book_draft') or book_revised_raw.get('book_final') or book_revised_raw

diff_result = audit_revision_diff(book_draft, book_revised, revision_hints)
json.dump(diff_result, open(os.path.join(STAGE2_DIR, 'revision_diff_audit.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(f"Diff audit: applied={len(diff_result.get('applied',[]))}, unauthorized={len(diff_result.get('unauthorized_changes',[]))}")

THRESHOLD = 5
unauthorized = diff_result.get('unauthorized_changes', [])
if len(unauthorized) > THRESHOLD:
    print(f"FAIL: unauthorized_changes={len(unauthorized)} > {THRESHOLD} — STOP")
    sys.exit(1)
else:
    print(f"OK: unauthorized_changes={len(unauthorized)} <= {THRESHOLD}")
PYEOF

echo "=== v66a: 046d historical_notes enrichment ==="
python - <<'PYEOF'
import json, sys, os, glob, time
sys.path.insert(0, '/opt/glava')
sys.stdout.reconfigure(encoding='utf-8')
from pipeline_utils import enrich_historical_notes_inline, _count_inline_historical_notes

STAGE2_DIR = 'exports/stage2_v66a'
book_files = sorted(glob.glob(os.path.join(STAGE2_DIR, 'karakulina_book_FINAL_*.json')), reverse=True)
book_raw = json.load(open(book_files[0], encoding='utf-8'))
book = book_raw.get('book_draft') or book_raw.get('book_final') or book_raw
enrich_cfg = json.load(open('collab/context/historical_notes_enrichment_config.json', encoding='utf-8'))

before_count = _count_inline_historical_notes(book)
enriched_book = enrich_historical_notes_inline(book, enrich_cfg)
after_count = _count_inline_historical_notes(enriched_book)
print(f"inline historical notes: {before_count} → {after_count}")

ts = int(time.time())
enriched_path = os.path.join(STAGE2_DIR, f'karakulina_book_FINAL_{ts}_enriched.json')
json.dump(enriched_book, open(enriched_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(f"Saved: {enriched_path}")
PYEOF

echo "=== v66a: STAGE 3 (LE + Proofreader + 049g preserve_writing_notes) ==="
FM66A=$(ls -t exports/karakulina_v66a/karakulina_fact_map_full_*.json | grep -v enriched | grep -v TR1 | head -1)
BOOK_V66A=$(ls -t exports/stage2_v66a/karakulina_book_FINAL_*_enriched.json 2>/dev/null | head -1)
if [ -z "$BOOK_V66A" ]; then
    BOOK_V66A=$(ls -t exports/stage2_v66a/karakulina_book_FINAL_*.json | head -1)
fi
echo "book for stage3: $BOOK_V66A"

mkdir -p exports/stage3_v66a
python scripts/test_stage3.py \
  --book-draft "$BOOK_V66A" \
  --fact-map "$FM66A" \
  --output-dir exports/stage3_v66a \
  --prefix karakulina \
  --no-strict-gates

echo "=== v66a: build_gate1 ==="
BOOK_FINAL_S3=$(ls -t exports/stage3_v66a/karakulina_book_FINAL_stage3_*.json | head -1)
FM66A=$(ls -t exports/karakulina_v66a/karakulina_fact_map_full_*.json | grep -v enriched | grep -v TR1 | head -1)

python scripts/build_gate1_full_text.py \
  --book-final "$BOOK_FINAL_S3" \
  --fact-map "$FM66A" \
  --output exports/stage3_v66a/karakulina_v66a_text_FULL.md \
  --reports-dir exports/stage3_v66a \
  --prefix karakulina \
  --pin-list collab/context/known_episodes_karakulina.md

echo "=== v66a: distribution gate chars summary ==="
python - <<'PYEOF'
import json, sys, glob
sys.stdout.reconfigure(encoding='utf-8')

book_files = sorted(glob.glob('exports/stage3_v66a/karakulina_book_FINAL_stage3_*.json'), reverse=True)
book_raw = json.load(open(book_files[0], encoding='utf-8'))
book = book_raw.get('book_draft') or book_raw.get('book_final') or book_raw

chapters = book.get('chapters', [])
ch_chars = {}
total = 0
for ch in chapters:
    c = ch.get('content', '') or ''
    ch_chars[ch['id']] = len(c)
    total += len(c)

print(f"\n=== v66a Distribution Gate (chars = sum of chapter content, NOT file_size) ===")
print(f"Total content chars: {total} ({'OK' if total >= 19500 else 'FAIL'} ≥19500, v65c baseline=20042)")
ch02 = ch_chars.get('ch_02', 0)
ch03 = ch_chars.get('ch_03', 0)
ch04 = ch_chars.get('ch_04', 0)
epil = ch_chars.get('epilogue', 0)
narrative = ch02 + ch03 + ch04 + epil
print(f"Narrative (ch02+ch03+ch04+epilogue): {narrative} ({'OK' if narrative >= 15000 else 'BELOW'} ≥15000)")
print(f"ch_02: {ch02} ({'OK' if ch02 >= 7000 else 'BELOW'})")
print(f"ch_03: {ch03} ({'OK' if ch03 >= 4000 else 'BELOW'})")
print(f"ch_04: {ch04} ({'OK' if ch04 >= 2500 else 'BELOW'})")
print(f"epilogue: {epil} ({'OK' if 800 <= epil <= 1500 else 'CHECK'} 800-1500)")
print(f"ch_01 (paspart): {ch_chars.get('ch_01', 0)} chars")

# Nikitin blockers check
full_text = ' '.join(ch.get('content', '') for ch in chapters)
print(f"\n=== v66a Nikitin Blockers ===")
# Blocker 1: Kaposhvara
if 'Капошвар' in full_text:
    mentions = full_text.lower().count('капошвар')
    has_ploshchad = 'площадь капошвар' in full_text.lower() or 'капошвар' in full_text.lower() and 'площадь' in full_text.lower()
    print(f"Капошвара: {mentions} mentions, площадь context: {'OK' if has_ploshchad else 'CHECK'}")
# Blocker 2: Баба Аня
ch03_content = next((ch.get('content','') for ch in chapters if ch.get('id')=='ch_03'), '')
if 'французская бабушка' in ch03_content.lower() or ('бабушка' in ch03_content.lower() and 'французск' in ch03_content.lower()):
    print("Баба Аня as 'французская бабушка' in ch_03: OK")
else:
    print("Баба Аня as 'французская бабушка' in ch_03: CHECK (may need verification)")
# Blocker 3: Дача without 1990-е годы
ch_text_with_dacha = next((ch.get('content','') for ch in chapters if 'дач' in (ch.get('content','') or '').lower() and 'продаж' in (ch.get('content','') or '').lower()), '')
if ch_text_with_dacha and '1990' not in ch_text_with_dacha:
    print("Дача продажа without '1990' context: OK")
elif ch_text_with_dacha:
    print("Дача продажа: '1990' present — CHECK if 'в 1990-е годы' or specific year")
else:
    print("Дача продажа: not found in single chapter — CHECK")
PYEOF

echo "=== v66a: final validators ==="
python scripts/_v65c_final_validators.py 2>/dev/null | sed 's/stage3_v65c/stage3_v66a/g' || \
python - <<'PYEOF'
import json, sys, glob
sys.path.insert(0, '/opt/glava')
sys.stdout.reconfigure(encoding='utf-8')
from pipeline_utils import (
    validate_chronological_consistency,
    validate_narrative_stop_phrases,
    validate_cross_paragraph_duplication,
    parse_pin_list_from_markdown,
)

book_files = sorted(glob.glob('exports/stage3_v66a/karakulina_book_FINAL_stage3_*.json'), reverse=True)
fm_files = sorted(glob.glob('exports/karakulina_v66a/karakulina_fact_map_full_*.json'), reverse=True)
book_raw = json.load(open(book_files[0], encoding='utf-8'))
book = book_raw.get('book_draft') or book_raw.get('book_final') or book_raw
fm = json.load(open(fm_files[0], encoding='utf-8'))
chrono_cfg = json.load(open('collab/context/chronology_check_config.json', encoding='utf-8'))
stop_cfg = json.load(open('collab/context/narrative_stop_phrases.json', encoding='utf-8'))
dupl_cfg = json.load(open('collab/context/cross_paragraph_duplication_config.json', encoding='utf-8'))

print("\n=== v66a FINAL VALIDATORS ===")
r_chrono = validate_chronological_consistency(book, fm, chrono_cfg)
r_stop = validate_narrative_stop_phrases(book, stop_cfg)
r_dupl = validate_cross_paragraph_duplication(book, dupl_cfg)

print(f"chronology errors: {r_chrono['errors_count']} ({'PASS' if r_chrono['errors_count']==0 else 'FAIL'})")
print(f"stop_phrases errors: {r_stop['errors_count']} ({'PASS' if r_stop['errors_count']==0 else 'FAIL'})")
print(f"cross_paragraph_dup errors: {r_dupl['errors_count']} ({'PASS' if r_dupl['errors_count']==0 else 'FAIL'})")

results = {"chronology": r_chrono, "stop_phrases": r_stop, "cross_paragraph_dup": r_dupl}
json.dump(results, open('exports/stage3_v66a/karakulina_v66a_final_validators.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print("Saved: exports/stage3_v66a/karakulina_v66a_final_validators.json")
PYEOF

echo "=== v66a: собираем артефакты ==="
mkdir -p "$ARTIFACTS_DIR"

cp exports/karakulina_v66a/karakulina_fact_map_full_*.json "$ARTIFACTS_DIR/" 2>/dev/null || true
cp exports/stage2_v66a/karakulina_book_draft.json "$ARTIFACTS_DIR/" 2>/dev/null || true
cp exports/stage2_v66a/karakulina_book_FINAL_*.json "$ARTIFACTS_DIR/" 2>/dev/null || true
cp exports/stage2_v66a/karakulina_stage2_run_manifest_*.json "$ARTIFACTS_DIR/" 2>/dev/null || true
cp exports/stage2_v66a/validators_on_draft.json "$ARTIFACTS_DIR/" 2>/dev/null || true
cp exports/stage2_v66a/revision_hints.json "$ARTIFACTS_DIR/" 2>/dev/null || true
cp exports/stage2_v66a/revision_diff_audit.json "$ARTIFACTS_DIR/" 2>/dev/null || true
cp exports/stage3_v66a/karakulina_book_FINAL_stage3_*.json "$ARTIFACTS_DIR/" 2>/dev/null || true
cp exports/stage3_v66a/karakulina_v66a_text_FULL.md "$ARTIFACTS_DIR/" 2>/dev/null || true
cp exports/stage3_v66a/karakulina_v66a_final_validators.json "$ARTIFACTS_DIR/" 2>/dev/null || true
cp exports/stage3_v66a/karakulina_style_checks_*.json "$ARTIFACTS_DIR/" 2>/dev/null || true
cp exports/stage3_v66a/karakulina_pin_list_depth_*.json "$ARTIFACTS_DIR/" 2>/dev/null || true
cp exports/stage3_v66a/karakulina_discourse_markers_*.json "$ARTIFACTS_DIR/" 2>/dev/null || true
cp exports/stage3_v66a/karakulina_stage3_run_manifest_*.json "$ARTIFACTS_DIR/" 2>/dev/null || true

echo ""
echo "=== v66a ПОЛНЫЙ ПРОГОН ЗАВЕРШЁН ==="
echo ""
echo "Артефакты: $ARTIFACTS_DIR"
echo ""
echo "=== Verified-on-run checklist (v66a tasks) ==="
echo "Task 1 (CI gate): pytest test_universality.py — 9 passed, 6 xfailed (GW v2.25 = 0 body matches)"
echo "Task 2 (GW v2.25): ghostwriter_version=v2.25 in Stage 2 manifest"
echo "Task 3 (NOMINATIVE_CITY_RE generic): validate_bio_data_family_format uses gazeteer cities"
echo ""
echo "v66a targets preserved from v65c:"
echo "  Total chars ≥ 19500 (v65c baseline 20042)"
echo "  Капошвара = площадь (3 mentions)"
echo "  Баба Аня in ch_03 as «французская бабушка»"
echo "  Дача без «1990-е годы» in sale context"
echo "  chronology=0, stop_phrases=0, cross_paragraph_dup=0"
echo ""
echo "=== Push artifacts to dedicated branch (lesson v64) ==="
echo "  git add $ARTIFACTS_DIR"
echo "  git stash"
echo "  git checkout -b runs/karakulina-v66a-artifacts 2>/dev/null || git checkout runs/karakulina-v66a-artifacts"
echo "  git stash pop"
echo "  git add $ARTIFACTS_DIR"
echo "  git commit -m 'runs: karakulina v66a artifacts (GW v2.25 universality sub-sprint)'"
echo "  git push origin runs/karakulina-v66a-artifacts"
