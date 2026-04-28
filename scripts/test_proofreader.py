#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Корректор (Proofreader) — отдельный запуск.

Использование:
    python scripts/test_proofreader.py
    python scripts/test_proofreader.py --book-text exports/karakulina_book_stage3_liteditor_*.json
    python scripts/test_proofreader.py --book-text ... --prefix korolkova
"""
import argparse
import asyncio
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

# ──────────────────────────────────────────────────────────────────
PROJECT_ID = "karakulina_stage3"
DEFAULT_BOOK_TEXT = ROOT / "exports" / "karakulina_book_stage3_liteditor_20260329_063025.json"
DEFAULT_PREFIX = "karakulina"


def normalize_book_text(raw: dict) -> dict:
    """Извлекает главы из book_draft / book_text / корневого уровня."""
    for key in ("book_text", "book_draft", "book_final"):
        if key in raw:
            bd = raw[key]
            break
    else:
        bd = raw
    return {
        "chapters": bd.get("chapters", []),
        "callouts": bd.get("callouts", []),
        "historical_notes": bd.get("historical_notes", []),
    }


def count_chars(book: dict) -> int:
    return sum(len(ch.get("content", "")) for ch in book.get("chapters", []))


def validate_proofreader_output(agent_response: dict, input_chapters: list) -> dict | None:
    if not isinstance(agent_response, dict):
        return None
    chapters = agent_response.get("chapters", [])
    if not chapters:
        print("[VALIDATE] ❌ Нет глав в ответе Корректора")
        return None
    input_ids = {ch.get("id") for ch in input_chapters}
    output_ids = {ch.get("id") for ch in chapters}
    missing = input_ids - output_ids
    if missing:
        print(f"[VALIDATE] ❌ Отсутствуют главы: {missing}")
        return None
    if not agent_response.get("style_passport"):
        print("[VALIDATE] ⚠️  style_passport пуст")
    return agent_response


async def run_proofreader_async(client, book_text: dict, cfg: dict) -> dict:
    pr_cfg = cfg["proofreader"]
    system_prompt = load_prompt(pr_cfg["prompt_file"])

    user_message = {
        "phase": "A",
        "project_id": PROJECT_ID,
        "book_text": book_text,
    }

    print(f"\n[PROOFREADER] Запускаю ({pr_cfg['model']}, "
          f"max_tokens={pr_cfg['max_tokens']}, temp={pr_cfg.get('temperature', 0.0)})...")
    print(f"[PROOFREADER] Глав: {len(book_text.get('chapters', []))} | "
          f"Символов: {count_chars(book_text)}")
    start = datetime.now()

    loop = asyncio.get_event_loop()

    def _call():
        raw_parts = []
        with client.messages.stream(
            model=pr_cfg["model"],
            max_tokens=pr_cfg["max_tokens"],
            temperature=pr_cfg.get("temperature", 0.0),
            system=system_prompt,
            messages=[{"role": "user", "content": json.dumps(user_message, ensure_ascii=False)}],
        ) as stream:
            for text in stream.text_stream:
                raw_parts.append(text)
            final = stream.get_final_message()
        return "".join(raw_parts), final.usage.input_tokens, final.usage.output_tokens

    raw, in_tok, out_tok = await loop.run_in_executor(None, _call)
    elapsed = (datetime.now() - start).total_seconds()
    print(f"[PROOFREADER] Готово за {elapsed:.1f}с | {len(raw)} симв. | "
          f"токены: in={in_tok}, out={out_tok}")

    if out_tok >= pr_cfg["max_tokens"] - 100:
        print("[PROOFREADER] ⚠️  output_tokens ≈ max_tokens — возможно обрезание!")

    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:])
        if text.endswith("```"):
            text = text[:-3].strip()
    s, e = text.find("{"), text.rfind("}")
    if s != -1 and e > s:
        candidate = text[s:e + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError as exc:
            print(f"[PROOFREADER] ❌ JSON parse error: {exc}")
            # Сохраняем сырой ответ для диагностики
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            raw_path = ROOT / "exports" / f"proofreader_raw_{ts}.txt"
            with open(raw_path, "w", encoding="utf-8") as _f:
                _f.write(candidate)
            print(f"[PROOFREADER] Сырой ответ сохранён: {raw_path.name}")
            # Попытка починить JSON через json_repair если доступен
            try:
                from json_repair import repair_json
                repaired = repair_json(candidate)
                parsed = json.loads(repaired)
                print("[PROOFREADER] ✅ JSON восстановлен через json_repair")
                return parsed
            except Exception:
                pass
            raise exc
    raise ValueError("No JSON object found in response")


def print_results(result: dict, chars_before: int):
    print("\n" + "=" * 60)
    print("РЕЗУЛЬТАТ КОРРЕКТОРА")
    print("=" * 60)

    summary = result.get("summary", {})
    chapters = result.get("chapters", [])
    chars_after = sum(len(ch.get("content", "")) for ch in chapters)
    corrections = result.get("corrections", [])
    modified = [ch for ch in chapters if ch.get("is_modified")]

    print(f"\n  Глав исправлено: {len(modified)}/{len(chapters)}")
    print(f"  Исправлений всего: {summary.get('total_corrections', len(corrections))}")
    print(f"  Символов: {chars_before} → {chars_after} (Δ{chars_after - chars_before:+})")
    print(f"  Готово к вёрстке: {summary.get('clean_text_ready', '?')}")

    by_type = summary.get("by_type", {})
    if by_type:
        print("\n  Типы исправлений:")
        for t, cnt in sorted(by_type.items(), key=lambda x: -x[1]):
            if cnt:
                print(f"    {cnt}× {t}")

    sp = result.get("style_passport", {})
    if sp:
        names = sp.get("person_names", [])
        print(f"\n  Паспорт стиля: {len(names)} имён зафиксировано")
        print(f"  Формат дат: {sp.get('date_format', '?')}")
        print(f"  Кавычки: {sp.get('quote_style', '?')}")

    notes = summary.get("notes")
    if notes:
        print(f"\n  Примечания: {notes[:300]}")

    print("=" * 60)


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--book-text", default=str(DEFAULT_BOOK_TEXT),
                        help="JSON после Литредактора")
    parser.add_argument("--prefix", default=DEFAULT_PREFIX)
    args = parser.parse_args()

    cfg = load_config()

    book_path = Path(args.book_text)
    print(f"[INPUT] book_text: {book_path.name}")
    with open(book_path, encoding="utf-8") as f:
        raw = json.load(f)
    book_text = normalize_book_text(raw)
    chars_before = count_chars(book_text)
    print(f"[INPUT] Глав: {len(book_text['chapters'])} | Символов: {chars_before}")

    pr_cfg = cfg["proofreader"]
    print(f"[PROMPT] Корректор: {pr_cfg['prompt_file']} "
          f"({len(open(ROOT / 'prompts' / pr_cfg['prompt_file'], encoding='utf-8').read())} симв.)")
    print(f"[CONFIG] {pr_cfg['model']} temp={pr_cfg.get('temperature', 0.0)} "
          f"max_tokens={pr_cfg['max_tokens']}")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("[ERROR] ANTHROPIC_API_KEY не задан")
        sys.exit(1)
    client = anthropic.Anthropic(api_key=api_key)

    raw_result = await run_proofreader_async(client, book_text, cfg)

    result = validate_proofreader_output(raw_result, book_text["chapters"])
    if result is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        raw_path = ROOT / "exports" / f"{args.prefix}_proofreader_raw_{ts}.json"
        with open(raw_path, "w", encoding="utf-8") as f:
            json.dump(raw_result, f, ensure_ascii=False, indent=2)
        print(f"[SAVED] Сырой ответ: {raw_path.name}")
        sys.exit(1)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Финальный JSON
    book_final = {
        "chapters": result["chapters"],
        "callouts": result.get("callouts", book_text.get("callouts", [])),
        "historical_notes": result.get("historical_notes", book_text.get("historical_notes", [])),
    }
    final_json_path = ROOT / "exports" / f"{args.prefix}_book_FINAL_stage3_{ts}.json"
    with open(final_json_path, "w", encoding="utf-8") as f:
        json.dump({"book_final": book_final}, f, ensure_ascii=False, indent=2)
    print(f"[SAVED] book_FINAL_stage3: {final_json_path.name}")

    # Отчёт Корректора
    report_path = ROOT / "exports" / f"{args.prefix}_proofreader_report_{ts}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"[SAVED] proofreader_report: {report_path.name}")

    # TXT
    txt_lines = []
    for ch in book_final["chapters"]:
        txt_lines.append("=" * 60)
        txt_lines.append(f"{ch.get('id', '')} | {ch.get('title', '')}")
        txt_lines.append("=" * 60)
        txt_lines.append(ch.get("content", ""))
        txt_lines.append("")
    txt_path = ROOT / "exports" / f"{args.prefix}_FINAL_stage3_{ts}.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(txt_lines))
    print(f"[SAVED] FINAL TXT: {txt_path.name}")

    print_results(result, chars_before)

    print(f"\n{'=' * 60}")
    print("  ✅ Корректор ЗАВЕРШЁН")
    print(f"  Финал: {txt_path.name}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
