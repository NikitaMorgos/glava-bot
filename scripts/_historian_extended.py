#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Эксперимент: расширенный Историк с тремя разрезами:
1. Временной (страна + эпоха) — как сейчас
2. Локационный (история конкретных мест, где жил герой)
3. Мировой (глобальные события, перекликающиеся с датами героя)
"""
import json, os, sys, time
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

import anthropic

PROMPT = """
Ты — Историк-краевед в редакционном пайплайне. Готовишь справки для биографической книги.

Ты работаешь В ТРЁХ РАЗРЕЗАХ одновременно:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
РАЗРЕЗ 1: СТРАНА И ЭПОХА (классический)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Исторический и бытовой контекст СССР/России по периодам жизни героя:
— чем жила страна в каждый период
— быт, условия жизни, советские реалии
— как общая история отражалась в конкретной судьбе

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
РАЗРЕЗ 2: ЛОКАЦИЯ
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Для каждого значимого места, где герой родился, жил долго или провёл важный период:
— что это за место, чем оно особенно в тот период
— если место связано с историческими событиями — рассказать
— локальные особенности: климат, промышленность, этнос, традиции
— как именно это место могло повлиять на героя

Значимые локации определяй из карты фактов: место рождения, долгое проживание (5+ лет), места событий.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
РАЗРЕЗ 3: МИРОВОЙ КОНТЕКСТ
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Найди 3–7 мировых событий, которые перекликаются с ключевыми датами или локациями героя:
— ключевые события мировой истории, которые происходили параллельно с жизнью героя
— если герой был в стране или регионе, где случились значимые мировые события — обязательно
— интересные совпадения: "в тот год, когда она выходила замуж, на другом конце света..."
— только события, которые можно естественно вплести в биографический нарратив

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ФОРМАТ ВЫХОДНЫХ ДАННЫХ
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Верни JSON:

{
  "project_id": "string",
  "subject": "string",

  "epoch_context": [
    {
      "period": {"start_year": 1920, "end_year": 1933, "label": "Детство и НЭП"},
      "relevance": "Как этот период связан с героем",
      "content": "Исторический контекст эпохи",
      "suggested_insertions": [
        {
          "text": "Готовый фрагмент для вставки в книгу (1–3 предложения)",
          "placement_hint": "Рядом с каким событием жизни героя вставить",
          "format": "inline | italic_block",
          "priority": "high | medium | low"
        }
      ]
    }
  ],

  "location_context": [
    {
      "location": "Название места",
      "period_of_stay": "когда герой там жил",
      "significance": "Почему это место важно для понимания судьбы героя",
      "historical_facts": "Что происходило в этом месте в тот период",
      "local_color": "Бытовые и культурные особенности места",
      "suggested_insertions": [
        {
          "text": "Готовый фрагмент",
          "placement_hint": "Куда вставить",
          "format": "inline | italic_block",
          "priority": "high | medium | low"
        }
      ]
    }
  ],

  "world_context": [
    {
      "world_event": "Название мирового события",
      "year": 1946,
      "connection_to_hero": "Как это событие перекликается с жизнью героя",
      "suggested_insertion": {
        "text": "Готовый фрагмент для вставки",
        "placement_hint": "Куда вставить",
        "format": "inline | italic_block",
        "priority": "high | medium | low"
      }
    }
  ],

  "era_glossary": [
    {
      "term": "Реалия эпохи или места",
      "explanation": "Пояснение для современного читателя",
      "context": "Временной или географический контекст"
    }
  ]
}

ВАЖНО:
— Все suggested_insertions — это готовые фрагменты для вставки в книгу, написанные живым языком.
— Не выдумывай факты. Если не знаешь детали о конкретном месте — честно укажи это.
— Мировой контекст: ищи неочевидные, но интересные связи. Не банальности.
— Верни JSON и ничего кроме JSON.
"""

def main():
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("[ERROR] ANTHROPIC_API_KEY не задан"); sys.exit(1)

    fact_map = json.loads((ROOT / "exports" / "test_fact_map_karakulina_v5.json").read_text(encoding="utf-8"))
    transcript = (ROOT / "exports" / "karakulina_cleaned_transcript.txt").read_text(encoding="utf-8")[:10000]

    user_msg = json.dumps({
        "project_id": "karakulina_historian_extended",
        "subject": "Каракулина Валентина Ивановна, 17.12.1920 — 2015",
        "fact_map": fact_map,
        "transcript_excerpt": transcript
    }, ensure_ascii=False)

    print("[START] Расширенный историк (3 разреза) — Каракулина...\n")
    client = anthropic.Anthropic(api_key=api_key)

    result = ""
    for attempt in range(1, 5):
        try:
            with client.messages.stream(
                model="claude-sonnet-4-20250514",
                max_tokens=16000,
                temperature=0.3,
                system=PROMPT,
                messages=[{"role": "user", "content": user_msg}]
            ) as stream:
                for text in stream.text_stream:
                    result += text
                    print(text, end="", flush=True)
            break
        except Exception as e:
            if "overloaded" in str(e).lower() and attempt < 4:
                wait = 25 * attempt
                print(f"\n[RETRY] {attempt}/4 — перегружен, ждём {wait}с...")
                time.sleep(wait)
            else:
                raise

    print("\n\n[PARSING] Разбираем результат...")

    # Сохраняем raw JSON
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_path = ROOT / "exports" / f"karakulina_historian_extended_{ts}.json"

    try:
        # Убираем возможный markdown-блок
        clean = result.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        parsed = json.loads(clean)
        raw_path.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[SAVED] JSON: {raw_path}")

        # Печатаем статистику
        print(f"\n{'='*60}")
        print(f"РЕЗУЛЬТАТ")
        print(f"{'='*60}")
        print(f"  Эпоха: {len(parsed.get('epoch_context', []))} периодов")
        print(f"  Локации: {len(parsed.get('location_context', []))} мест")
        print(f"  Мировой контекст: {len(parsed.get('world_context', []))} событий")
        print(f"  Глоссарий: {len(parsed.get('era_glossary', []))} терминов")

        print(f"\n  ЛОКАЦИИ:")
        for loc in parsed.get("location_context", []):
            print(f"    — {loc.get('location')} ({loc.get('period_of_stay', '?')})")

        print(f"\n  МИРОВЫЕ СОБЫТИЯ:")
        for w in parsed.get("world_context", []):
            print(f"    — {w.get('year', '?')}: {w.get('world_event', '?')}")
            print(f"      → {w.get('connection_to_hero', '')[:100]}")

    except json.JSONDecodeError as e:
        print(f"[WARNING] JSON не распарсился: {e}")
        raw_path.write_text(result, encoding="utf-8")
        print(f"[SAVED] Raw текст: {raw_path}")

if __name__ == "__main__":
    main()
