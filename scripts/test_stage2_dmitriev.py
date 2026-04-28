#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stage 2: Историк + Писатель → Фактчекер для Дмитриева Сергея Александровича

Флоу:
  1. Загружаем fact_map из Stage 1 (dmitriev_fact_map_v1.json)
  2. Историк → исторический контекст (СССР 1955–2001)
  3. Писатель 1-й проход → черновик
  4. Писатель 2-й проход → интеграция контекста историка
  5. Фактчекер → если fail: Писатель revision → повтор (до 3 раз)

Использование:
    python scripts/test_stage2_dmitriev.py
    python scripts/test_stage2_dmitriev.py --skip-historian
    python scripts/test_stage2_dmitriev.py --max-fc-iterations 1
"""
import argparse
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

try:
    import anthropic
except ImportError:
    print("[ERROR] pip install anthropic")
    sys.exit(1)

from pipeline_utils import (
    load_config,
    run_historian,
    run_ghostwriter,
    run_fact_checker,
    print_book_stats,
    print_fact_check_report,
)

CHARACTER_NAME = "Дмитриев Сергей Александрович"
NARRATOR_NAME = "Лена, Дима и Катя Дмитриевы"
NARRATOR_RELATION = "дети (дочь Лена, сын Дима, дочь Катя)"
PROJECT_ID = "dmitriev_stage2"

DEFAULT_FACT_MAP = ROOT / "exports" / "dmitriev_fact_map_v1.json"
DEFAULT_TRANSCRIPT = ROOT / "exports" / "transcripts" / "dmitriev_combined_transcript.txt"


def main():
    parser = argparse.ArgumentParser(description="Stage 2: Дмитриев — Историк + Писатель + Фактчекер")
    parser.add_argument("--fact-map", default=str(DEFAULT_FACT_MAP))
    parser.add_argument("--transcript", default=str(DEFAULT_TRANSCRIPT))
    parser.add_argument("--output-dir", default=str(ROOT / "exports"))
    parser.add_argument("--skip-historian", action="store_true")
    parser.add_argument("--skip-historian-pass2", action="store_true")
    parser.add_argument("--max-fc-iterations", type=int, default=3)
    args = parser.parse_args()

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("[ERROR] ANTHROPIC_API_KEY не задан")
        sys.exit(1)

    fact_map_path = Path(args.fact_map)
    if not fact_map_path.exists():
        print(f"[ERROR] Fact map не найден: {fact_map_path}")
        sys.exit(1)

    fact_map = json.loads(fact_map_path.read_text(encoding="utf-8"))
    print(f"\n[START] Stage 2: {CHARACTER_NAME}")
    print(f"[INPUT] Fact map: {fact_map_path.name} ({fact_map.get('processing_notes', {}).get('total_facts_extracted', '?')} фактов)")

    transcript_path = Path(args.transcript)
    if transcript_path.exists():
        transcript_text = transcript_path.read_text(encoding="utf-8")
        print(f"[INPUT] Транскрипт: {transcript_path.name} ({len(transcript_text)} символов)")
    else:
        transcript_text = ""
        print(f"[WARNING] Транскрипт не найден: {transcript_path}")

    transcripts = [{
        "interview_id": "int_001",
        "speaker_name": NARRATOR_NAME,
        "relation_to_subject": NARRATOR_RELATION,
        "text": transcript_text,
    }]

    cfg = load_config()
    print(f"[CONFIG] Историк:   {cfg['historian']['model']} ({cfg['historian']['prompt_file']})")
    print(f"[CONFIG] Писатель:  {cfg['ghostwriter']['model']} ({cfg['ghostwriter']['prompt_file']})")
    print(f"[CONFIG] Фактчекер: {cfg['fact_checker']['model']} ({cfg['fact_checker']['prompt_file']})")

    client = anthropic.Anthropic(api_key=api_key)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    # ─── Историк ──────────────────────────────────────────────────
    print("\n" + "─" * 60)
    print("ИСТОРИК")
    print("─" * 60)

    historical_context = {}
    if not args.skip_historian:
        historical_context = run_historian(client, fact_map, cfg=cfg)
        hist_path = out_dir / f"dmitriev_historian_{ts}.json"
        hist_path.write_text(
            json.dumps(historical_context, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"[SAVED] {hist_path.name}")
        if historical_context:
            print(f"[HISTORIAN] {historical_context.get('period_overview', '')[:120]}")
    else:
        print("[HISTORIAN] Пропущен (--skip-historian)")

    # ─── Писатель 1-й проход ──────────────────────────────────────
    print("\n" + "─" * 60)
    print("ПИСАТЕЛЬ — 1-й проход")
    print("─" * 60)

    book_draft_v1 = run_ghostwriter(
        client, fact_map, transcripts,
        subject_name=CHARACTER_NAME,
        project_id=PROJECT_ID,
        cfg=cfg,
        call_type="initial",
        version=1,
    )
    draft_v1_path = out_dir / f"dmitriev_book_draft_v1_{ts}.json"
    draft_v1_path.write_text(
        json.dumps(book_draft_v1, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[SAVED] {draft_v1_path.name}")
    print_book_stats(book_draft_v1)

    # ─── Писатель 2-й проход (интеграция историка) ────────────────
    if historical_context and not args.skip_historian_pass2:
        print("\n" + "─" * 60)
        print("ПИСАТЕЛЬ — 2-й проход (интеграция историка)")
        print("─" * 60)

        book_draft_v2 = run_ghostwriter(
            client, fact_map, transcripts,
            subject_name=CHARACTER_NAME,
            project_id=PROJECT_ID,
            cfg=cfg,
            call_type="revision",
            current_book=book_draft_v1,
            historical_context=historical_context,
            version=2,
        )
        draft_v2_path = out_dir / f"dmitriev_book_draft_v2_{ts}.json"
        draft_v2_path.write_text(
            json.dumps(book_draft_v2, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"[SAVED] {draft_v2_path.name}")
        print_book_stats(book_draft_v2)
        current_draft = book_draft_v2
    else:
        current_draft = book_draft_v1

    # ─── Фактчекер + revision цикл ────────────────────────────────
    print("\n" + "─" * 60)
    print(f"ФАКТЧЕКЕР (макс. {args.max_fc_iterations} итерации)")
    print("─" * 60)

    fc_report = None
    for iteration in range(1, args.max_fc_iterations + 1):
        print(f"\n[FC] Итерация {iteration}/{args.max_fc_iterations}")

        fc_report = run_fact_checker(
            client, current_draft, fact_map, transcripts,
            project_id=PROJECT_ID,
            phase="A",
            iteration=iteration,
            max_iterations=args.max_fc_iterations,
            cfg=cfg,
        )
        fc_path = out_dir / f"dmitriev_fc_report_iter{iteration}_{ts}.json"
        fc_path.write_text(
            json.dumps(fc_report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"[SAVED] {fc_path.name}")
        print_fact_check_report(fc_report)

        verdict = fc_report.get("verdict", "fail")
        if verdict == "pass":
            print(f"\n✅ [FACT_CHECKER] PASS на итерации {iteration}")
            break

        if iteration < args.max_fc_iterations:
            print(f"\n❌ [FACT_CHECKER] FAIL. Возвращаем Писателю (итерация {iteration + 1})...")
            errors = fc_report.get("errors", [])
            affected = list({e.get("chapter_id") for e in errors if e.get("chapter_id")})
            revision_scope = {
                "type": "fact_correction",
                "affected_chapters": affected or ["ch_01", "ch_02", "ch_03", "ch_04"],
                "instructions": f"Исправь {len(errors)} ошибок, найденных Фактчекером.",
                "fact_checker_errors": errors,
            }
            current_draft = run_ghostwriter(
                client, fact_map, transcripts,
                subject_name=CHARACTER_NAME,
                project_id=PROJECT_ID,
                cfg=cfg,
                call_type="revision",
                current_book=current_draft,
                revision_scope=revision_scope,
                version=iteration + 2,
            )
            rev_path = out_dir / f"dmitriev_book_draft_v{iteration + 2}_{ts}.json"
            rev_path.write_text(
                json.dumps(current_draft, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(f"[SAVED] {rev_path.name}")
            print_book_stats(current_draft)
        else:
            print(f"\n❌ [FACT_CHECKER] FAIL после {args.max_fc_iterations} итераций.")

    # ─── Финальный текст ──────────────────────────────────────────
    final_book_path = out_dir / f"dmitriev_book_FINAL_{ts}.json"
    final_book_path.write_text(json.dumps(current_draft, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[RESULT] Финальная книга: {final_book_path.name}")

    final_text = current_draft.get("book_text") or current_draft.get("text") or ""
    if not final_text and isinstance(current_draft, dict):
        for k, v in current_draft.items():
            if isinstance(v, str) and len(v) > 500:
                final_text = v
                break

    if final_text:
        final_txt_path = out_dir / f"dmitriev_book_FINAL_{ts}.txt"
        final_txt_path.write_text(final_text, encoding="utf-8")
        print(f"[RESULT] Финальный текст: {final_txt_path.name} ({len(final_text)} символов)")

    print(f"\n{'='*60}")
    print(f"Stage 2 завершён: {CHARACTER_NAME}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
