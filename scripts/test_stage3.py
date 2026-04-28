#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stage 3 — Литредактор + Корректор

Что делает:
  - Загружает book_draft (после Фактчекера) и warnings
  - Запускает Литредактора (v3): стиль, голос, ритм, антиклише, выноски
  - Запускает Корректора (v1): орфография, пунктуация, типографика, паспорт стиля
  - Сохраняет промежуточный и финальный текст, логи правок

Использование:
    python scripts/test_stage3.py
    python scripts/test_stage3.py --book-draft exports/karakulina_book_FINAL_20260327_173733.json
    python scripts/test_stage3.py --book-draft ... --fc-warnings exports/karakulina_fc_report_iter2_*.json
    python scripts/test_stage3.py --prefix korolkova --book-draft exports/korolkova_book_FINAL_*.json
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

from pipeline_utils import load_config, load_prompt, save_run_manifest, run_proofreader_per_chapter
from pipeline_quality_gates import (
    run_stage3_text_gates, run_stage3_text_gates_variant_b,
    save_gate_report, summarize_failed_gates,
)
from checkpoint_utils import load_checkpoint

# ──────────────────────────────────────────────────────────────────
PROJECT_ID = "karakulina_stage3"
SUBJECT_NAME = "Каракулина Валентина Ивановна"

DEFAULT_BOOK_DRAFT = ROOT / "exports" / "karakulina_book_FINAL_20260327_173733.json"
DEFAULT_FC_WARNINGS = ROOT / "exports" / "karakulina_fc_report_iter2_20260327_173733.json"
DEFAULT_PREFIX = "karakulina"
CHECKPOINT_PROJECT = "karakulina"
CHECKPOINT_STAGE_FACT_MAP = "fact_map"


def parse_agent_json(raw_text: str) -> dict:
    """
    Устойчивый парсинг JSON из LLM-ответа:
      1) чистый json
      2) json внутри ```...```
      3) самый длинный валидный {...} фрагмент
    """
    text = (raw_text or "").strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:])
        if text.endswith("```"):
            text = text[:-3].strip()

    # 1) direct
    try:
        return json.loads(text)
    except Exception:
        pass

    # 2) broad slice first/last braces
    s, e = text.find("{"), text.rfind("}")
    if s != -1 and e > s:
        candidate = text[s : e + 1]
        try:
            return json.loads(candidate)
        except Exception:
            pass

    # 3) incremental shrink from right brace
    if s != -1:
        for right in range(text.rfind("}"), s, -1):
            if text[right] != "}":
                continue
            candidate = text[s : right + 1]
            try:
                return json.loads(candidate)
            except Exception:
                continue

    raise json.JSONDecodeError("Unable to parse JSON from LLM response", text, 0)


# ──────────────────────────────────────────────────────────────────
# Нормализация структуры черновика
# ──────────────────────────────────────────────────────────────────

def normalize_book_draft(raw: dict) -> dict:
    """Извлекает главы из book_draft или корневого уровня."""
    if "book_draft" in raw:
        bd = raw["book_draft"]
    else:
        bd = raw
    return {
        "chapters": bd.get("chapters", []),
        "callouts": bd.get("callouts", []),
        "historical_notes": bd.get("historical_notes", []),
    }


def count_chars(book_draft: dict) -> int:
    return sum(len(ch.get("content") or "") for ch in book_draft.get("chapters", []))


def extract_warnings(fc_report: dict) -> list:
    """Извлекает warnings из отчёта Фактчекера."""
    warnings = fc_report.get("warnings", [])
    return [
        {
            "id": w.get("id", ""),
            "type": w.get("type", ""),
            "chapter_id": w.get("chapter_id", ""),
            "description": w.get("description", ""),
        }
        for w in warnings
    ]


def ensure_ch01_bio_content(book_final: dict, fact_map: dict) -> tuple[dict, bool]:
    """
    Гарантирует, что ch_01 содержит минимальный биографический текст.
    Нужен для strict-gates, когда входной формат хранит биоданные вне chapter.content.
    """
    chapters = book_final.get("chapters", [])
    for ch in chapters:
        if ch.get("id") != "ch_01":
            continue
        if (ch.get("content") or "").strip():
            return book_final, False

        subj = fact_map.get("subject", {}) or {}
        lines: list[str] = []
        name = subj.get("name")
        birth_date = subj.get("birth_date") or subj.get("birth_year")
        birth_place = subj.get("birth_place")
        death_date = subj.get("death_date") or subj.get("death_year")
        father = subj.get("father")
        mother = subj.get("mother")

        if name:
            lines.append(f"{name}.")
        if birth_date or birth_place:
            if birth_date and birth_place:
                lines.append(f"Родилась {birth_date} в {birth_place}.")
            elif birth_date:
                lines.append(f"Родилась {birth_date}.")
            else:
                lines.append(f"Место рождения: {birth_place}.")
        if father or mother:
            parent_bits = []
            if father:
                parent_bits.append(f"Отец: {father}")
            if mother:
                parent_bits.append(f"Мать: {mother}")
            lines.append(". ".join(parent_bits) + ".")
        if death_date:
            lines.append(f"Умерла в {death_date}.")

        if not lines:
            # fallback, чтобы не потерять главу полностью
            lines = ["Основные биографические данные сохранены в фактах интервью."]

        ch["content"] = "\n".join(lines)
        ch["is_modified"] = True
        return book_final, True

    return book_final, False


# ──────────────────────────────────────────────────────────────────
# Валидация выхода Литредактора
# ──────────────────────────────────────────────────────────────────

def validate_literary_editor_output(agent_response: dict, input_chapters: list) -> dict | None:
    if not isinstance(agent_response, dict):
        return None

    chapters = agent_response.get("chapters", [])
    if not chapters:
        print(f"[VALIDATE] ❌ Нет глав в ответе Литредактора")
        return None

    input_ids = {ch.get("id") for ch in input_chapters}
    output_ids = {ch.get("id") for ch in chapters}
    missing = input_ids - output_ids
    if missing:
        print(f"[VALIDATE] ❌ Отсутствуют главы: {missing}")
        return None

    edits_log = agent_response.get("edits_log", [])
    if not edits_log:
        print("[VALIDATE] ⚠️  edits_log пуст — Литредактор ничего не изменил")

    verdict = agent_response.get("verdict", "")
    if verdict not in ("pass", "return_to_writer"):
        print(f"[VALIDATE] ❌ Неизвестный verdict: {verdict!r}")
        return None

    return agent_response


# ──────────────────────────────────────────────────────────────────
# Агент
# ──────────────────────────────────────────────────────────────────

async def run_literary_editor_async(
    client, book_draft: dict, fc_warnings: list, cfg: dict
) -> dict:
    le_cfg = cfg["literary_editor"]
    system_prompt = load_prompt(le_cfg["prompt_file"])

    user_message = {
        "phase": "A",
        "project_id": PROJECT_ID,
        "iteration": 1,
        "max_iterations": 2,
        "book_draft": book_draft,
        "fact_checker_warnings": fc_warnings,
    }

    print(f"\n[LITEDITOR] Запускаю ({le_cfg['model']}, "
          f"max_tokens={le_cfg['max_tokens']}, temp={le_cfg.get('temperature', 0.4)})...")
    print(f"[LITEDITOR] Глав: {len(book_draft.get('chapters', []))} | "
          f"Символов: {count_chars(book_draft)} | "
          f"Warnings: {len(fc_warnings)}")
    start = datetime.now()

    loop = asyncio.get_event_loop()

    def _call():
        raw_parts = []
        with client.messages.stream(
            model=le_cfg["model"],
            max_tokens=le_cfg["max_tokens"],
            temperature=le_cfg.get("temperature", 0.4),
            system=system_prompt,
            messages=[{"role": "user", "content": json.dumps(user_message, ensure_ascii=False)}],
        ) as stream:
            for text in stream.text_stream:
                raw_parts.append(text)
            final = stream.get_final_message()
        return "".join(raw_parts), final.usage.input_tokens, final.usage.output_tokens

    raw, in_tok, out_tok = await loop.run_in_executor(None, _call)
    elapsed = (datetime.now() - start).total_seconds()
    print(f"[LITEDITOR] Готово за {elapsed:.1f}с | {len(raw)} симв. | "
          f"токены: in={in_tok}, out={out_tok}")

    if out_tok >= le_cfg["max_tokens"] - 100:
        print("[LITEDITOR] ⚠️  output_tokens ≈ max_tokens — возможно обрезание!")

    # Парсинг JSON (устойчивый)
    try:
        return parse_agent_json(raw)
    except json.JSONDecodeError as exc:
        print(f"[LITEDITOR] ❌ JSON parse error: {exc}")
        raise


# ──────────────────────────────────────────────────────────────────
# Корректор
# ──────────────────────────────────────────────────────────────────

def validate_proofreader_output(agent_response: dict, input_chapters: list) -> dict | None:
    if not isinstance(agent_response, dict):
        return None
    chapters = agent_response.get("chapters", [])
    if not chapters:
        print("[VALIDATE-PR] ❌ Нет глав в ответе Корректора")
        return None
    input_ids = {ch.get("id") for ch in input_chapters}
    output_ids = {ch.get("id") for ch in chapters}
    if input_ids - output_ids:
        print(f"[VALIDATE-PR] ❌ Отсутствуют главы: {input_ids - output_ids}")
        return None
    if not agent_response.get("style_passport"):
        print("[VALIDATE-PR] ⚠️  style_passport пуст")
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

    try:
        return parse_agent_json(raw)
    except json.JSONDecodeError as exc:
        print(f"[PROOFREADER] ❌ JSON parse error: {exc}")
        raise


def print_proofreader_results(result: dict, chars_before: int):
    print("\n" + "=" * 60)
    print("РЕЗУЛЬТАТ ЭТАПА 3 — КОРРЕКТОР")
    print("=" * 60)

    summary = result.get("summary", {})
    chapters = result.get("chapters", [])
    chars_after = sum(len(ch.get("content") or "") for ch in chapters)
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

    notes = summary.get("notes")
    if notes:
        print(f"\n  Примечания: {notes[:200]}")

    print("=" * 60)


# ──────────────────────────────────────────────────────────────────
# Печать результатов Литредактора
# ──────────────────────────────────────────────────────────────────

def print_results(result: dict, chars_before: int):
    print("\n" + "=" * 60)
    print("РЕЗУЛЬТАТ ЭТАПА 3 — ЛИТРЕДАКТОР")
    print("=" * 60)

    verdict = result.get("verdict", "?")
    verdict_sym = "✅ PASS" if verdict == "pass" else "🔄 RETURN_TO_WRITER"
    print(f"\n  Verdict: {verdict_sym}")

    # Статистика правок
    edits = result.get("edits_log", [])
    chapters = result.get("chapters", [])
    chars_after = sum(len(ch.get("content") or "") for ch in chapters)
    modified = [ch for ch in chapters if ch.get("is_modified")]

    print(f"\n  Глав отредактировано: {len(modified)}/{len(chapters)}")
    print(f"  Правок в лог: {len(edits)}")
    print(f"  Символов: {chars_before} → {chars_after} (Δ{chars_after - chars_before:+})")

    # Стилевая оценка
    sa = result.get("style_assessment", {})
    if sa:
        print(f"\n  Стиль:")
        print(f"    Единство голоса: {sa.get('voice_consistency', '?')}")
        print(f"    Тон: {sa.get('tone', '?')}")
        print(f"    AI-артефактов: {sa.get('ai_artifacts_found', '?')}")
        print(f"    Читаемость: {sa.get('readability', '?')}")
        comment = sa.get("overall_comment", "")
        if comment:
            print(f"    Комментарий: {comment[:180]}...")

    # Типы правок
    if edits:
        from collections import Counter
        edit_types = Counter(e.get("type", "?") for e in edits)
        print("\n  Типы правок:")
        for t, cnt in edit_types.most_common():
            print(f"    {cnt}× {t}")

    # Callouts
    callouts = result.get("callouts", [])
    if callouts:
        statuses = {}
        for c in callouts:
            s = c.get("status", "kept")
            statuses[s] = statuses.get(s, 0) + 1
        print(f"\n  Callouts ({len(callouts)}): {statuses}")

    # return_to_writer
    rtw = result.get("return_to_writer_reasons", [])
    if rtw:
        print("\n  Причины возврата Писателю:")
        for r in rtw:
            print(f"    [{r.get('chapter_id')}] {r.get('issue', '')}")

    print("=" * 60)


# ──────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--book-draft", default=str(DEFAULT_BOOK_DRAFT))
    parser.add_argument("--fc-warnings", default=str(DEFAULT_FC_WARNINGS),
                        help="Файл отчёта Фактчекера (для извлечения warnings)")
    parser.add_argument("--fact-map", default=None,
                        help="Путь к fact_map JSON (по умолчанию approved checkpoint)")
    parser.add_argument("--prefix", default=DEFAULT_PREFIX,
                        help="Префикс для имён выходных файлов (напр. korolkova)")
    parser.add_argument("--output-dir", default=str(ROOT / "exports"),
                        help="Папка для сохранения результатов (по умолчанию ROOT/exports/)")
    parser.add_argument("--no-strict-gates", action="store_true",
                        help="Отключить блокирующие Stage3 text-gates (не рекомендуется)")
    parser.add_argument("--variant-b", action="store_true",
                        help="Режим Вариант B: пропускает gate_required_entities в Stage3 gates")
    args = parser.parse_args()

    cfg = load_config()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Загрузка черновика
    draft_path = Path(args.book_draft)
    print(f"[INPUT] book_draft: {draft_path.name}")
    with open(draft_path, encoding="utf-8") as f:
        raw_draft = json.load(f)
    book_draft = normalize_book_draft(raw_draft)
    chars_before = count_chars(book_draft)
    print(f"[INPUT] Глав: {len(book_draft['chapters'])} | Символов: {chars_before}")

    # Загрузка warnings из отчёта ФК
    fc_warnings = []
    fc_path = Path(args.fc_warnings)
    if fc_path.exists():
        print(f"[INPUT] fc_report: {fc_path.name}")
        with open(fc_path, encoding="utf-8") as f:
            fc_report = json.load(f)
        fc_warnings = extract_warnings(fc_report)
        print(f"[INPUT] Warnings: {len(fc_warnings)}")
    else:
        print("[INPUT] fc_warnings: файл не найден, продолжаем без warnings")

    # fact_map для обязательных сущностей (strict gates)
    fact_map_source = None
    fact_checkpoint_meta = {}
    if args.fact_map:
        fact_map_path = Path(args.fact_map)
        if not fact_map_path.exists():
            print(f"[ERROR] fact_map не найден: {fact_map_path}")
            sys.exit(1)
        fact_map = json.loads(fact_map_path.read_text(encoding="utf-8"))
        fact_map_source = str(fact_map_path)
    else:
        cp_fact = load_checkpoint(CHECKPOINT_PROJECT, CHECKPOINT_STAGE_FACT_MAP, require_approved=True)
        fact_map = cp_fact.get("content", {})
        fact_map_source = f"checkpoint:{CHECKPOINT_PROJECT}/{CHECKPOINT_STAGE_FACT_MAP}@v{cp_fact.get('version')}"
        fact_checkpoint_meta = {
            "fact_map": {
                "project": CHECKPOINT_PROJECT,
                "stage": CHECKPOINT_STAGE_FACT_MAP,
                "version": cp_fact.get("version"),
                "approved_at": cp_fact.get("approved_at"),
                "source_file": cp_fact.get("source_file"),
            }
        }
    print(f"[INPUT] fact_map source: {fact_map_source}")

    le_cfg = cfg["literary_editor"]
    pr_cfg = cfg.get("proofreader", {})
    print(f"[PROMPT] Литредактор: {le_cfg['prompt_file']} "
          f"({len(open(ROOT / 'prompts' / le_cfg['prompt_file'], encoding='utf-8').read())} симв.)")
    print(f"[CONFIG] Литредактор: {le_cfg['model']} "
          f"temp={le_cfg.get('temperature', 0.5)} max_tokens={le_cfg['max_tokens']}")
    if pr_cfg:
        print(f"[PROMPT] Корректор: {pr_cfg['prompt_file']} "
              f"({len(open(ROOT / 'prompts' / pr_cfg['prompt_file'], encoding='utf-8').read())} симв.)")
        print(f"[CONFIG] Корректор: {pr_cfg['model']} "
              f"temp={pr_cfg.get('temperature', 0.0)} max_tokens={pr_cfg['max_tokens']}")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("[ERROR] ANTHROPIC_API_KEY не задан")
        sys.exit(1)
    client = anthropic.Anthropic(api_key=api_key)

    # ══ ШАГ 1: Литредактор ══
    print("\n" + "─" * 60)
    print("ШАГ 1: ЛИТРЕДАКТОР")
    print("─" * 60)
    raw_result = await run_literary_editor_async(client, book_draft, fc_warnings, cfg)

    # Валидация
    result = validate_literary_editor_output(raw_result, book_draft["chapters"])
    if result is None:
        raw_path = out_dir / f"{args.prefix}_liteditor_raw_{ts}.json"
        with open(raw_path, "w", encoding="utf-8") as f:
            json.dump(raw_result, f, ensure_ascii=False, indent=2)
        print(f"[SAVED] Сырой ответ: {raw_path}")
        sys.exit(1)

    # Сохранение промежуточного результата
    book_after_le = {
        "chapters": result["chapters"],
        "callouts": result.get("callouts", []),
        "historical_notes": result.get("historical_notes", []),
    }
    book_le_path = out_dir / f"{args.prefix}_book_stage3_liteditor_{ts}.json"
    with open(book_le_path, "w", encoding="utf-8") as f:
        json.dump({"book_draft": book_after_le}, f, ensure_ascii=False, indent=2)
    print(f"[SAVED] book после Литредактора: {book_le_path.name}")

    report_path = out_dir / f"{args.prefix}_liteditor_report_{ts}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"[SAVED] liteditor_report: {report_path.name}")

    print_results(result, chars_before)

    verdict = result.get("verdict", "")
    if verdict == "return_to_writer":
        print("\n🔄 Литредактор вернул тексту Писателю:")
        for r in result.get("return_to_writer_reasons", []):
            print(f"  [{r.get('chapter_id')}] {r.get('issue', '')}")

    # ══ ШАГ 2: Корректор ══
    if not pr_cfg:
        print("\n[SKIP] proofreader не настроен в config — пропускаем")
        print(f"\n{'=' * 60}")
        print("  ✅ Этап 3 (только Литредактор) ЗАВЕРШЁН")
        print(f"  Книга: {book_le_path.name}")
        print("=" * 60)
        stage3_partial_report = run_stage3_text_gates_variant_b(book_after_le, fact_map) if args.variant_b else run_stage3_text_gates(book_after_le, fact_map)
        stage3_partial_path = out_dir / f"{args.prefix}_stage3_text_gates_{ts}.json"
        save_gate_report(stage3_partial_path, stage3_partial_report)
        print(f"[SAVED] Stage3 text gates: {stage3_partial_path.name}")
        if summarize_failed_gates(stage3_partial_report) and not args.no_strict_gates:
            print("\n❌ [STRICT_GATES] Stage3 (partial) не пройден.")
            sys.exit(2)
        return

    print("\n" + "─" * 60)
    print("ШАГ 2: КОРРЕКТОР (по главам)")
    print("─" * 60)

    chars_after_le = count_chars(book_after_le)
    PROOFREADER_CHUNK_THRESHOLD = 10_000
    use_per_chapter = chars_after_le > PROOFREADER_CHUNK_THRESHOLD
    if use_per_chapter:
        print(f"[PROOFREADER] Объём {chars_after_le} симв. > {PROOFREADER_CHUNK_THRESHOLD} → режим по главам")
    else:
        print(f"[PROOFREADER] Объём {chars_after_le} симв. → стандартный режим")

    try:
        if use_per_chapter:
            loop = asyncio.get_event_loop()
            raw_pr = await loop.run_in_executor(
                None, run_proofreader_per_chapter, client, book_after_le, PROJECT_ID, cfg
            )
        else:
            raw_pr = await run_proofreader_async(client, book_after_le, cfg)
    except Exception as exc:
        print(f"[WARN] Корректор вернул невалидный JSON: {exc}")
        raw_pr = {"_parse_error": str(exc)}

    pr_result = validate_proofreader_output(raw_pr, book_after_le["chapters"])
    if pr_result is None:
        raw_pr_path = out_dir / f"{args.prefix}_proofreader_raw_{ts}.json"
        with open(raw_pr_path, "w", encoding="utf-8") as f:
            json.dump(raw_pr, f, ensure_ascii=False, indent=2)
        print(f"[SAVED] Сырой ответ Корректора: {raw_pr_path.name}")
        print("[WARN] Корректор не прошёл валидацию — используем текст после Литредактора")
        pr_result = {
            "chapters": book_after_le["chapters"],
            "callouts": book_after_le.get("callouts", []),
            "historical_notes": book_after_le.get("historical_notes", []),
            "style_passport": {},
            "summary": {"total_corrections": 0, "clean_text_ready": False, "notes": "Proofreader validation failed"},
        }

    # Сохраняем финальный JSON
    book_final = {
        "chapters": pr_result["chapters"],
        "callouts": pr_result.get("callouts", book_after_le.get("callouts", [])),
        "historical_notes": pr_result.get("historical_notes", book_after_le.get("historical_notes", [])),
    }
    # Сохраняем bio_data из book_draft — LitEditor/Proofreader его не трогают
    draft_bio_map = {ch.get("id"): ch.get("bio_data") for ch in book_draft.get("chapters", []) if ch.get("bio_data")}
    if draft_bio_map:
        for ch in book_final["chapters"]:
            ch_id = ch.get("id")
            if ch_id in draft_bio_map and not ch.get("bio_data"):
                ch["bio_data"] = draft_bio_map[ch_id]
    book_final, ch01_filled = ensure_ch01_bio_content(book_final, fact_map)
    if ch01_filled:
        print("[PATCH] ch_01 была пустой — добавлен минимальный биографический блок из fact_map")
        pr_result["chapters"] = book_final["chapters"]
    final_path = out_dir / f"{args.prefix}_book_FINAL_stage3_{ts}.json"
    with open(final_path, "w", encoding="utf-8") as f:
        json.dump({"book_final": book_final}, f, ensure_ascii=False, indent=2)
    print(f"[SAVED] book_FINAL_stage3: {final_path.name}")

    # Паспорт стиля и отчёт Корректора
    pr_report_path = out_dir / f"{args.prefix}_proofreader_report_{ts}.json"
    with open(pr_report_path, "w", encoding="utf-8") as f:
        json.dump(pr_result, f, ensure_ascii=False, indent=2)
    print(f"[SAVED] proofreader_report: {pr_report_path.name}")

    # TXT финала
    txt_lines = []
    for ch in book_final["chapters"]:
        txt_lines.append("=" * 60)
        txt_lines.append(f"{ch.get('id', '')} | {ch.get('title', '')}")
        txt_lines.append("=" * 60)
        txt_lines.append(ch.get("content") or "")
        txt_lines.append("")
    txt_text = "\n".join(txt_lines)
    txt_path = out_dir / f"{args.prefix}_FINAL_stage3_{ts}.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(txt_text)
    print(f"[SAVED] FINAL TXT: {txt_path.name}")

    print_proofreader_results(pr_result, chars_after_le)

    print(f"\n{'=' * 60}")
    print("  ✅ Этап 3 (Литредактор + Корректор) ЗАВЕРШЁН")
    print(f"  Финальный файл: {txt_path.name}")
    print(f"  Готово к вёрстке: {pr_result.get('summary', {}).get('clean_text_ready', '?')}")
    print("=" * 60)

    stage3_report = run_stage3_text_gates_variant_b(book_final, fact_map) if args.variant_b else run_stage3_text_gates(book_final, fact_map)
    stage3_gate_path = out_dir / f"{args.prefix}_stage3_text_gates_{ts}.json"
    save_gate_report(stage3_gate_path, stage3_report)
    print(f"[SAVED] Stage3 text gates: {stage3_gate_path.name}")
    gate_failed = bool(summarize_failed_gates(stage3_report))

    save_run_manifest(
        output_dir=out_dir,
        prefix=args.prefix,
        stage="stage3",
        project_id=PROJECT_ID,
        cfg=cfg,
        ts=ts,
        inputs={
            "book_draft_path": str(draft_path),
            "fc_report_path": str(fc_path),
            "fact_map_source": fact_map_source,
            "warnings_count": len(fc_warnings),
        },
        outputs={
            "liteditor_report_path": str(report_path),
            "book_after_liteditor": str(book_le_path),
            "proofreader_report_path": str(pr_report_path),
            "book_final_stage3_path": str(final_path),
            "final_txt_path": str(txt_path),
            "ready_for_layout": pr_result.get("summary", {}).get("clean_text_ready"),
            "text_gates_path": str(stage3_gate_path),
            "text_gates_passed": stage3_report.get("passed"),
        },
        notes={"strict_gates_enabled": not args.no_strict_gates, "variant_b": args.variant_b},
        checkpoints=fact_checkpoint_meta,
    )

    if gate_failed and not args.no_strict_gates:
        print("\n❌ [STRICT_GATES] Stage3 не пройден: обнаружены критические проблемы текста.")
        if args.variant_b:
            print("   (Режим --variant-b: gate_required_entities пропущен)")
        print("   См. отчёт:", stage3_gate_path.name)
        sys.exit(2)


if __name__ == "__main__":
    asyncio.run(main())
