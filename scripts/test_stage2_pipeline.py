#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест пайплайна Stage 2: Историк + Писатель → Фактчекер
Субъект: Каракулина Валентина Ивановна

Флоу:
  1. Загружаем fact_map из Stage 1
  2. Параллельно: Историк + Писатель (1-й проход)
  3. Писатель (2-й проход: интеграция контекста Историка)
  4. Фактчекер → если fail: Писатель revision → повтор (до 3 раз)

Конфиг: prompts/pipeline_config.json
Shared логика: pipeline_utils.py

Использование:
    python scripts/test_stage2_pipeline.py
    python scripts/test_stage2_pipeline.py --fact-map exports/my_fact_map.json
    python scripts/test_stage2_pipeline.py --skip-historian
    python scripts/test_stage2_pipeline.py --skip-historian --max-fc-iterations 1
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
    save_run_manifest,
)
from pipeline_quality_gates import (
    run_stage2_text_gates, run_stage2_text_gates_variant_b,
    save_gate_report, summarize_failed_gates,
)

# ──────────────────────────────────────────────────────────────────
# Параметры субъекта
# ──────────────────────────────────────────────────────────────────
CHARACTER_NAME = "Каракулина Валентина Ивановна"
NARRATOR_NAME = "Татьяна Каракулина"
NARRATOR_RELATION = "дочь"
PROJECT_ID = "karakulina_stage2_test"

DEFAULT_FACT_MAP = ROOT / "exports" / "test_fact_map_karakulina_v5.json"
DEFAULT_TRANSCRIPT = ROOT / "exports" / "transcripts" / "karakulina_valentina_interview_assemblyai.txt"


def main():
    parser = argparse.ArgumentParser(description="Stage 2: Историк + Писатель + Фактчекер")
    parser.add_argument("--fact-map", default=str(DEFAULT_FACT_MAP),
                        help="Путь к fact_map JSON от Stage 1")
    parser.add_argument("--transcript", default=str(DEFAULT_TRANSCRIPT),
                        help="Путь к очищенному транскрипту")
    parser.add_argument("--output-dir", default=str(ROOT / "exports"),
                        help="Папка для сохранения результатов")
    parser.add_argument("--skip-historian", action="store_true",
                        help="Пропустить Историка. ОБЯЗАТЕЛЬНО указать --skip-reason")
    parser.add_argument("--skip-reason", type=str, default="",
                        help="Причина пропуска Историка (обязательно при --skip-historian)")
    parser.add_argument("--skip-historian-pass2", action="store_true",
                        help="Пропустить 2-й проход Писателя с историком")
    parser.add_argument("--max-fc-iterations", type=int, default=3,
                        help="Макс. итераций Фактчекер → Писатель (по умолчанию 3)")
    parser.add_argument("--allow-fc-fail", action="store_true",
                        help="Разрешить продолжение при FC FAIL после max итераций. "
                             "Без этого флага прогон останавливается. "
                             "Записывается в manifest как fc_fail_accepted: true.")
    parser.add_argument("--no-strict-gates", action="store_true",
                        help="Отключить блокирующие text-gates (не рекомендуется)")
    parser.add_argument("--variant-b", action="store_true",
                        help="Режим Вариант B: TR1-only основа. Пропускает gate_required_entities, "
                             "проверяет только непустоту глав и повторы.")
    args = parser.parse_args()

    # Guard: --skip-historian требует явной причины
    if args.skip_historian:
        if not args.skip_reason:
            print("❌ [ERROR] --skip-historian требует обязательного --skip-reason")
            print("   Пример: --skip-historian --skip-reason='testing rendering only'")
            print("   ⚠️  Книга без Историка не будет содержать исторических справок!")
            sys.exit(1)
        print(f"\n{'⚠️ ' * 20}")
        print(f"⚠️  ПРЕДУПРЕЖДЕНИЕ: Историк ПРОПУЩЕН")
        print(f"⚠️  Причина: {args.skip_reason}")
        print(f"⚠️  Книга не будет содержать исторических справок (правило 50% стр. гл.02)!")
        print(f"{'⚠️ ' * 20}\n")

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("[ERROR] ANTHROPIC_API_KEY не задан")
        sys.exit(1)

    # Загружаем fact_map
    fact_map_path = Path(args.fact_map)
    if not fact_map_path.exists():
        print(f"[ERROR] Fact map не найден: {fact_map_path}")
        print(f"  Сначала запусти Stage 1: python scripts/test_stage1_pipeline.py")
        sys.exit(1)

    fact_map = json.loads(fact_map_path.read_text(encoding="utf-8"))
    print(f"\n[START] Stage 2: {CHARACTER_NAME}")
    print(f"[INPUT] Fact map: {fact_map_path.name}")

    # Загружаем транскрипт (для Писателя и Фактчекера)
    transcript_path = Path(args.transcript)
    if transcript_path.exists():
        transcript_text = transcript_path.read_text(encoding="utf-8")
        print(f"[INPUT] Транскрипт: {transcript_path.name} ({len(transcript_text)} символов)")
    else:
        transcript_text = ""
        print(f"[WARNING] Транскрипт не найден: {transcript_path}. Продолжаем без него.")

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
    # Стык 3: Историк + Писатель (1-й проход) — параллельно
    # В синхронном варианте запускаем последовательно
    # ──────────────────────────────────────────────────────────────
    print("\n" + "─" * 60)
    print("СТЫК 3: Историк + Писатель 1-й проход")
    print("─" * 60)

    # Историк
    historical_context = {}
    if not args.skip_historian:
        historical_context = run_historian(client, fact_map, cfg=cfg)
        hist_path = out_dir / f"karakulina_historian_{ts}.json"
        hist_path.write_text(json.dumps(historical_context, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[SAVED] Историк: {hist_path.name}")
        if historical_context:
            print(f"[HISTORIAN] Период: {historical_context.get('period_overview', '')[:100]}")
    else:
        print(f"[HISTORIAN] SKIPPED — причина: {args.skip_reason}")

    # Писатель 1-й проход
    book_draft_v1 = run_ghostwriter(
        client, fact_map, transcripts,
        subject_name=CHARACTER_NAME,
        project_id=PROJECT_ID,
        cfg=cfg,
        call_type="initial",
        version=1,
    )
    draft_v1_path = out_dir / f"karakulina_book_draft_v1_{ts}.json"
    draft_v1_path.write_text(json.dumps(book_draft_v1, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[SAVED] Черновик v1: {draft_v1_path.name}")
    print_book_stats(book_draft_v1)

    # ──────────────────────────────────────────────────────────────
    # Стык 3.5: Историк → Писатель 2-й проход (интеграция контекста)
    # ──────────────────────────────────────────────────────────────
    if historical_context and not args.skip_historian_pass2:
        print("\n" + "─" * 60)
        print("СТЫК 3.5: Писатель 2-й проход (интеграция историка)")
        print("─" * 60)

        book_draft = run_ghostwriter(
            client, fact_map, transcripts,
            subject_name=CHARACTER_NAME,
            project_id=PROJECT_ID,
            cfg=cfg,
            call_type="revision",
            current_book=book_draft_v1,
            historical_context=historical_context,
            version=2,
        )
        draft_v2_path = out_dir / f"karakulina_book_draft_v2_{ts}.json"
        draft_v2_path.write_text(json.dumps(book_draft, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[SAVED] Черновик v2 (с историком): {draft_v2_path.name}")
        print_book_stats(book_draft)
    else:
        book_draft = book_draft_v1
        if args.skip_historian_pass2:
            print("[GHOSTWRITER pass2] Пропущен (--skip-historian-pass2)")

    # ──────────────────────────────────────────────────────────────
    # Стык 4: Писатель → Фактчекер (цикл до max_iterations)
    # ──────────────────────────────────────────────────────────────
    print("\n" + "─" * 60)
    print(f"СТЫК 4: Фактчекер (макс. {args.max_fc_iterations} итерации)")
    print("─" * 60)

    fc_report = None
    for iteration in range(1, args.max_fc_iterations + 1):
        fc_report = run_fact_checker(
            client, book_draft, fact_map, transcripts,
            project_id=PROJECT_ID,
            phase="A",
            iteration=iteration,
            max_iterations=args.max_fc_iterations,
            cfg=cfg,
        )
        fc_path = out_dir / f"karakulina_fc_report_iter{iteration}_{ts}.json"
        fc_path.write_text(json.dumps(fc_report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[SAVED] FC отчёт итерация {iteration}: {fc_path.name}")
        print_fact_check_report(fc_report)

        verdict = fc_report.get("verdict", "fail")
        if verdict == "pass":
            print(f"\n✅ [FACT_CHECKER] PASS на итерации {iteration}. Книга готова для Литредактора.")
            break

        # fail → возврат к Писателю
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
            book_draft = run_ghostwriter(
                client, fact_map, transcripts,
                subject_name=CHARACTER_NAME,
                project_id=PROJECT_ID,
                cfg=cfg,
                call_type="revision",
                current_book=book_draft,
                revision_scope=revision_scope,
                version=iteration + 2,
            )
            book_path = out_dir / f"karakulina_book_draft_v{iteration + 2}_{ts}.json"
            book_path.write_text(json.dumps(book_draft, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[SAVED] Черновик v{iteration + 2} (после правок): {book_path.name}")
            print_book_stats(book_draft)
        else:
            errors_remain = [e for e in fc_report.get("errors", []) if e.get("severity") in ("critical", "major")]
            print(f"\n❌ [FACT_CHECKER] FAIL после {args.max_fc_iterations} итераций.")
            print(f"   Critical+Major ошибок: {len(errors_remain)}")
            for e in errors_remain[:5]:
                print(f"   [{e.get('severity')}] {e.get('type','?')}: {e.get('description','')[:100]}")
            if not args.allow_fc_fail:
                print(f"\n🛑 ПРОГОН ОСТАНОВЛЕН: FC не прошёл после {args.max_fc_iterations} итераций.")
                print(f"   Для принудительного продолжения: --allow-fc-fail")
                print(f"   Диагностика: последний fc_report сохранён в {fc_path}")
                sys.exit(1)
            else:
                print(f"⚠️  --allow-fc-fail: продолжаем несмотря на FC FAIL. fc_fail_accepted=true в manifest.")

    # Финальное сохранение книги
    final_book_path = out_dir / f"karakulina_book_FINAL_{ts}.json"
    final_book_path.write_text(json.dumps(book_draft, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[RESULT] Финальная книга: {final_book_path.name}")
    if fc_report:
        print(f"[RESULT] Вердикт: {fc_report.get('verdict', '?').upper()}")

    # Сохраняем читаемый текст
    txt_path = out_dir / f"karakulina_book_FINAL_{ts}.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        chapters = book_draft.get("chapters", [])
        for ch in sorted(chapters, key=lambda x: x.get("order", 0)):
            f.write(f"\n{'=' * 60}\n{ch.get('title', ch['id'])}\n{'=' * 60}\n\n")
            f.write((ch.get("content") or "") + "\n")
    print(f"[RESULT] Текст книги: {txt_path.name}")

    # ──────────────────────────────────────────────────────────────
    # STRICT TEXT GATES (Phase 2)
    # ──────────────────────────────────────────────────────────────
    if args.variant_b:
        gate_report = run_stage2_text_gates_variant_b(book_draft, fact_map)
    else:
        gate_report = run_stage2_text_gates(book_draft, fact_map)
    gate_report_path = out_dir / f"karakulina_stage2_text_gates_{ts}.json"
    save_gate_report(gate_report_path, gate_report)
    print(f"[SAVED] Stage2 text gates: {gate_report_path.name}")
    gate_failed = bool(summarize_failed_gates(gate_report))

    save_run_manifest(
        output_dir=out_dir,
        prefix="karakulina",
        stage="stage2",
        project_id=PROJECT_ID,
        cfg=cfg,
        ts=ts,
        inputs={
            "fact_map_path": str(fact_map_path),
            "transcript_path": str(transcript_path),
            "skip_historian": args.skip_historian,
            "historian_skipped_reason": args.skip_reason if args.skip_historian else None,
            "skip_historian_pass2": args.skip_historian_pass2,
            "max_fc_iterations": args.max_fc_iterations,
            "fc_fail_accepted": args.allow_fc_fail if (fc_report and fc_report.get("verdict") != "pass") else False,
        },
        outputs={
            "historian_path": str(hist_path) if (not args.skip_historian and "hist_path" in locals()) else None,
            "book_draft_v1_path": str(draft_v1_path),
            "book_draft_v2_path": str(draft_v2_path) if "draft_v2_path" in locals() else None,
            "last_fc_report_path": str(fc_path) if fc_report else None,
            "final_book_json": str(final_book_path),
            "final_book_txt": str(txt_path),
            "final_verdict": fc_report.get("verdict") if fc_report else None,
            "text_gates_path": str(gate_report_path),
            "text_gates_passed": gate_report.get("passed"),
        },
        notes={"strict_gates_enabled": not args.no_strict_gates, "variant_b": args.variant_b},
    )

    if gate_failed and not args.no_strict_gates:
        print("\n❌ [STRICT_GATES] Stage2 не пройден: обнаружены критические проблемы текста.")
        if args.variant_b:
            print("   (Режим --variant-b: gate_required_entities пропущен, проверены непустота и повторы)")
        print("   См. отчёт:", gate_report_path.name)
        sys.exit(2)


if __name__ == "__main__":
    main()
