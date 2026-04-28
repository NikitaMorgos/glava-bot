#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stage 2 — Шаг 3: Фактчекер

Проверяет book_draft_v2 против fact_map и транскрипта.
Особое внимание: needs_verification, conflicts, confidence:"low".
Выдаёт verdict: pass | fail + errors + warnings + stats.

Использование:
    python scripts/test_stage2_step3.py
    python scripts/test_stage2_step3.py --book-draft exports/karakulina_book_draft_v2_....json
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

from pipeline_utils import load_config, load_prompt

PROJECT_ID = "karakulina_stage2_step3"
NARRATOR_NAME = "Татьяна Каракулина"

DEFAULT_BOOK_DRAFT = ROOT / "exports" / "karakulina_book_draft_v2_20260326_120522.json"
DEFAULT_FACT_MAP   = ROOT / "exports" / "test_fact_map_karakulina_v5.json"
DEFAULT_TRANSCRIPT = ROOT / "exports" / "transcripts" / "karakulina_valentina_interview_assemblyai.txt"


def validate_fact_check(agent_response: dict) -> dict | None:
    if not isinstance(agent_response, dict):
        return None
    verdict = agent_response.get("verdict")
    if verdict not in ("pass", "fail"):
        print(f"[VALIDATE] ❌ Нет verdict или неверное значение: {verdict!r}")
        return None
    if verdict == "fail":
        errors = agent_response.get("errors", [])
        if len(errors) == 0:
            print("[VALIDATE] ❌ verdict=fail, но errors пусты")
            return None
    return agent_response


def severity_icon(s: str) -> str:
    return {"critical": "🔴", "major": "🟠", "minor": "🟡"}.get(s, "⚪")


def print_fact_check_report(fc: dict):
    verdict = fc.get("verdict", "?")
    errors = fc.get("errors", [])
    warnings = fc.get("warnings", [])
    stats = fc.get("stats", {})

    verdict_icon = "✅ PASS" if verdict == "pass" else "❌ FAIL"
    print(f"\n{'='*60}")
    print(f"ФАКТЧЕКЕР — ОТЧЁТ   {verdict_icon}")
    print(f"{'='*60}")
    print(f"  Проверено фактов: {stats.get('facts_checked','?')}")
    print(f"  Ошибок:           {stats.get('errors_found', len(errors))}")
    print(f"  Предупреждений:   {stats.get('warnings_found', len(warnings))}")
    print(f"  Покрытие:         {stats.get('coverage_percent','?')}%")

    if errors:
        print(f"\n--- ОШИБКИ ({len(errors)}) ---")
        for e in errors:
            sev = e.get("severity", "?")
            etype = e.get("type", "?")
            print(f"\n  {severity_icon(sev)} [{sev.upper()}] {etype} | {e.get('chapter_id','?')}")
            print(f"  Написано:  {e.get('what_is_written','?')[:120]}")
            print(f"  Должно:    {e.get('what_should_be','?')[:120]}")
            if e.get("source_quote"):
                print(f"  Источник:  «{e['source_quote'][:100]}»")
            print(f"  Правка:    {e.get('fix_instruction','?')[:120]}")

    if warnings:
        print(f"\n--- ПРЕДУПРЕЖДЕНИЯ ({len(warnings)}) ---")
        for w in warnings:
            print(f"  ⚠️  [{w.get('type','?')}] {w.get('description','?')[:120]}")
            if w.get("suggestion"):
                print(f"      → {w['suggestion'][:100]}")

    print()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--book-draft", default=str(DEFAULT_BOOK_DRAFT))
    parser.add_argument("--fact-map",   default=str(DEFAULT_FACT_MAP))
    parser.add_argument("--transcript", default=str(DEFAULT_TRANSCRIPT))
    args = parser.parse_args()

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("[ERROR] ANTHROPIC_API_KEY не задан")
        sys.exit(1)

    for p in (Path(args.book_draft), Path(args.fact_map), Path(args.transcript)):
        if not p.exists():
            print(f"[ERROR] Файл не найден: {p}")
            sys.exit(1)

    book_draft_raw = json.loads(Path(args.book_draft).read_text(encoding="utf-8"))
    fact_map       = json.loads(Path(args.fact_map).read_text(encoding="utf-8"))
    transcript     = Path(args.transcript).read_text(encoding="utf-8")

    # Нормализуем book_draft
    if "book_draft" in book_draft_raw:
        book_draft = book_draft_raw["book_draft"]
    else:
        book_draft = book_draft_raw

    chapters = book_draft.get("chapters", [])
    total_chars = sum(
        len(ch.get("content", "")) or
        sum(len(p.get("text","")) for p in ch.get("paragraphs",[]))
        for ch in chapters
    )
    print(f"\n[START] Фактчекер | {len(chapters)} глав | {total_chars} символов")
    print(f"[INPUT] book_draft: {Path(args.book_draft).name}")
    print(f"[INPUT] fact_map:   {Path(args.fact_map).name}")

    cfg    = load_config()
    fc_cfg = cfg["fact_checker"]
    system_prompt = load_prompt(fc_cfg["prompt_file"])

    print(f"[CONFIG] Фактчекер: {fc_cfg['model']} "
          f"temp={fc_cfg['temperature']} max_tokens={fc_cfg['max_tokens']}")

    user_message = {
        "context": {
            "project_id": PROJECT_ID,
            "phase": "A",
            "call_type": "initial",
            "iteration": 1,
            "max_iterations": 3,
            "previous_agent": "ghostwriter",
            "instruction": (
                "Проверь текст книги на фактическую точность. "
                "Сверь с картой фактов и протоколами интервью. "
                "Факты с needs_verification: true — проверяй особо внимательно, "
                "помечай как warning если использованы без оговорок. "
                "Факты с confidence: 'low' — проверь, не превратил ли Писатель предположение в утверждение (тип: confidence_upgrade). "
                "Конфликты из поля conflicts — проверь, что Писатель не принял одну из сторон без оговорки. "
                "Выдай вердикт: pass или fail."
            ),
        },
        "data": {
            "book_draft": book_draft,
            "fact_map": fact_map,
            "transcripts": [{"speaker": NARRATOR_NAME, "text": transcript}],
        },
    }

    client = anthropic.Anthropic(api_key=api_key)
    out_dir = ROOT / "exports"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    print(f"\n[FACT CHECKER] Запускаю...")
    start = datetime.now()

    raw_parts = []
    with client.messages.stream(
        model=fc_cfg["model"],
        max_tokens=fc_cfg["max_tokens"],
        temperature=fc_cfg.get("temperature", 0.1),
        system=system_prompt,
        messages=[{"role": "user", "content": json.dumps(user_message, ensure_ascii=False)}],
    ) as stream:
        for text in stream.text_stream:
            raw_parts.append(text)
        final = stream.get_final_message()

    elapsed = (datetime.now() - start).total_seconds()
    raw = "".join(raw_parts)
    in_tok = final.usage.input_tokens
    out_tok = final.usage.output_tokens
    print(f"[FACT CHECKER] Готово за {elapsed:.1f}с | токены: in={in_tok}, out={out_tok}")

    # Сохраняем сырой ответ
    raw_path = out_dir / f"karakulina_factcheck_raw_{ts}.json"
    raw_path.write_text(raw, encoding="utf-8")

    # Парсим JSON
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:])
        if text.endswith("```"):
            text = text[:-3].strip()
    s, e = text.find("{"), text.rfind("}")
    try:
        fc_raw = json.loads(text[s:e+1]) if s != -1 and e > s else json.loads(text)
    except json.JSONDecodeError as ex:
        print(f"[ERROR] JSON parse failed: {ex}")
        print(f"[SAVED] Сырой ответ: {raw_path}")
        sys.exit(1)

    fc_result = validate_fact_check(fc_raw)
    if not fc_result:
        print("[FACT CHECKER] ❌ Валидация не пройдена. Сырой ответ:")
        print(json.dumps(fc_raw, ensure_ascii=False, indent=2)[:1000])
        sys.exit(1)

    # Сохраняем отчёт
    report_path = out_dir / f"karakulina_factcheck_report_{ts}.json"
    report_path.write_text(
        json.dumps(fc_result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[SAVED] Отчёт: {report_path}")

    print_fact_check_report(fc_result)

    # Итог
    verdict = fc_result.get("verdict")
    errors  = fc_result.get("errors", [])
    crit    = [e for e in errors if e.get("severity") == "critical"]

    print(f"{'='*60}")
    print(f"ШАГ 3 ЗАВЕРШЁН   {'✅ PASS' if verdict=='pass' else '❌ FAIL'}")
    print(f"{'='*60}")
    if verdict == "pass":
        print("  Текст прошёл проверку → готов к Литредактору (Этап 3)")
    else:
        print(f"  Critical ошибок: {len(crit)} | Всего ошибок: {len(errors)}")
        print(f"  Следующий шаг: запустить revision (Ghostwriter исправляет ошибки)")
        print(f"  Отчёт: {report_path}")


if __name__ == "__main__":
    main()
