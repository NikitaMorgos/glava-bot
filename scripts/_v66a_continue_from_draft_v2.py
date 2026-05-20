#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v66a continuation: FC + optional GW revision, starting from existing draft_v2.

Uses:
  - exports/stage2_v66a/karakulina_book_draft_v2_<ts>.json  (GW pass with historian)
  - exports/stage2_v66a/karakulina_historian_<ts>.json       (historian context)

Runs:
  1. FC iteration 1 (max_tokens from config — now 48000)
  2. If FC fail: GW revision (call_type=revision) + FC iteration 2
  3. Save book_FINAL + manifest

Usage:
  python scripts/_v66a_continue_from_draft_v2.py
"""

import glob
import json
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

import anthropic
from pipeline_utils import (
    load_config,
    run_ghostwriter,
    run_fact_checker,
    print_book_stats,
    print_fact_check_report,
    save_run_manifest,
    validate_revision_volume,
    merge_revision_out_of_scope_chapters,
    enforce_bio_data_completeness,
)
from pipeline_quality_gates import run_stage2_text_gates, save_gate_report, summarize_failed_gates

STAGE2_DIR = ROOT / "exports" / "stage2_v66a"
FM_DIR = ROOT / "exports" / "karakulina_v66a"
CHARACTER_NAME = "Каракулина Валентина Ивановна"
PROJECT_ID = "karakulina_v66a_stage2"

api_key = os.getenv("ANTHROPIC_API_KEY", "")
if not api_key:
    print("[ERROR] ANTHROPIC_API_KEY not set")
    sys.exit(1)

client = anthropic.Anthropic(api_key=api_key)
cfg = load_config()
ts = datetime.now().strftime("%Y%m%d_%H%M%S")

# Load book draft v2 (GW initial + historian integration)
draft_v2_files = sorted(glob.glob(str(STAGE2_DIR / "karakulina_book_draft_v2_*.json")), reverse=True)
if not draft_v2_files:
    print("[ERROR] No draft_v2 found in", STAGE2_DIR)
    sys.exit(1)
draft_path = draft_v2_files[0]
print(f"[INPUT] book draft v2: {Path(draft_path).name}")
book_raw = json.loads(Path(draft_path).read_text(encoding="utf-8"))
book_draft = book_raw.get("book_draft") or book_raw.get("book_final") or book_raw

# Load fact_map
fm_files = sorted(glob.glob(str(FM_DIR / "karakulina_fact_map_full_*.json")), reverse=True)
if not fm_files:
    print("[ERROR] No fact_map found in", FM_DIR)
    sys.exit(1)
fact_map = json.loads(Path(fm_files[0]).read_text(encoding="utf-8"))
print(f"[INPUT] fact_map: {Path(fm_files[0]).name}")

# Load historian context
hist_files = sorted(glob.glob(str(STAGE2_DIR / "karakulina_historian_*.json")), reverse=True)
historical_context = None
if hist_files:
    hist_raw = json.loads(Path(hist_files[0]).read_text(encoding="utf-8"))
    # run_historian returns the context directly or wrapped
    if isinstance(hist_raw, dict) and "historical_context" in hist_raw:
        historical_context = hist_raw
    else:
        historical_context = hist_raw
    n_ctx = len((hist_raw if isinstance(hist_raw, list) else hist_raw.get("historical_context", [])))
    print(f"[INPUT] historian context: {Path(hist_files[0]).name} ({n_ctx} blocks)")
else:
    print("[WARN] No historian context found — proceeding without")

# Load transcripts
tr_files = sorted(glob.glob(str(ROOT / "collab/transcripts/*.txt")))
transcripts = [open(f, encoding="utf-8").read() for f in tr_files[:2]]
print(f"[INPUT] transcripts: {len(transcripts)} files")

# Print current draft stats
print("\n[DRAFT_V2] Stats before FC:")
print_book_stats(book_draft)

# ─── СТЫК 4: FC loop (up to 2 iterations) ────────────────────────────────────
print("\n" + "─" * 60)
print("СТЫК 4: Фактчекер (макс. 2 итерации)")
print("─" * 60)

MAX_FC_ITERS = 2
fc_report = None
fc_path = None

for iteration in range(1, MAX_FC_ITERS + 1):
    fc_report = run_fact_checker(
        client, book_draft, fact_map, transcripts,
        project_id=PROJECT_ID,
        iteration=iteration,
        max_iterations=MAX_FC_ITERS,
        historical_context=historical_context,
        cfg=cfg,
    )
    fc_path = STAGE2_DIR / f"karakulina_fc_report_iter{iteration}_{ts}.json"
    fc_path.write_text(json.dumps(fc_report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[SAVED] FC отчёт итерация {iteration}: {fc_path.name}")
    print_fact_check_report(fc_report)

    if fc_report.get("verdict") == "pass":
        print(f"\n✅ [FACT_CHECKER] PASS на итерации {iteration}")
        break

    if iteration < MAX_FC_ITERS:
        print(f"\n[FACT_CHECKER] FAIL на итерации {iteration} — запускаю GW revision...")
        errors = fc_report.get("errors", [])
        revision_scope = fc_report.get("revision_scope", {})
        affected_chapters = revision_scope.get("affected_chapters") if revision_scope else None

        book_before_revision = book_draft.copy()
        book_draft = run_ghostwriter(
            client, fact_map, transcripts,
            subject_name=CHARACTER_NAME,
            project_id=PROJECT_ID,
            cfg=cfg,
            call_type="revision",
            current_book=book_draft,
            historical_context=historical_context if historical_context else None,
            revision_scope=revision_scope,
            version=iteration + 2,
        )
        rev_path = STAGE2_DIR / f"karakulina_book_draft_v{iteration+2}_{ts}.json"
        rev_path.write_text(json.dumps(book_draft, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[SAVED] Черновик v{iteration+2} (после правок): {rev_path.name}")
        print_book_stats(book_draft)

        # Scope-merge guardrail
        book_draft, merge_details = merge_revision_out_of_scope_chapters(
            book_before_revision, book_draft,
            affected_chapters=affected_chapters,
        )
        merge_path = STAGE2_DIR / f"karakulina_scope_merge_iter{iteration}_{ts}.json"
        merge_path.write_text(json.dumps(merge_details, ensure_ascii=False, indent=2), encoding="utf-8")
        restored = len(merge_details.get("chapters_restored", []))
        print(f"[SCOPE_MERGE] chapters_restored={restored}")

        # Revision volume check
        rv_passed, rv_details = validate_revision_volume(book_before_revision, book_draft, fc_report=fc_report)
        rv_path = STAGE2_DIR / f"karakulina_revision_volume_iter{iteration}_{ts}.json"
        rv_path.write_text(json.dumps(rv_details, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[REVISION_VOLUME] verdict={rv_details['verdict']} "
              f"({rv_details['chars_before']} → {rv_details['chars_after']} chars)")
    else:
        print(f"\n⚠️  [FACT_CHECKER] FAIL после {MAX_FC_ITERS} итераций. --allow-fc-fail: продолжаем.")

# ─── bio_data completeness ─────────────────────────────────────────────────────
book_draft = enforce_bio_data_completeness(book_draft, fact_map, strict=False)

# ─── Final save ───────────────────────────────────────────────────────────────
final_path = STAGE2_DIR / f"karakulina_book_FINAL_{ts}.json"
final_path.write_text(json.dumps(book_draft, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\n[RESULT] Финальная книга: {final_path.name}")
if fc_report:
    print(f"[RESULT] FC вердикт: {fc_report.get('verdict', '?').upper()}")

# Readable text
txt_path = STAGE2_DIR / f"karakulina_book_FINAL_{ts}.txt"
with open(txt_path, "w", encoding="utf-8") as f:
    chapters = book_draft.get("chapters", [])
    for ch in sorted(chapters, key=lambda x: x.get("order", 0)):
        f.write(f"\n{'=' * 60}\n{ch.get('title', ch['id'])}\n{'=' * 60}\n\n")
        f.write((ch.get("content") or "") + "\n")
print(f"[RESULT] Текст книги: {txt_path.name}")

# Stage 2 text gates
gate_report = run_stage2_text_gates(book_draft, fact_map)
gate_path = STAGE2_DIR / f"karakulina_stage2_text_gates_{ts}.json"
save_gate_report(gate_path, gate_report)
print(f"[SAVED] Stage2 text gates: {gate_path.name}")

# Manifest
save_run_manifest(
    output_dir=STAGE2_DIR,
    prefix="karakulina",
    stage="stage2",
    project_id=PROJECT_ID,
    cfg=cfg,
    ts=ts,
    inputs={
        "fact_map_path": str(fm_files[0]),
        "draft_v2_source": str(draft_path),
        "historian_context": str(hist_files[0]) if hist_files else None,
        "max_fc_iterations": MAX_FC_ITERS,
        "fc_fail_accepted": True,
        "note": "continuation from draft_v2 (GW initial + historian pass already done)",
    },
    outputs={
        "historian_path": str(hist_files[0]) if hist_files else None,
        "final_book_json": str(final_path),
        "final_book_txt": str(txt_path),
        "final_verdict": fc_report.get("verdict") if fc_report else None,
        "text_gates_path": str(gate_path),
        "text_gates_passed": gate_report.get("passed"),
    },
    notes={
        "ghostwriter_version": "v2.25",
        "completeness_auditor_version": "v1.5",
        "run_note": "v66a universality sub-sprint; GW v2.25 placeholder examples",
    },
)

print(f"\n[DONE] Stage 2 v66a completed: {final_path.name}")
