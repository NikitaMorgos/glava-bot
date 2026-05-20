#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v66a orchestrator revision pass:
  1. Run validators on Stage 2 FINAL output
  2. Collect revision hints (049f-2)
  3. Run GW revision pass with hints
  4. Save enriched book for Stage 3

Usage: python scripts/_v66a_orchestrator_revision.py
"""
import glob, json, sys, os, re
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding='utf-8')

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

import anthropic
from pipeline_utils import (
    load_config,
    run_ghostwriter,
    validate_chronological_consistency,
    validate_narrative_stop_phrases,
    validate_epilogue_quote_density,
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

STAGE2_DIR = ROOT / "exports" / "stage2_v66a"
FM_DIR = ROOT / "exports" / "karakulina_v66a"
CHARACTER_NAME = "Каракулина Валентина Ивановна"
PROJECT_ID = "karakulina_v66a_orchestrator"

api_key = os.getenv("ANTHROPIC_API_KEY", "")
if not api_key:
    print("[ERROR] ANTHROPIC_API_KEY not set"); sys.exit(1)

client = anthropic.Anthropic(api_key=api_key)
cfg = load_config()
ts = datetime.now().strftime("%Y%m%d_%H%M%S")

# Load Stage 2 FINAL
book_files = sorted(glob.glob(str(STAGE2_DIR / "karakulina_book_FINAL_*.json")), reverse=True)
fm_files = sorted(glob.glob(str(FM_DIR / "karakulina_fact_map_full_*.json")), reverse=True)
hist_files = sorted(glob.glob(str(STAGE2_DIR / "karakulina_historian_*.json")), reverse=True)

book_raw = json.loads(Path(book_files[0]).read_text(encoding='utf-8'))
book_draft = book_raw.get('book_draft') or book_raw.get('book_final') or book_raw
fm = json.loads(Path(fm_files[0]).read_text(encoding='utf-8'))

historical_context = None
if hist_files:
    hist_raw = json.loads(Path(hist_files[0]).read_text(encoding='utf-8'))
    historical_context = hist_raw
    n_ctx = len((hist_raw if isinstance(hist_raw, list) else hist_raw.get("historical_context", [])))
    print(f"[INPUT] historian context: {Path(hist_files[0]).name} ({n_ctx} blocks)")

tr_files = sorted(glob.glob(str(ROOT / "collab/transcripts/*.txt")))
transcripts = [open(f, encoding='utf-8').read() for f in tr_files[:2]]

pin_list_data = parse_pin_list_from_markdown(str(ROOT / 'collab/context/known_episodes_karakulina.md'))
pin_episodes = pin_list_data.get('episodes', []) + pin_list_data.get('bytovye', [])
print(f"[INPUT] pin_list: {len(pin_episodes)} episodes")

# Load configs
def _load_cfg(name):
    p = ROOT / 'collab' / 'context' / name
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}

stop_cfg = _load_cfg('narrative_stop_phrases.json')
chrono_cfg = _load_cfg('chronology_check_config.json')
dupl_cfg = _load_cfg('cross_paragraph_duplication_config.json')
hist_dist_cfg = _load_cfg('historical_notes_distribution_config.json')

print(f"\n[INPUT] Stage 2 FINAL: {Path(book_files[0]).name}")
print("=== Running validators ===")

r_chrono = validate_chronological_consistency(book_draft, fm, chrono_cfg)
print(f"[1] chronology: errors={r_chrono['errors_count']}, warnings={r_chrono['warnings_count']}")

r_truism = validate_narrative_truism(book_draft)
print(f"[2] narrative_truism: errors={r_truism['errors_count']}, warnings={r_truism['warnings_count']}")

r_stop = validate_narrative_stop_phrases(book_draft, stop_cfg)
print(f"[3] stop_phrases: errors={r_stop['errors_count']}, warnings={r_stop['warnings_count']}")

r_voice = validate_personal_historical_voice(book_draft)
print(f"[4] personal_historical_voice: markers={r_voice.get('markers_found_per_chapter')}")

r_epil = validate_epilogue_quote_density(book_draft)
print(f"[5] epilogue_quote_density: ok={r_epil.get('ok')}, quotes={r_epil.get('quote_count')}")

r_desc = validate_descendants_in_early_context(book_draft, fm)
print(f"[7] descendants_early: errors={r_desc['errors_count']}, warnings={r_desc['warnings_count']}")

r_dupl = validate_cross_paragraph_duplication(book_draft, dupl_cfg)
print(f"[8] cross_paragraph_dup: errors={r_dupl['errors_count']}, warnings={r_dupl['warnings_count']}")

r_hist_dist = validate_historical_notes_distribution(book_draft, hist_dist_cfg)
print(f"[9] hist_notes_dist: errors={r_hist_dist['errors_count']}, warnings={r_hist_dist['warnings_count']}")

r_req_ep = validate_required_episodes_coverage(book_draft, pin_episodes)
print(f"[10] required_episodes: total={r_req_ep.get('total_required')}, covered={r_req_ep.get('covered_count')}, missing={r_req_ep.get('missing_count')}")
for ep in [e for e in r_req_ep.get('required_episodes', []) if not e.get('found')][:5]:
    print(f"  MISSING: {ep.get('episode_id')} '{str(ep.get('title',''))[:50]}'")

validator_outputs = {
    'chronology_check': r_chrono,
    'narrative_truism': r_truism,
    'narrative_stop_phrases': r_stop,
    'personal_historical_voice': r_voice,
    'epilogue_quote_density': r_epil,
    'descendants_in_early_context': r_desc,
    'cross_paragraph_duplication': r_dupl,
    'historical_notes_distribution': r_hist_dist,
    'required_episodes_coverage': r_req_ep,
}
val_path = STAGE2_DIR / f"validators_on_draft_{ts}.json"
val_path.write_text(json.dumps(validator_outputs, ensure_ascii=False, indent=2), encoding='utf-8')
print(f"\n[SAVED] validators: {val_path.name}")

revision_hints = collect_revision_hints(book_draft, validator_outputs)
print(f"\n=== 049f-2 collect_revision_hints: {len(revision_hints)} hints ===")
must_apply = [h for h in revision_hints if h.get('must_apply')]
warn_hints = [h for h in revision_hints if not h.get('must_apply')]
print(f"  must_apply: {len(must_apply)}, warnings: {len(warn_hints)}")
for h in revision_hints[:5]:
    print(f"  [{h.get('hint_id')}] {h.get('validator')}/{h.get('category')} ch={h.get('chapter_id')} must_apply={h.get('must_apply')}")

hints_path = STAGE2_DIR / f"revision_hints_{ts}.json"
hints_path.write_text(json.dumps(revision_hints, ensure_ascii=False, indent=2), encoding='utf-8')
print(f"[SAVED] revision_hints: {hints_path.name}")

if not revision_hints:
    print("\n=== REVISION SKIPPED: all validators clean ===")
    # Use existing book as final
    final_path = STAGE2_DIR / f"karakulina_book_ENRICHED_{ts}.json"
    final_path.write_text(json.dumps(book_draft, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"[SAVED] No revision needed: {final_path.name}")
    sys.exit(0)

# Run GW orchestrator revision pass
print(f"\n=== ORCHESTRATOR REVISION PASS: {len(revision_hints)} hints ===")
book_before = json.loads(json.dumps(book_draft))  # deep copy

revision_scope = {
    "affected_chapters": list(set(h.get('chapter_id') for h in revision_hints if h.get('chapter_id'))),
    "revision_hints": revision_hints,
}
print(f"  affected_chapters: {revision_scope['affected_chapters']}")

book_enriched = run_ghostwriter(
    client, fm, transcripts,
    subject_name=CHARACTER_NAME,
    project_id=PROJECT_ID,
    cfg=cfg,
    call_type="revision",
    current_book=book_draft,
    historical_context=historical_context if historical_context else None,
    revision_scope=revision_scope,
    version=10,
)

enriched_path = STAGE2_DIR / f"karakulina_book_ENRICHED_{ts}.json"
enriched_path.write_text(json.dumps(book_enriched, ensure_ascii=False, indent=2), encoding='utf-8')
print(f"\n[SAVED] Enriched book: {enriched_path.name}")

# Stats
chapters = book_enriched.get('chapters', [])
ch_chars = {ch.get('id','?'): len(ch.get('content') or '') for ch in chapters}
for cid in ['ch_01','ch_02','ch_03','ch_04','epilogue']:
    print(f"  {cid}: {ch_chars.get(cid,0)} chars")
print(f"  Narrative: {sum(ch_chars.get(k,0) for k in ['ch_02','ch_03','ch_04','epilogue'])} chars")

# Save revision diff audit
before_chars = {ch.get('id','?'): len(ch.get('content') or '') for ch in book_before.get('chapters',[])}
diff_audit = {
    'version': 'v66a_orchestrator',
    'ts': ts,
    'revision_hints_count': len(revision_hints),
    'must_apply_count': len(must_apply),
    'chapters': {
        cid: {
            'before': before_chars.get(cid, 0),
            'after': ch_chars.get(cid, 0),
            'delta': ch_chars.get(cid, 0) - before_chars.get(cid, 0),
        }
        for cid in ['ch_01','ch_02','ch_03','ch_04','epilogue']
    }
}
diff_path = STAGE2_DIR / f"revision_diff_audit_{ts}.json"
diff_path.write_text(json.dumps(diff_audit, ensure_ascii=False, indent=2), encoding='utf-8')
print(f"[SAVED] revision_diff_audit: {diff_path.name}")
print(f"\n[DONE] Orchestrator revision complete. Enriched book: {enriched_path.name}")
