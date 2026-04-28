#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stage 2: Историк + Писатель → Фактчекер
Субъект: Королькова Елена Андреевна

Флоу:
  1. Загружаем fact_map из Stage 1
  2. Историк + Писатель (1-й проход)
  3. Писатель (2-й проход: интеграция контекста Историка)
  4. Фактчекер → если fail: Писатель revision → повтор (до 3 раз)

Конфиг: prompts/pipeline_config.json

Использование:
    python scripts/test_stage2_korolkova.py
    python scripts/test_stage2_korolkova.py --skip-historian --max-fc-iterations 1
"""
import argparse
import json
import os
import sys
import time
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

# ──────────────────────────────────────────────────────────────────
# Параметры субъекта
# ──────────────────────────────────────────────────────────────────
CHARACTER_NAME = "Королькова Елена Андреевна"
NARRATOR_NAME = "Дочь"
NARRATOR_RELATION = "дочь"
PROJECT_ID = "korolkova_stage2_test"
PREFIX = "korolkova"

DEFAULT_FACT_MAP = ROOT / "exports" / "korolkova_fact_map_v2.json"
DEFAULT_TRANSCRIPT = ROOT / "exports" / "korolkova_cleaned_transcript.txt"


def run_with_retry(fn, *args, max_retries=4, **kwargs):
    """Обёртка с retry при overloaded_error."""
    for attempt in range(1, max_retries + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            err = str(e)
            if "overloaded" in err.lower() and attempt < max_retries:
                wait = 30 * attempt
                print(f"[RETRY] Попытка {attempt}/{max_retries} — API перегружен, ждём {wait}с...")
                time.sleep(wait)
            else:
                raise


def main():
    parser = argparse.ArgumentParser(description="Stage 2 Королькова")
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
    print(f"[INPUT] Fact map: {fact_map_path.name}")

    transcript_path = Path(args.transcript)
    if transcript_path.exists():
        transcript_text = transcript_path.read_text(encoding="utf-8")
        print(f"[INPUT] Транскрипт: {transcript_path.name} ({len(transcript_text)} символов)")
    else:
        transcript_text = ""
        print(f"[WARNING] Транскрипт не найден. Продолжаем без него.")

    transcripts = [{
        "interview_id": "int_001",
        "speaker_name": NARRATOR_NAME,
        "relation_to_subject": NARRATOR_RELATION,
        "text": transcript_text,
    }]

    cfg = load_config()
    print(f"[CONFIG] Историк: {cfg['historian']['model']} ({cfg['historian']['prompt_file']})")
    print(f"[CONFIG] Писатель: {cfg['ghostwriter']['model']} ({cfg['ghostwriter']['prompt_file']})")
    print(f"[CONFIG] Фактчекер: {cfg['fact_checker']['model']} ({cfg['fact_checker']['prompt_file']})")

    client = anthropic.Anthropic(api_key=api_key)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    # ──────────────────────────────────────────────────────────────
    # Стык 3: Историк + Писатель (1-й проход)
    # ──────────────────────────────────────────────────────────────
    print("\n" + "─" * 60)
    print("СТЫК 3: Историк + Писатель 1-й проход")
    print("─" * 60)

    historical_context = {}
    if not args.skip_historian:
        historical_context = run_with_retry(run_historian, client, fact_map, cfg=cfg)
        hist_path = out_dir / f"{PREFIX}_historian_{ts}.json"
        hist_path.write_text(json.dumps(historical_context, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[SAVED] Историк: {hist_path.name}")
        if historical_context:
            print(f"[HISTORIAN] Период: {historical_context.get('period_overview', '')[:100]}")
    else:
        print("[HISTORIAN] Пропущен (--skip-historian)")

    book_draft_v1 = run_with_retry(
        run_ghostwriter,
        client, fact_map, transcripts,
        subject_name=CHARACTER_NAME,
        project_id=PROJECT_ID,
        cfg=cfg,
        call_type="initial",
        version=1,
    )
    draft_v1_path = out_dir / f"{PREFIX}_book_draft_v1_{ts}.json"
    draft_v1_path.write_text(json.dumps(book_draft_v1, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[SAVED] Черновик v1: {draft_v1_path.name}")
    print_book_stats(book_draft_v1)

    # ──────────────────────────────────────────────────────────────
    # Стык 3.5: Писатель 2-й проход (интеграция историка)
    # ──────────────────────────────────────────────────────────────
    if historical_context and not args.skip_historian_pass2:
        print("\n" + "─" * 60)
        print("СТЫК 3.5: Писатель 2-й проход (интеграция историка)")
        print("─" * 60)

        book_draft = run_with_retry(
            run_ghostwriter,
            client, fact_map, transcripts,
            subject_name=CHARACTER_NAME,
            project_id=PROJECT_ID,
            cfg=cfg,
            call_type="revision",
            current_book=book_draft_v1,
            historical_context=historical_context,
            version=2,
        )
        draft_v2_path = out_dir / f"{PREFIX}_book_draft_v2_{ts}.json"
        draft_v2_path.write_text(json.dumps(book_draft, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[SAVED] Черновик v2 (с историком): {draft_v2_path.name}")
        print_book_stats(book_draft)
    else:
        book_draft = book_draft_v1
        if args.skip_historian_pass2:
            print("[GHOSTWRITER pass2] Пропущен")

    # ──────────────────────────────────────────────────────────────
    # Стык 4: Фактчекер (цикл до max_iterations)
    # ──────────────────────────────────────────────────────────────
    print("\n" + "─" * 60)
    print(f"СТЫК 4: Фактчекер (макс. {args.max_fc_iterations} итерации)")
    print("─" * 60)

    fc_report = None
    for iteration in range(1, args.max_fc_iterations + 1):
        fc_report = run_with_retry(
            run_fact_checker,
            client, book_draft, fact_map, transcripts,
            project_id=PROJECT_ID,
            phase="A",
            iteration=iteration,
            max_iterations=args.max_fc_iterations,
            cfg=cfg,
        )
        fc_path = out_dir / f"{PREFIX}_fc_report_iter{iteration}_{ts}.json"
        fc_path.write_text(json.dumps(fc_report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[SAVED] FC отчёт итерация {iteration}: {fc_path.name}")
        print_fact_check_report(fc_report)

        verdict = fc_report.get("verdict", "fail")
        if verdict == "pass":
            print(f"\n✅ [FACT_CHECKER] PASS на итерации {iteration}. Книга готова для Литредактора.")
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
            book_draft = run_with_retry(
                run_ghostwriter,
                client, fact_map, transcripts,
                subject_name=CHARACTER_NAME,
                project_id=PROJECT_ID,
                cfg=cfg,
                call_type="revision",
                current_book=book_draft,
                revision_scope=revision_scope,
                version=iteration + 2,
            )
            book_path = out_dir / f"{PREFIX}_book_draft_v{iteration + 2}_{ts}.json"
            book_path.write_text(json.dumps(book_draft, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[SAVED] Черновик v{iteration + 2} (после правок): {book_path.name}")
            print_book_stats(book_draft)
        else:
            print(f"\n❌ [FACT_CHECKER] FAIL после {args.max_fc_iterations} итераций. ЭСКАЛАЦИЯ → Продюсер.")

    # Финальное сохранение
    final_book_path = out_dir / f"{PREFIX}_book_FINAL_{ts}.json"
    final_book_path.write_text(json.dumps(book_draft, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[RESULT] Финальная книга: {final_book_path.name}")
    if fc_report:
        print(f"[RESULT] Вердикт: {fc_report.get('verdict', '?').upper()}")

    # Финальный текст
    txt_path = out_dir / f"{PREFIX}_book_FINAL_{ts}.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        bd = book_draft.get("book_draft", book_draft)
        chapters = bd.get("chapters", [])
        for ch in sorted(chapters, key=lambda x: x.get("order", 0)):
            f.write(f"\n{'=' * 60}\n{ch.get('title', ch.get('id', ''))}\n{'=' * 60}\n\n")
            f.write(ch.get("content", "") + "\n")
    print(f"[RESULT] Текст книги: {txt_path.name}")

    return final_book_path, fc_report


if __name__ == "__main__":
    main()
