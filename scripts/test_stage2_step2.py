#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stage 2 — Шаг 2: Ghostwriter 2-й проход (интеграция контекста Историка)

Берёт готовый черновик из step 1 и добавляет исторические справки.
Инструкция: «дополняй, не переписывай».

Использование:
    python scripts/test_stage2_step2.py
    python scripts/test_stage2_step2.py \
        --book-draft exports/karakulina_book_draft_v1_....json \
        --historian exports/karakulina_historian_....json
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

PROJECT_ID = "karakulina_stage2_step2"
SUBJECT_NAME = "Каракулина Валентина Ивановна"
NARRATOR_NAME = "Татьяна Каракулина"

DEFAULT_BOOK_DRAFT = ROOT / "exports" / "karakulina_ghostwriter_raw_20260326_110530.json"
DEFAULT_HISTORIAN = ROOT / "exports" / "karakulina_historian_20260325_191405.json"
DEFAULT_FACT_MAP = ROOT / "exports" / "test_fact_map_karakulina_v5.json"
DEFAULT_TRANSCRIPT = ROOT / "exports" / "transcripts" / "karakulina_valentina_interview_assemblyai.txt"


def count_text(book_draft: dict) -> int:
    """Считает суммарный объём текста из paragraphs или content."""
    chapters = book_draft.get("chapters", [])
    total = 0
    for ch in chapters:
        paras = ch.get("paragraphs", [])
        if paras:
            total += sum(len(p.get("text", "")) for p in paras)
        else:
            total += len(ch.get("content", ""))
    return total


def normalize_book_draft(raw: dict) -> dict:
    """
    Нормализует выход Ghostwriter к единому виду с book_draft на верхнем уровне.
    Поддерживает:
      1. {"book_draft": {"chapters": [...]}}
      2. {"chapters": [...]}  (прямой вывод промпта)
    """
    if "book_draft" in raw:
        return raw["book_draft"]
    if "chapters" in raw:
        return raw
    return {}


def validate_book_draft(raw: dict, min_chars: int = 3000) -> dict | None:
    bd = normalize_book_draft(raw)
    chapters = bd.get("chapters", [])
    if len(chapters) < 3:
        print(f"[VALIDATE] ❌ Мало глав: {len(chapters)} (нужно ≥3)")
        return None
    total = count_text(bd)
    if total < min_chars:
        print(f"[VALIDATE] ❌ Короткий текст: {total} симв. (нужно ≥{min_chars})")
        return None
    return bd


def print_book_stats(label: str, book_draft: dict):
    chapters = book_draft.get("chapters", [])
    total = count_text(book_draft)
    print(f"\n{'='*60}")
    print(f"{label}")
    print(f"{'='*60}")
    print(f"  Глав: {len(chapters)} | Символов: {total} | Слов ~{total//5}")
    for ch in chapters:
        paras = ch.get("paragraphs", [])
        ch_chars = sum(len(p.get("text","")) for p in paras) if paras else len(ch.get("content",""))
        hn = len(ch.get("historical_notes", []))
        print(f"  [{ch.get('id','?')}] {ch.get('title','?')} — {ch_chars} симв."
              + (f" | {hn} ист. вставок" if hn else ""))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--book-draft", default=str(DEFAULT_BOOK_DRAFT))
    parser.add_argument("--historian", default=str(DEFAULT_HISTORIAN))
    parser.add_argument("--fact-map", default=str(DEFAULT_FACT_MAP))
    parser.add_argument("--transcript", default=str(DEFAULT_TRANSCRIPT))
    args = parser.parse_args()

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("[ERROR] ANTHROPIC_API_KEY не задан")
        sys.exit(1)

    # Загружаем входные данные
    draft_path = Path(args.book_draft)
    historian_path = Path(args.historian)
    fact_map_path = Path(args.fact_map)
    transcript_path = Path(args.transcript)

    for p in (draft_path, historian_path, fact_map_path, transcript_path):
        if not p.exists():
            print(f"[ERROR] Файл не найден: {p}")
            sys.exit(1)

    raw_draft = json.loads(draft_path.read_text(encoding="utf-8"))
    historian_output = json.loads(historian_path.read_text(encoding="utf-8"))
    fact_map = json.loads(fact_map_path.read_text(encoding="utf-8"))
    transcript_text = transcript_path.read_text(encoding="utf-8")

    book_draft_v1 = validate_book_draft(raw_draft)
    if not book_draft_v1:
        print(f"[ERROR] Невалидный book_draft из {draft_path}")
        sys.exit(1)

    print_book_stats("ЧЕРНОВИК v1 (ВХОД)", book_draft_v1)
    print(f"\n[HISTORIAN] Контекст: {Path(historian_path).name}")
    # Историк может быть в разных форматах — показываем что есть
    for k in list(historian_output.keys())[:4]:
        print(f"  {k}: {str(historian_output[k])[:80]}...")

    cfg = load_config()
    gw_cfg = cfg["ghostwriter"]

    print(f"\n[CONFIG] Ghostwriter: {gw_cfg['model']} "
          f"temp={gw_cfg['temperature']} max_tokens={gw_cfg['max_tokens']}")

    system_prompt = load_prompt(gw_cfg["prompt_file"])

    user_message = {
        "context": {
            "project_id": PROJECT_ID,
            "phase": "A",
            "call_type": "revision",
            "iteration": 2,
            "max_iterations": 2,
            "previous_agent": "historian",
            "instruction": (
                "Интегрируй исторический контекст в свой черновик. "
                "Используй справки от Историка-краеведа: ключевые исторические события, "
                "культурный и политический контекст, детали быта эпохи. "
                "Не все справки обязательно включать — выбери те, которые обогащают повествование. "
                "Исторические вставки оформляй как ***жирный курсив***. "
                "Не более 1–2 развёрнутых исторических отступлений на всю книгу. "
                "Не переписывай текст целиком — дополняй."
            ),
        },
        "data": {
            "book_draft": book_draft_v1,
            "historical_context": historian_output,
            "fact_map": fact_map,
            "transcripts": [{"speaker": NARRATOR_NAME, "text": transcript_text}],
        },
    }

    client = anthropic.Anthropic(api_key=api_key)
    out_dir = ROOT / "exports"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    print(f"\n[GHOSTWRITER] Запускаю 2-й проход (интеграция контекста)...")
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
    in_tok = final.usage.input_tokens
    out_tok = final.usage.output_tokens
    print(f"[GHOSTWRITER] Готово за {elapsed:.1f}с | {len(raw)} симв. | "
          f"токены: in={in_tok}, out={out_tok}")

    if out_tok >= gw_cfg["max_tokens"] - 10:
        print("[GHOSTWRITER] ⚠️  output_tokens ≈ max_tokens — возможно обрезание!")

    # Парсим
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
        raw_path = out_dir / f"karakulina_ghostwriter_v2_raw_{ts}.json"
        raw_path.write_text(raw, encoding="utf-8")
        print(f"[SAVED] Сырой ответ: {raw_path}")
        sys.exit(1)

    # Сохраняем сырой ответ
    raw_path = out_dir / f"karakulina_ghostwriter_v2_raw_{ts}.json"
    raw_path.write_text(json.dumps(result_raw, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[SAVED] Сырой ответ v2: {raw_path}")

    book_draft_v2 = validate_book_draft(result_raw)
    if not book_draft_v2:
        print("[GHOSTWRITER] ❌ Валидация v2 не пройдена. Изучи сырой ответ.")
        sys.exit(1)

    # Сохраняем нормализованный book_draft v2
    out_path = out_dir / f"karakulina_book_draft_v2_{ts}.json"
    out_path.write_text(
        json.dumps({"book_draft": book_draft_v2}, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"[SAVED] book_draft_v2: {out_path}")

    print_book_stats("ЧЕРНОВИК v2 (С ИСТОРИЧЕСКИМ КОНТЕКСТОМ)", book_draft_v2)

    # Сравниваем объём
    v1_chars = count_text(book_draft_v1)
    v2_chars = count_text(book_draft_v2)
    delta = v2_chars - v1_chars
    pct = (delta / v1_chars * 100) if v1_chars else 0
    print(f"\n  Δ текст: {v1_chars} → {v2_chars} ({delta:+d} симв., {pct:+.1f}%)")

    if v2_chars < v1_chars * 0.9:
        print("  ⚠️  Текст стал существенно короче — проверь, не потерян ли контент!")
    else:
        print("  ✅ Объём текста сохранён / увеличен")

    # Выводим главы с историческими вставками
    print(f"\n{'='*60}")
    print("ПОЛНЫЙ ТЕКСТ КНИГИ v2 (ДЛЯ РЕВЬЮ)")
    print(f"{'='*60}")
    chapters = book_draft_v2.get("chapters", [])
    for ch in chapters:
        print(f"\n\n### [{ch.get('id')}] {ch.get('title','?').upper()}")
        paras = ch.get("paragraphs", [])
        if paras:
            for p in paras:
                print(p.get("text", ""))
        else:
            print(ch.get("content", ""))
        hn = ch.get("historical_notes", [])
        if hn:
            print(f"\n  [ИСТОРИЧЕСКИЕ ВСТАВКИ: {len(hn)}]")
            for n in hn:
                print(f"  → {n.get('text', '')[:100]}...")

    print(f"\n{'='*60}")
    print(f"ШАГ 2 ЗАВЕРШЁН")
    print(f"{'='*60}")
    print(f"  Следующий шаг: запустить test_stage2_step3.py --book-draft {out_path}")


if __name__ == "__main__":
    main()
