#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_regression_suite.py — обязательный regression suite перед approve.

Кейсы:
  1) content_guard — обязательные сущности/факты не потеряны
  2) dedup_guard   — межглавные повторы в пределах порога
  3) layout_guard  — соответствие page_plan ↔ page_map ↔ PDF preflight
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from checkpoint_utils import load_checkpoint
from pipeline_quality_gates import (
    run_stage3_text_gates,
    structural_layout_guard,
    pdf_preflight,
    save_gate_report,
    summarize_failed_gates,
)


def _extract_book(content: dict) -> dict:
    if "book_final" in content:
        return content["book_final"]
    if "book_draft" in content:
        return content["book_draft"]
    return content


def _extract_fact_map(content: dict) -> dict:
    return content.get("fact_map", content)


def _extract_pdf_path(content: dict) -> str | None:
    if isinstance(content, str):
        return content
    if isinstance(content, dict):
        return content.get("pdf_path") or content.get("path")
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Run strict regression suite")
    parser.add_argument("--project", required=True, help="checkpoint project id")
    parser.add_argument("--stage", required=True, help="stage being approved")
    parser.add_argument("--output-dir", default=str(ROOT / "exports"), help="where to save regression report")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    require_text = args.stage in {"proofreader", "layout", "pdf"}
    require_layout = args.stage in {"layout", "pdf"}

    content_guard = {"gate": "required_entities", "passed": True, "skipped": not require_text}
    dedup_guard = {"gate": "cross_chapter_repetition", "passed": True, "skipped": not require_text}
    layout_guard = {"gate": "structural_layout_guard", "passed": True, "skipped": not require_layout}
    preflight = {"gate": "pdf_preflight", "passed": True, "skipped": not require_layout}
    sources = {}

    if require_text:
        cp_fact = load_checkpoint(args.project, "fact_map", require_approved=True)
        # proofreader ещё не approved — проверяем содержимое сохранённого чекпоинта
        cp_proof = load_checkpoint(args.project, "proofreader", require_approved=False)
        fact_map = _extract_fact_map(cp_fact.get("content", {}))
        book = _extract_book(cp_proof.get("content", {}))
        text_report = run_stage3_text_gates(book, fact_map)
        content_guard = next((g for g in text_report["gates"] if g.get("gate") == "required_entities"), content_guard)
        dedup_guard = next((g for g in text_report["gates"] if g.get("gate") == "cross_chapter_repetition"), dedup_guard)
        sources.update(
            {
                "fact_map_version": cp_fact.get("version"),
                "proofreader_version": cp_proof.get("version"),
            }
        )
    else:
        text_report = {"gates": []}

    if require_layout:
        layout_cp = load_checkpoint(args.project, "layout", require_approved=True)
        layout_content = layout_cp.get("content", {})
        page_plan = layout_content.get("page_plan_source") or {"page_plan": layout_content.get("page_plan", [])}
        layout_guard = structural_layout_guard(layout_content, page_plan if isinstance(page_plan, dict) else {"page_plan": []})
        pdf_cp = load_checkpoint(args.project, "pdf", require_approved=True)
        pdf_path = _extract_pdf_path(pdf_cp.get("content"))
        if not pdf_path:
            raise RuntimeError("pdf checkpoint content must include pdf path")
        preflight = pdf_preflight(pdf_path, layout_content.get("page_map", []))
        sources.update(
            {
                "layout_version": layout_cp.get("version"),
                "pdf_version": pdf_cp.get("version"),
                "pdf_path": pdf_path,
            }
        )

    suite = {
        "project": args.project,
        "stage_under_approval": args.stage,
        "timestamp": ts,
        "cases": {
            "content_guard": content_guard,
            "dedup_guard": dedup_guard,
            "layout_guard": layout_guard,
            "pdf_preflight": preflight,
        },
        "sources": sources,
        "requirements": {"require_text": require_text, "require_layout": require_layout},
    }
    suite["passed"] = bool(content_guard.get("passed") and dedup_guard.get("passed") and layout_guard.get("passed") and preflight.get("passed"))

    report_path = out_dir / f"{args.project}_regression_suite_{ts}.json"
    save_gate_report(report_path, suite)
    print(f"[SAVED] regression_suite: {report_path}")
    print(f"[SUITE] PASSED={suite['passed']}")
    failed_text = summarize_failed_gates(text_report)
    if failed_text:
        print(f"[SUITE] text failed gates: {[g.get('gate') for g in failed_text]}")
    if not layout_guard.get("passed"):
        print("[SUITE] layout_guard failed")
    if not preflight.get("passed"):
        print("[SUITE] pdf_preflight failed")
    return 0 if suite["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
