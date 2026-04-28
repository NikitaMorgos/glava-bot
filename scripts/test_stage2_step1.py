#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stage 2 — Шаг 1: Ghostwriter (1-й проход) + Историк (параллельно)

Что делает:
  - Загружает fact_map из exports/
  - Запускает Ghostwriter (1-й проход) и Историка ОДНОВРЕМЕННО (asyncio.gather)
  - Сохраняет book_draft_v1 и historian_output
  - Выводит статистику для ревью

Следующий шаг — запустить test_stage2_step2.py (интеграция + Фактчекер).

Использование:
    python scripts/test_stage2_step1.py
    python scripts/test_stage2_step1.py --fact-map exports/test_fact_map_karakulina_v5.json
    python scripts/test_stage2_step1.py --transcript exports/transcripts/karakulina_valentina_interview_assemblyai.txt
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
# Параметры субъекта
# ──────────────────────────────────────────────────────────────────
PROJECT_ID = "karakulina_stage2_step1"
SUBJECT_NAME = "Каракулина Валентина Ивановна"
NARRATOR_NAME = "Татьяна Каракулина"
DEFAULT_FACT_MAP = ROOT / "exports" / "test_fact_map_karakulina_v5.json"
DEFAULT_TRANSCRIPT = ROOT / "exports" / "transcripts" / "karakulina_valentina_interview_assemblyai.txt"


# ──────────────────────────────────────────────────────────────────
# Валидация выходов
# ──────────────────────────────────────────────────────────────────

def validate_book_draft(agent_response: dict, min_chars: int = 3000) -> dict | None:
    """
    Проверяет структуру book_draft: ≥3 главы, ≥3000 символов.
    Поддерживает два формата:
      1. {"book_draft": {"chapters": [{"paragraphs": [{"text": "..."}]}]}}  (spec)
      2. {"chapters": [{"content": "..."}]}  (реальный вывод Ghostwriter)
    Возвращает нормализованный book_draft dict.
    """
    if not isinstance(agent_response, dict):
        return None

    # Формат 1: есть ключ book_draft
    raw = agent_response.get("book_draft")
    if raw and isinstance(raw, dict):
        chapters = raw.get("chapters", [])
    # Формат 2: главы на верхнем уровне
    elif "chapters" in agent_response:
        raw = agent_response
        chapters = agent_response.get("chapters", [])
    else:
        print(f"[VALIDATE] ❌ Нет ключей book_draft или chapters. Ключи: {list(agent_response.keys())[:6]}")
        return None

    if len(chapters) < 3:
        print(f"[VALIDATE] ❌ Мало глав: {len(chapters)} (нужно ≥3)")
        return None

    # Считаем текст из paragraphs[].text ИЛИ из content
    total = 0
    for ch in chapters:
        paras = ch.get("paragraphs", [])
        if paras:
            total += sum(len(p.get("text", "")) for p in paras)
        elif "content" in ch:
            total += len(ch["content"])

    if total < min_chars:
        print(f"[VALIDATE] ❌ Текст слишком короткий: {total} симв. (нужно ≥{min_chars})")
        return None

    return raw


def validate_historian_output(agent_response: dict) -> dict | None:
    """Проверяет структуру historical_context."""
    if not isinstance(agent_response, dict):
        return None
    hc = agent_response.get("historical_context")
    if not isinstance(hc, list) or len(hc) == 0:
        return None
    return agent_response


# ──────────────────────────────────────────────────────────────────
# Агенты
# ──────────────────────────────────────────────────────────────────

async def run_ghostwriter_async(client, fact_map: dict, transcript_text: str,
                                 cfg: dict) -> dict:
    """Ghostwriter — 1-й проход (initial). Возвращает сырой dict."""
    gw_cfg = cfg["ghostwriter"]
    system_prompt = load_prompt(gw_cfg["prompt_file"])

    user_message = {
        "context": {
            "project_id": PROJECT_ID,
            "phase": "A",
            "call_type": "initial",
            "iteration": 1,
            "max_iterations": 1,
            "previous_agent": "fact_extractor",
            "instruction": (
                "Создай полный черновик книги на основе карты фактов и протоколов интервью. "
                "Структура: 4 главы (справочный блок, автобиография, портрет, интересные факты). "
                "Приоритет — полнота фактов. "
                "Исторический контекст пока не добавляй — он будет интегрирован на следующем шаге."
            ),
        },
        "data": {
            "fact_map": fact_map,
            "transcripts": [{"speaker": NARRATOR_NAME, "text": transcript_text}],
            "photos_available": False,
        },
    }

    print(f"\n[GHOSTWRITER] Запускаю 1-й проход ({gw_cfg['model']}, max_tokens={gw_cfg['max_tokens']})...")
    start = datetime.now()

    loop = asyncio.get_event_loop()

    def _call():
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
        return "".join(raw_parts), final.usage.input_tokens, final.usage.output_tokens

    raw, in_tok, out_tok = await loop.run_in_executor(None, _call)
    elapsed = (datetime.now() - start).total_seconds()
    print(f"[GHOSTWRITER] Готово за {elapsed:.1f}с | {len(raw)} симв. | "
          f"токены: in={in_tok}, out={out_tok}")

    if out_tok >= gw_cfg["max_tokens"] - 10:
        print("[GHOSTWRITER] ⚠️  output_tokens ≈ max_tokens — возможно обрезание!")

    # Парсинг JSON
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:])
        if text.endswith("```"):
            text = text[:-3].strip()
    s, e = text.find("{"), text.rfind("}")
    if s != -1 and e > s:
        try:
            return json.loads(text[s:e + 1])
        except json.JSONDecodeError:
            pass
    return json.loads(text)


async def run_historian_async(client, fact_map: dict, cfg: dict) -> dict:
    """Историк. Возвращает сырой dict или {} при ошибке."""
    hist_cfg = cfg["historian"]
    system_prompt = load_prompt(hist_cfg["prompt_file"])

    subject = fact_map.get("subject", {})
    user_message = {
        "context": {
            "project_id": PROJECT_ID,
            "phase": "A",
            "call_type": "initial",
            "iteration": 1,
            "max_iterations": 1,
            "previous_agent": "fact_extractor",
            "instruction": (
                "Подготовь исторические и краеведческие справки для каждого значимого периода "
                "и места в жизни героя. Объём определяй сам. "
                "Подготовь готовые фрагменты для вставки и словарь реалий эпохи."
            ),
        },
        "data": {
            "subject": {
                "name": subject.get("name", SUBJECT_NAME),
                "birth_year": subject.get("birth_year"),
                "death_year": subject.get("death_year"),
                "birth_place": subject.get("birth_place", ""),
            },
            "timeline": fact_map.get("timeline", []),
            "locations": fact_map.get("locations", []),
            "persons": fact_map.get("persons", []),
        },
    }

    print(f"\n[HISTORIAN] Запускаю ({hist_cfg['model']}, max_tokens={hist_cfg['max_tokens']})...")
    start = datetime.now()

    loop = asyncio.get_event_loop()

    def _call():
        raw_parts = []
        # Историк 16000 токенов — используем streaming на всякий случай
        with client.messages.stream(
            model=hist_cfg["model"],
            max_tokens=hist_cfg["max_tokens"],
            temperature=hist_cfg.get("temperature", 0.3),
            system=system_prompt,
            messages=[{"role": "user", "content": json.dumps(user_message, ensure_ascii=False)}],
        ) as stream:
            for text in stream.text_stream:
                raw_parts.append(text)
            final = stream.get_final_message()
        return "".join(raw_parts), final.usage.input_tokens, final.usage.output_tokens

    try:
        raw, in_tok, out_tok = await loop.run_in_executor(None, _call)
        elapsed = (datetime.now() - start).total_seconds()
        print(f"[HISTORIAN] Готово за {elapsed:.1f}с | токены: in={in_tok}, out={out_tok}")

        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:])
            if text.endswith("```"):
                text = text[:-3].strip()
        s, e = text.find("{"), text.rfind("}")
        if s != -1 and e > s:
            return json.loads(text[s:e + 1])
        return json.loads(text)
    except Exception as ex:
        print(f"[HISTORIAN] ⚠️  Ошибка: {ex} — продолжаем без исторического контекста.")
        return {}


# ──────────────────────────────────────────────────────────────────
# Вывод результатов
# ──────────────────────────────────────────────────────────────────

def print_book_stats(book_draft: dict):
    chapters = book_draft.get("chapters", [])
    total_chars = 0
    for ch in chapters:
        paras = ch.get("paragraphs", [])
        if paras:
            total_chars += sum(len(p.get("text", "")) for p in paras)
        else:
            total_chars += len(ch.get("content", ""))
    total_words = total_chars // 5
    print(f"\n{'='*60}")
    print(f"ЧЕРНОВИК КНИГИ — СТАТИСТИКА")
    print(f"{'='*60}")
    print(f"  Глав: {len(chapters)} | Символов: {total_chars} | Слов ~{total_words}")
    print()
    for ch in chapters:
        paras = ch.get("paragraphs", [])
        if paras:
            ch_chars = sum(len(p.get("text", "")) for p in paras)
            n_para = len(paras)
        else:
            ch_chars = len(ch.get("content", ""))
            n_para = 1
        n_call = len(ch.get("callouts", []))
        print(f"  [{ch.get('id','?')}] {ch.get('title','?')}")
        print(f"       {n_para} блок(ов), {n_call} callout'ов, {ch_chars} символов")


def print_historian_stats(historian_output: dict):
    hc = historian_output.get("historical_context", [])
    gl = historian_output.get("era_glossary", [])
    print(f"\n{'='*60}")
    print(f"ИСТОРИК — СТАТИСТИКА")
    print(f"{'='*60}")
    print(f"  Периодов: {len(hc)} | Терминов в глоссарии: {len(gl)}")
    for ctx in hc:
        period = ctx.get("period", {})
        label = period.get("label", "?")
        n_ins = len(ctx.get("suggested_insertions", []))
        print(f"  [{period.get('start_year','?')}–{period.get('end_year','?')}] {label} — {n_ins} вставок")
    if gl:
        print(f"\n  Глоссарий: {', '.join(t.get('term','?') for t in gl[:5])}{'...' if len(gl)>5 else ''}")


# ──────────────────────────────────────────────────────────────────
# Главная точка входа
# ──────────────────────────────────────────────────────────────────

async def main_async(args):
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("[ERROR] ANTHROPIC_API_KEY не задан")
        sys.exit(1)

    fact_map_path = Path(args.fact_map)
    if not fact_map_path.exists():
        print(f"[ERROR] fact_map не найден: {fact_map_path}")
        sys.exit(1)
    fact_map = json.loads(fact_map_path.read_text(encoding="utf-8"))

    transcript_path = Path(args.transcript)
    if not transcript_path.exists():
        print(f"[ERROR] Транскрипт не найден: {transcript_path}")
        sys.exit(1)
    transcript_text = transcript_path.read_text(encoding="utf-8")

    cfg = load_config()
    print(f"\n[START] Stage 2 — Шаг 1: Ghostwriter + Историк (параллельно)")
    print(f"[START] fact_map: {fact_map_path.name} | "
          f"transcript: {transcript_path.name} ({len(transcript_text)} симв.)")
    print(f"[CONFIG] Ghostwriter: {cfg['ghostwriter']['model']} "
          f"temp={cfg['ghostwriter']['temperature']} "
          f"max_tokens={cfg['ghostwriter']['max_tokens']}")
    print(f"[CONFIG] Historian: {cfg['historian']['model']} "
          f"temp={cfg['historian']['temperature']} "
          f"max_tokens={cfg['historian']['max_tokens']}")

    client = anthropic.Anthropic(api_key=api_key)
    out_dir = ROOT / "exports"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    # ─── Параллельный запуск ───
    print(f"\n[PARALLEL] Запускаю Ghostwriter + Историка одновременно...")
    wall_start = datetime.now()

    ghostwriter_task = asyncio.create_task(
        run_ghostwriter_async(client, fact_map, transcript_text, cfg)
    )
    historian_task = asyncio.create_task(
        run_historian_async(client, fact_map, cfg)
    )

    gw_result_raw, hist_result_raw = await asyncio.gather(
        ghostwriter_task, historian_task,
        return_exceptions=True,
    )

    wall_elapsed = (datetime.now() - wall_start).total_seconds()
    print(f"\n[PARALLEL] Оба агента завершили работу за {wall_elapsed:.1f}с (параллельно)")

    # ─── Ghostwriter ───
    if isinstance(gw_result_raw, Exception):
        print(f"[GHOSTWRITER] ❌ ОШИБКА: {gw_result_raw}")
        sys.exit(1)

    book_draft = validate_book_draft(gw_result_raw)
    if not book_draft:
        print(f"[GHOSTWRITER] ❌ Валидация не пройдена. Сохраняем сырой ответ.")
        raw_path = out_dir / f"karakulina_ghostwriter_raw_{ts}.json"
        raw_path.write_text(json.dumps(gw_result_raw, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[SAVED] Сырой ответ: {raw_path}")
        sys.exit(1)

    gw_out_path = out_dir / f"karakulina_book_draft_v1_{ts}.json"
    gw_out_path.write_text(json.dumps({"book_draft": book_draft}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[SAVED] book_draft_v1: {gw_out_path}")
    print_book_stats(book_draft)

    # ─── Историк ───
    if isinstance(hist_result_raw, Exception):
        print(f"[HISTORIAN] ❌ ОШИБКА: {hist_result_raw} — продолжаем без контекста")
        historian_output = {}
    else:
        historian_output = validate_historian_output(hist_result_raw) or {}
        if not historian_output:
            print("[HISTORIAN] ⚠️  Валидация не пройдена — продолжаем без контекста")
        else:
            hist_out_path = out_dir / f"karakulina_historian_{ts}.json"
            hist_out_path.write_text(
                json.dumps(historian_output, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[SAVED] historian_output: {hist_out_path}")
            print_historian_stats(historian_output)

    # ─── Итог ───
    print(f"\n{'='*60}")
    print(f"ШАГ 1 ЗАВЕРШЁН")
    print(f"{'='*60}")
    ok_hist = bool(historian_output.get("historical_context"))
    print(f"  Ghostwriter: ✅ {len(book_draft.get('chapters',[]))} глав")
    print(f"  Историк:     {'✅' if ok_hist else '⚠️  нет контекста'}")
    print(f"  Следующий шаг: запустить test_stage2_step2.py --book-draft {gw_out_path}")
    if ok_hist:
        print(f"                  --historian {hist_out_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fact-map", default=str(DEFAULT_FACT_MAP))
    parser.add_argument("--transcript", default=str(DEFAULT_TRANSCRIPT))
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
