#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase B: content_addition — вплетение нового интервью в существующую книгу.

Использование:
    python scripts/test_stage2_phase_b.py \
        --current-book exports/karakulina_book_FINAL_stage3_20260412_132158.json \
        --new-transcript exports/karakulina_cleaned_transcript_20260403.txt \
        --speaker-name "Татьяна Каракулина" \
        --speaker-relation "дочь" \
        --fact-map checkpoints/karakulina/fact_map.json \
        --instructions "Вплети материал нового интервью..."
"""
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import anthropic

from pipeline_utils import (
    load_config, load_prompt, save_run_manifest, print_book_stats,
    run_fact_checker, run_fact_extractor, merge_fact_maps,
)

CHARACTER_NAME = "Каракулина Валентина Ивановна"
PROJECT_ID = "karakulina_phase_b"

DEFAULT_CURRENT_BOOK  = ROOT / "exports" / "karakulina_book_FINAL_stage3_20260412_132158.json"
DEFAULT_NEW_TRANSCRIPT = ROOT / "exports" / "karakulina_cleaned_transcript_20260403.txt"
DEFAULT_FACT_MAP       = ROOT / "checkpoints" / "karakulina" / "fact_map.json"
DEFAULT_PREFIX         = "karakulina"

DEFAULT_INSTRUCTIONS = (
    "Вплети материал нового интервью с Татьяной (дочерью Валентины, записанного внуком Никитой) "
    "в существующие главы. Не меняй общую структуру книги и не удаляй существующие главы. "
    "Добавляй конкретные детали, истории и наблюдения из нового интервью в соответствующие главы:\n"
    "— История с огурцами и чемоданом Маргося (конкретный эпизод, иллюстрирующий напряжение)\n"
    "— Зависимость Валентины от мнения доктора Нинвана (Полсачева) — раздражала домашних\n"
    "— Продажа дачи: Валентина жалела об этом, это была её отдушина\n"
    "— Ежедневный распорядок в химинституте: всегда занята, редко отдыхала\n"
    "— Запах ванили и крема — ассоциация с домом бабушки\n"
    "— Нюансы конфликта с Маргосём: история со счётчиком и непрошенными советами\n"
    "— После смерти мужа: Татьяна осталась с мамой, потому что та нуждалась в ком-то\n"
    "— Традиция «посидеть на дорожку»\n"
    "— Как она пекла для коллег в поликлинике — ей это приносило уважение и признание\n"
    "Расширяй ch_02, ch_03, ch_04. Epilogue не трогай."
)


def run_phase_b_ghostwriter(
    client,
    fact_map: dict,
    current_book: dict,
    new_transcripts: list[dict],
    instructions: str,
    cfg: dict,
) -> dict:
    """Запускает Ghostwriter в Phase B режиме (content_addition)."""
    gw_cfg = cfg["ghostwriter"]
    model = gw_cfg["model"]
    max_tokens = gw_cfg["max_tokens"]
    temperature = gw_cfg.get("temperature", 0.5)
    system_prompt = load_prompt(gw_cfg["prompt_file"])

    affected = ["ch_02", "ch_03", "ch_04"]

    user_message = {
        "phase": "B",
        "project_id": PROJECT_ID,
        "subject": {"name": CHARACTER_NAME},
        "fact_map": fact_map,
        "transcripts": new_transcripts,
        "current_book": {
            "chapters": current_book.get("chapters", [])
        },
        "revision_scope": {
            "type": "content_addition",
            "affected_chapters": affected,
            "instructions": instructions,
            "new_facts": [],
        },
    }

    print(f"\n[GHOSTWRITER Phase B] Запускаю ({model}, max_tokens={max_tokens})...")
    print(f"[GHOSTWRITER Phase B] Затронутые главы: {affected}")
    start = datetime.now()

    raw_parts = []
    with client.messages.stream(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system_prompt,
        messages=[{"role": "user", "content": json.dumps(user_message, ensure_ascii=False)}],
    ) as stream:
        for text in stream.text_stream:
            raw_parts.append(text)
        final_msg = stream.get_final_message()

    elapsed = (datetime.now() - start).total_seconds()
    raw = "".join(raw_parts).strip()
    usage = final_msg.usage
    print(f"[GHOSTWRITER Phase B] Готово за {elapsed:.1f}с | {len(raw)} символов | токены: in={usage.input_tokens}, out={usage.output_tokens}")

    # Парсим JSON
    s, e = raw.find("{"), raw.rfind("}")
    if s != -1 and e > s:
        try:
            result = json.loads(raw[s:e + 1])
            return result
        except json.JSONDecodeError as ex:
            print(f"[GHOSTWRITER Phase B] ❌ JSON parse error: {ex}")
    print("[GHOSTWRITER Phase B] ❌ Не удалось распарсить ответ")
    return {}


def merge_phase_b_into_book(current_book: dict, phase_b_result: dict) -> dict:
    """
    Мёржит обновлённые главы из Phase B в исходную книгу.
    Phase B возвращает только is_modified=True главы — остальные берём из current_book.

    ВАЖНО: ch_01.bio_data и ch_01.timeline ВСЕГДА берутся из current_book —
    Phase B не должна перезаписывать структурированные данные героя.
    """
    current_chapters = {ch["id"]: ch for ch in current_book.get("chapters", [])}
    updated_chapters = {ch["id"]: ch for ch in phase_b_result.get("chapters", [])}

    merged = []
    for ch_id, ch in current_chapters.items():
        if ch_id in updated_chapters and updated_chapters[ch_id].get("is_modified"):
            print(f"[MERGE] Обновлена глава: {ch_id}")
            merged_ch = updated_chapters[ch_id]
            # Защита ch_01: bio_data и timeline неизменяемы Phase B
            if ch_id == "ch_01":
                orig_bio = ch.get("bio_data")
                orig_timeline = ch.get("timeline")
                if orig_bio:
                    merged_ch = dict(merged_ch)
                    merged_ch["bio_data"] = orig_bio
                    print(f"[MERGE] ch_01.bio_data защищён из Stage 3 (Phase B не перезаписывает)")
                if orig_timeline:
                    merged_ch = dict(merged_ch)
                    merged_ch["timeline"] = orig_timeline
                    print(f"[MERGE] ch_01.timeline защищён из Stage 3 ({len(orig_timeline)} этапов)")
            merged.append(merged_ch)
        else:
            merged.append(ch)

    # Если Phase B вернул новые главы которых нет в current
    for ch_id, ch in updated_chapters.items():
        if ch_id not in current_chapters:
            print(f"[MERGE] Добавлена новая глава: {ch_id}")
            merged.append(ch)

    # Сортируем по order
    merged.sort(key=lambda c: c.get("order", 99))

    result = dict(current_book)
    result["chapters"] = merged
    result["callouts"] = phase_b_result.get("callouts", current_book.get("callouts", []))
    result["version"] = current_book.get("version", 1) + 1
    result["phase"] = "B"
    return result


def main():
    parser = argparse.ArgumentParser(description="Phase B: content_addition — вплетение нового интервью")
    parser.add_argument("--current-book", default=str(DEFAULT_CURRENT_BOOK))
    parser.add_argument("--new-transcript", default=str(DEFAULT_NEW_TRANSCRIPT))
    parser.add_argument("--speaker-name", default="Татьяна Каракулина",
                        help="Имя рассказчика нового интервью")
    parser.add_argument("--speaker-relation", default="дочь",
                        help="Отношение к герою")
    parser.add_argument("--fact-map", default=str(DEFAULT_FACT_MAP))
    parser.add_argument("--output-dir", default=str(ROOT / "exports"))
    parser.add_argument("--prefix", default=DEFAULT_PREFIX)
    parser.add_argument("--instructions", default=DEFAULT_INSTRUCTIONS)
    parser.add_argument("--max-fc-iterations", type=int, default=1,
                        help="Макс. итераций FC в Phase B (по умолчанию 1, рекомендуется 3)")
    parser.add_argument("--allow-fc-fail", action="store_true",
                        help="Разрешить продолжение при FC FAIL после max итераций. "
                             "Без этого флага прогон останавливается. "
                             "Записывается в manifest как fc_fail_accepted: true.")
    parser.add_argument("--no-incremental-fe", action="store_true",
                        help="Отключить Incremental FactExtractor перед Ghostwriter Phase B")
    parser.add_argument("--variant-b", action="store_true",
                        help="Проверить рост объёма после Phase B (мин. +20%)")
    args = parser.parse_args()

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("[ERROR] ANTHROPIC_API_KEY не задан")
        sys.exit(1)

    # Загружаем файлы
    current_book_path = Path(args.current_book)
    if not current_book_path.exists():
        print(f"[ERROR] current_book не найден: {current_book_path}")
        sys.exit(1)
    raw_book = json.loads(current_book_path.read_text(encoding="utf-8"))
    # Stage3 хранит итоговую книгу под ключом 'book_final'
    current_book = raw_book.get("book_final") or raw_book
    print(f"[INPUT] current_book: {current_book_path.name}")
    print(f"[INPUT] Глав: {len(current_book.get('chapters', []))}")

    transcript_path = Path(args.new_transcript)
    if not transcript_path.exists():
        print(f"[ERROR] Транскрипт не найден: {transcript_path}")
        sys.exit(1)
    transcript_text = transcript_path.read_text(encoding="utf-8")
    print(f"[INPUT] Новый транскрипт: {transcript_path.name} ({len(transcript_text)} символов)")

    fact_map_path = Path(args.fact_map)
    fact_map = json.loads(fact_map_path.read_text(encoding="utf-8")) if fact_map_path.exists() else {}
    print(f"[INPUT] fact_map: {fact_map_path.name}")

    new_transcripts = [{
        "interview_id": "int_tatyana_002",
        "speaker_name": args.speaker_name,
        "relation_to_subject": args.speaker_relation,
        "text": transcript_text,
    }]

    cfg = load_config()
    print(f"\n[CONFIG] Писатель: {cfg['ghostwriter']['model']} ({cfg['ghostwriter']['prompt_file']})")
    print(f"[CONFIG] Фактчекер: {cfg['fact_checker']['model']} ({cfg['fact_checker']['prompt_file']})")

    client = anthropic.Anthropic(api_key=api_key)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    prefix = args.prefix

    # ── Incremental FactExtractor на новом транскрипте ──────────────────────
    if not args.no_incremental_fe:
        print(f"\n{'─'*60}")
        print("Incremental FactExtractor (TR2 → обновлённый fact_map)")
        print(f"{'─'*60}")
        try:
            subject = fact_map.get("subject", {}) or {}
            incremental_fm = run_fact_extractor(
                client,
                cleaned_text=transcript_text,
                subject_name=CHARACTER_NAME,
                narrator_name=args.speaker_name,
                narrator_relation=args.speaker_relation,
                project_id=PROJECT_ID + "_incremental_fe",
                known_birth_year=subject.get("birth_year"),
                known_details=None,
                existing_facts=fact_map,
                cfg=cfg,
            )
            merged_fm_path = out_dir / f"{prefix}_fact_map_phase_b_{ts}.json"
            merged_fm = merge_fact_maps(fact_map, incremental_fm)
            merged_fm_path.write_text(json.dumps(merged_fm, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[SAVED] Обновлённый fact_map: {merged_fm_path.name}")
            new_persons = [p for p in merged_fm.get("persons", []) if p.get("is_new")]
            new_events = [e for e in merged_fm.get("timeline", []) if e.get("is_new")]
            print(f"[INCREMENTAL FE] Новых персон: {len(new_persons)} | Новых событий: {len(new_events)}")
            fact_map = merged_fm
        except Exception as exc:
            print(f"[WARN] Incremental FactExtractor упал: {exc} — используем исходный fact_map")
    else:
        print("[SKIP] Incremental FactExtractor отключён (--no-incremental-fe)")

    print(f"\n{'─'*60}")
    print("Phase B: Ghostwriter content_addition")
    print(f"{'─'*60}")

    # Ghostwriter Phase B
    phase_b_raw = run_phase_b_ghostwriter(
        client, fact_map, current_book, new_transcripts, args.instructions, cfg
    )

    if not phase_b_raw or not phase_b_raw.get("chapters"):
        print("[ERROR] Ghostwriter Phase B не вернул главы")
        sys.exit(1)

    # Сохраняем сырой ответ Phase B
    raw_path = out_dir / f"{prefix}_phase_b_raw_{ts}.json"
    raw_path.write_text(json.dumps(phase_b_raw, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[SAVED] Phase B raw: {raw_path.name}")

    # Мёрджим обновлённые главы
    merged_book = merge_phase_b_into_book(current_book, phase_b_raw)
    print_book_stats(merged_book)

    merged_path = out_dir / f"{prefix}_book_phase_b_{ts}.json"
    merged_path.write_text(json.dumps(merged_book, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[SAVED] Merged book: {merged_path.name}")

    # Volume growth gate (Variant B)
    if args.variant_b:
        from pipeline_quality_gates import gate_phase_b_volume_growth
        vg = gate_phase_b_volume_growth(current_book, merged_book, min_growth=0.20)
        vg_d = vg.details
        growth_pct = round(vg_d.get("actual_growth", 0) * 100, 1)
        status = "✅ PASS" if vg.passed else "⚠️ FAIL"
        print(f"[VARIANT_B] Volume growth: {vg_d.get('chars_before')} → "
              f"{vg_d.get('chars_after')} симв. (+{growth_pct}%) {status}")
        if not vg.passed:
            print(f"[VARIANT_B] Ожидался рост ≥20%. Ghostwriter Phase B добавил недостаточно материала.")

    print(f"\n{'─'*60}")
    print(f"Фактчекер (макс. {args.max_fc_iterations} итерации)")
    print(f"{'─'*60}")

    # Все транскрипты для Фактчекера (original + new)
    original_transcript_path = ROOT / "exports" / "karakulina_meeting_transcript_20260403.txt"
    original_text = original_transcript_path.read_text(encoding="utf-8") if original_transcript_path.exists() else ""
    all_transcripts = [
        {"interview_id": "int_001", "speaker_name": "Татьяна Каракулина",
         "relation_to_subject": "дочь", "text": original_text},
        new_transcripts[0],
    ]

    # В Phase B FC проверяем только затронутые главы (affected_chapters_only)
    affected_chapters = ["ch_02", "ch_03", "ch_04"]

    book_draft = merged_book
    fc_path = None
    for iteration in range(1, args.max_fc_iterations + 1):
        fc_report = run_fact_checker(
            client, book_draft, fact_map, all_transcripts,
            project_id=PROJECT_ID, cfg=cfg,
            phase="B",
            max_iterations=args.max_fc_iterations, iteration=iteration,
            affected_chapters=affected_chapters,
        )
        fc_path = out_dir / f"{prefix}_phase_b_fc_report_iter{iteration}_{ts}.json"
        fc_path.write_text(json.dumps(fc_report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[SAVED] FC отчёт итерация {iteration}: {fc_path.name}")

        verdict = fc_report.get("verdict", "fail")
        errors = [e for e in fc_report.get("errors", []) if e.get("severity") in ("critical", "major")]
        print(f"\n[FACT_CHECKER] Итерация {iteration}: {verdict.upper()} | Critical+Major: {len(errors)}")

        if verdict == "pass" or not errors:
            print(f"✅ [FACT_CHECKER] PASS на итерации {iteration}.")
            break

        if iteration < args.max_fc_iterations and errors:
            print(f"[FACT_CHECKER] Отправляем Писателю на правку ({len(errors)} ошибок)...")
            revision_scope = {
                "type": "fact_correction",
                "affected_chapters": list({e.get("chapter_id", "ch_02") for e in errors}),
                "instructions": "Исправь фактические ошибки согласно отчёту Фактчекера.",
                "conflicts": [{"fact_id": e.get("fact_id", ""), "description": e.get("description", "")}
                              for e in errors],
            }
            book_draft = run_phase_b_ghostwriter(
                client, fact_map, book_draft, all_transcripts,
                f"Исправь ошибки Фактчекера: {json.dumps(errors[:5], ensure_ascii=False)}",
                cfg,
            )
            if book_draft and book_draft.get("chapters"):
                draft_path = out_dir / f"{prefix}_phase_b_draft_v{iteration+1}_{ts}.json"
                draft_path.write_text(json.dumps(book_draft, ensure_ascii=False, indent=2), encoding="utf-8")
                book_draft = merge_phase_b_into_book(merged_book, book_draft)
        else:
            # Последняя итерация завершилась с FAIL
            errors_remain = [e for e in fc_report.get("errors", []) if e.get("severity") in ("critical", "major")]
            print(f"\n❌ [FACT_CHECKER Phase B] FAIL после {args.max_fc_iterations} итераций.")
            print(f"   Critical+Major ошибок: {len(errors_remain)}")
            for e in errors_remain[:5]:
                print(f"   [{e.get('severity')}] {e.get('type','?')}: {e.get('description','')[:100]}")
            if not args.allow_fc_fail:
                print(f"\n🛑 ПРОГОН ОСТАНОВЛЕН: FC Phase B не прошёл после {args.max_fc_iterations} итераций.")
                print(f"   Для принудительного продолжения: --allow-fc-fail")
                print(f"   Диагностика: последний fc_report сохранён в {fc_path}")
                sys.exit(1)
            else:
                print(f"⚠️  --allow-fc-fail: продолжаем несмотря на FC FAIL Phase B. fc_fail_accepted=true в manifest.")

    # Финальный файл
    final_path = out_dir / f"{prefix}_book_FINAL_phase_b_{ts}.json"
    final_path.write_text(json.dumps(book_draft, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[RESULT] Финальная книга Phase B: {final_path.name}")

    # TXT-версия
    txt_path = out_dir / f"{prefix}_FINAL_phase_b_{ts}.txt"
    lines = []
    for ch in book_draft.get("chapters", []):
        lines.append(f"\n{'='*60}\n{ch.get('id','?')} | {ch.get('title','')}\n{'='*60}\n")
        content = ch.get("content") or ""
        if content:
            lines.append(content)
        elif ch.get("bio_data"):
            lines.append("[bio_data структура — раскрывается в PDF]\n")
    txt_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[RESULT] TXT: {txt_path.name}")

    # Run manifest
    save_run_manifest(
        output_dir=out_dir,
        prefix=prefix,
        stage="phase_b",
        project_id=PROJECT_ID,
        cfg=cfg,
        ts=ts,
        inputs={
            "current_book_path": str(current_book_path),
            "new_transcript_path": str(transcript_path),
            "fact_map_path": str(fact_map_path),
            "speaker_name": args.speaker_name,
            "speaker_relation": args.speaker_relation,
        },
        outputs={
            "phase_b_raw_path": str(raw_path),
            "merged_book_path": str(merged_path),
            "fc_report_path": str(fc_path) if fc_path else None,
            "final_book_json": str(final_path),
            "final_book_txt": str(txt_path),
        },
        notes={
            "instructions_preview": args.instructions[:200],
            "max_fc_iterations": args.max_fc_iterations,
            "fc_fail_accepted": args.allow_fc_fail if (fc_report and fc_report.get("verdict") != "pass") else False,
            "fc_final_verdict": fc_report.get("verdict", "unknown") if fc_report else "no_fc_run",
        },
    )

    print(f"\n✅ Phase B завершён. Финальный файл: {final_path.name}")


if __name__ == "__main__":
    main()
