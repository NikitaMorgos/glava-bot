#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stage 2 — Возврат A: Ghostwriter исправляет ошибки Фактчекера (итерация 2).

Загружает отчёт фактчекера, исключает помеченные ошибки (исторические вставки),
отправляет Ghostwriter точечные правки.

Использование:
    python scripts/test_stage2_revision.py
    python scripts/test_stage2_revision.py \
        --book-draft exports/karakulina_book_draft_v2_....json \
        --fc-report  exports/karakulina_factcheck_report_....json
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
    print("[ERROR] pip install anthropic"); sys.exit(1)

from pipeline_utils import load_config, load_prompt

PROJECT_ID   = "karakulina_stage2_revision"
NARRATOR_NAME = "Татьяна Каракулина"

DEFAULT_BOOK_DRAFT = ROOT / "exports" / "karakulina_book_draft_v2_20260326_120522.json"
DEFAULT_FC_REPORT  = ROOT / "exports" / "karakulina_factcheck_report_20260326_121520.json"
DEFAULT_FACT_MAP   = ROOT / "exports" / "test_fact_map_karakulina_v5.json"
DEFAULT_TRANSCRIPT = ROOT / "exports" / "transcripts" / "karakulina_valentina_interview_assemblyai.txt"

# ID ошибок для ПРОПУСКА (исторические вставки — оставляем как есть)
SKIP_ERROR_TYPES = set()   # можно добавить типы
SKIP_ERROR_IDS   = set()   # можно добавить конкретные id


def normalize_book_draft(raw: dict) -> dict:
    if "book_draft" in raw:
        return raw["book_draft"]
    return raw


def count_text(book_draft: dict) -> int:
    chapters = book_draft.get("chapters", [])
    total = 0
    for ch in chapters:
        paras = ch.get("paragraphs", [])
        total += sum(len(p.get("text","")) for p in paras) if paras else len(ch.get("content",""))
    return total


def validate_book_draft(raw: dict, min_chars: int = 3000) -> dict | None:
    bd = normalize_book_draft(raw)
    chapters = bd.get("chapters", [])
    if len(chapters) < 3:
        print(f"[VALIDATE] ❌ Мало глав: {len(chapters)}")
        return None
    total = count_text(bd)
    if total < min_chars:
        print(f"[VALIDATE] ❌ Короткий текст: {total} симв.")
        return None
    return bd


def print_book_stats(label: str, bd: dict):
    chapters = bd.get("chapters", [])
    total = count_text(bd)
    print(f"\n{'='*60}")
    print(f"{label}")
    print(f"{'='*60}")
    print(f"  Глав: {len(chapters)} | Символов: {total} | Слов ~{total//5}")
    for ch in chapters:
        paras = ch.get("paragraphs", [])
        ch_ch = sum(len(p.get("text","")) for p in paras) if paras else len(ch.get("content",""))
        print(f"  [{ch.get('id','?')}] {ch.get('title','?')} — {ch_ch} симв.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--book-draft", default=str(DEFAULT_BOOK_DRAFT))
    parser.add_argument("--fc-report",  default=str(DEFAULT_FC_REPORT))
    parser.add_argument("--fact-map",   default=str(DEFAULT_FACT_MAP))
    parser.add_argument("--transcript", default=str(DEFAULT_TRANSCRIPT))
    # Ошибки для пропуска через запятую, например: --skip-errors err_005,err_006
    parser.add_argument("--skip-errors", default="", help="ID ошибок через запятую (не исправлять)")
    args = parser.parse_args()

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("[ERROR] ANTHROPIC_API_KEY не задан"); sys.exit(1)

    for p in (Path(args.book_draft), Path(args.fc_report), Path(args.fact_map), Path(args.transcript)):
        if not p.exists():
            print(f"[ERROR] Файл не найден: {p}"); sys.exit(1)

    book_draft_raw = json.loads(Path(args.book_draft).read_text(encoding="utf-8"))
    fc_report      = json.loads(Path(args.fc_report).read_text(encoding="utf-8"))
    fact_map       = json.loads(Path(args.fact_map).read_text(encoding="utf-8"))
    transcript     = Path(args.transcript).read_text(encoding="utf-8")

    book_draft = validate_book_draft(book_draft_raw)
    if not book_draft:
        print("[ERROR] Невалидный book_draft"); sys.exit(1)

    # Фильтруем ошибки
    skip_ids = set(x.strip() for x in args.skip_errors.split(",") if x.strip())
    skip_ids |= SKIP_ERROR_IDS

    all_errors = fc_report.get("errors", [])
    active_errors = [
        e for e in all_errors
        if e.get("id") not in skip_ids
        and e.get("type") not in SKIP_ERROR_TYPES
    ]
    skipped_errors = [e for e in all_errors if e not in active_errors]

    print(f"\n[START] Возврат A — Ghostwriter revision (итерация 2)")
    print(f"[INPUT] Ошибок в отчёте: {len(all_errors)} | "
          f"К исправлению: {len(active_errors)} | "
          f"Пропущено: {len(skipped_errors)}")

    if skipped_errors:
        print("[SKIP] Пропускаем (исторические вставки — оставляем):")
        for e in skipped_errors:
            print(f"  [{e.get('id','?')}] {e.get('type','?')} — "
                  f"{e.get('what_is_written','?')[:60]}...")

    print("\n[ERRORS] Исправляем:")
    for e in active_errors:
        sev_icon = {"critical":"🔴","major":"🟠","minor":"🟡"}.get(e.get("severity",""),"⚪")
        print(f"  {sev_icon} [{e.get('id','?')}] {e.get('type','?')} | "
              f"{e.get('what_is_written','?')[:60]}...")

    print_book_stats("ЧЕРНОВИК v2 (ВХОД)", book_draft)

    cfg    = load_config()
    gw_cfg = cfg["ghostwriter"]
    system_prompt = load_prompt(gw_cfg["prompt_file"])
    print(f"\n[CONFIG] Ghostwriter: {gw_cfg['model']} "
          f"temp={gw_cfg['temperature']} max_tokens={gw_cfg['max_tokens']}")

    # Собираем user_message для revision
    user_message = {
        "context": {
            "project_id": PROJECT_ID,
            "phase": "A",
            "call_type": "revision",
            "iteration": 2,
            "max_iterations": 3,
            "previous_agent": "fact_checker",
            "instruction": (
                "Фактчекер обнаружил ошибки в тексте. "
                "Исправь ТОЛЬКО указанные проблемы согласно fix_instruction. "
                "Не переписывай текст целиком — вноси точечные исправления. "
                "Исторические вставки (***жирный курсив***) НЕ трогай — они намеренные. "
                "Верни полную книгу со всеми главами."
            ),
        },
        "data": {
            "book_draft": book_draft,
            "fact_checker_report": {
                "verdict": "fail",
                "errors": active_errors,
                "warnings": fc_report.get("warnings", []),
            },
            "fact_map": fact_map,
            "transcripts": [{"speaker": NARRATOR_NAME, "text": transcript}],
        },
    }

    client = anthropic.Anthropic(api_key=api_key)
    out_dir = ROOT / "exports"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    print(f"\n[GHOSTWRITER] Запускаю revision (исправление {len(active_errors)} ошибок)...")
    start = datetime.now()

    raw_parts = []
    with client.messages.stream(
        model=gw_cfg["model"],
        max_tokens=gw_cfg["max_tokens"],
        temperature=gw_cfg.get("temperature", 0.6),
        system=system_prompt,
        messages=[{"role": "user", "content": json.dumps(user_message, ensure_ascii=False)}],
    ) as stream:
        for text in stream.text_stream:
            raw_parts.append(text)
        final = stream.get_final_message()

    elapsed = (datetime.now() - start).total_seconds()
    raw = "".join(raw_parts)
    in_tok, out_tok = final.usage.input_tokens, final.usage.output_tokens
    print(f"[GHOSTWRITER] Готово за {elapsed:.1f}с | {len(raw)} симв. | "
          f"токены: in={in_tok}, out={out_tok}")
    if out_tok >= gw_cfg["max_tokens"] - 10:
        print("[GHOSTWRITER] ⚠️  output_tokens ≈ max_tokens — возможно обрезание!")

    # Сохраняем сырой ответ
    raw_path = out_dir / f"karakulina_ghostwriter_v3_raw_{ts}.json"
    raw_path.write_text(json.dumps(json.loads(raw) if raw.strip().startswith("{") else {"raw": raw},
                                   ensure_ascii=False, indent=2)
                        if True else raw, encoding="utf-8")

    # Парсим JSON
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:])
        if text.endswith("```"):
            text = text[:-3].strip()
    s, e = text.find("{"), text.rfind("}")
    try:
        result_raw = json.loads(text[s:e+1]) if s != -1 and e > s else json.loads(text)
    except json.JSONDecodeError as ex:
        print(f"[ERROR] JSON parse failed: {ex}")
        raw_path = out_dir / f"karakulina_ghostwriter_v3_raw_{ts}.txt"
        raw_path.write_text(raw, encoding="utf-8")
        print(f"[SAVED] Сырой ответ: {raw_path}")
        sys.exit(1)

    raw_path.write_text(json.dumps(result_raw, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[SAVED] Сырой ответ v3: {raw_path}")

    book_draft_v3 = validate_book_draft(result_raw)
    if not book_draft_v3:
        print("[GHOSTWRITER] ❌ Валидация v3 не пройдена.")
        sys.exit(1)

    # Сохраняем нормализованный book_draft v3
    out_path = out_dir / f"karakulina_book_draft_v3_{ts}.json"
    out_path.write_text(
        json.dumps({"book_draft": book_draft_v3}, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"[SAVED] book_draft_v3: {out_path}")

    print_book_stats("ЧЕРНОВИК v3 (ПОСЛЕ ПРАВОК)", book_draft_v3)

    v2_chars = count_text(book_draft)
    v3_chars = count_text(book_draft_v3)
    delta = v3_chars - v2_chars
    print(f"\n  Δ текст: {v2_chars} → {v3_chars} ({delta:+d} симв.)")
    if v3_chars < v2_chars * 0.9:
        print("  ⚠️  Текст существенно короче — проверь потери!")
    else:
        print("  ✅ Объём сохранён")

    # Выводим полный текст для ревью
    print(f"\n{'='*60}")
    print("ПОЛНЫЙ ТЕКСТ v3 (ДЛЯ РЕВЬЮ)")
    print(f"{'='*60}")
    for ch in book_draft_v3.get("chapters", []):
        print(f"\n\n### [{ch.get('id')}] {ch.get('title','?').upper()}")
        paras = ch.get("paragraphs", [])
        if paras:
            for p in paras:
                print(p.get("text",""))
        else:
            print(ch.get("content",""))

    print(f"\n{'='*60}")
    print("ВОЗВРАТ A ЗАВЕРШЁН")
    print(f"{'='*60}")
    print(f"  Следующий шаг: запустить Фактчекер повторно")
    print(f"    python scripts/test_stage2_step3.py --book-draft {out_path}")


if __name__ == "__main__":
    main()
