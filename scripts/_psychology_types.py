#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Эксперимент: биография Каракулиной через призму психолога-типолога.
Типологии: Знаки зодиака, Соционика, Эннеаграмма, Хьюман Дизайн, MBTI.
"""
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

import anthropic

PROMPT = """
Ты — психолог-практик, который свободно владеет несколькими популярными типологическими системами:
— Знаки зодиака и астрология
— Соционика (ТИМ, дихотомии, квадры)
— Эннеаграмма (9 типов + крылья + центры)
— Хьюман Дизайн (тип, профиль, авторитет)
— MBTI (16 типов)
— Энеостиль / цветотипы характера (Томас Хюбл, Ицхак Адизес и т.п.)

Перед тобой — карта фактов и фрагменты интервью о реальном человеке.

Твоя задача:
1. Проанализировать личность человека через КАЖДУЮ из перечисленных систем.
2. По каждой системе — сначала выдвинуть гипотезу типа, потом обосновать конкретными фактами из биографии.
3. В конце — синтез: что все системы говорят о человеке СООБЩА? Где они сходятся?
4. Оговорка: это не диагноз, а интерпретация — честно признай, где данных недостаточно.

Важно:
— Опирайся ТОЛЬКО на факты из карты и интервью, не фантазируй.
— Будь конкретным: цитируй поведенческие эпизоды, подтверждающие тип.
— Язык — живой, не академический. Пиши как будто объясняешь клиенту на сессии.
— Хьюман Дизайн: дата рождения 17 декабря 1920, время рождения неизвестно — укажи что можно определить без времени, и что остаётся неизвестным.

Формат ответа: свободный текст, заголовки по каждой системе, финальный синтез.
"""

def main():
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("[ERROR] ANTHROPIC_API_KEY не задан")
        sys.exit(1)

    # Загружаем данные
    fact_map = json.loads((ROOT / "exports" / "test_fact_map_karakulina_v5.json").read_text(encoding="utf-8"))
    transcript = (ROOT / "exports" / "karakulina_cleaned_transcript.txt").read_text(encoding="utf-8")

    # Берём только первые 15к символов транскрипта чтобы не превышать контекст
    transcript_excerpt = transcript[:15000]

    user_message = json.dumps({
        "subject": "Каракулина Валентина Ивановна, 17 декабря 1920 — 2015",
        "fact_map": fact_map,
        "transcript_excerpt": transcript_excerpt
    }, ensure_ascii=False)

    print("[START] Анализ личности Каракулиной через психологические типологии...")
    print(f"[INPUT] fact_map: {len(json.dumps(fact_map))} символов")
    print(f"[INPUT] transcript: {len(transcript_excerpt)} символов (из {len(transcript)})")
    print()

    client = anthropic.Anthropic(api_key=api_key)

    for attempt in range(1, 5):
        try:
            result = ""
            with client.messages.stream(
                model="claude-sonnet-4-20250514",
                max_tokens=8000,
                temperature=0.7,
                system=PROMPT,
                messages=[{"role": "user", "content": user_message}]
            ) as stream:
                for text in stream.text_stream:
                    result += text
                    print(text, end="", flush=True)
            break
        except Exception as e:
            if "overloaded" in str(e).lower() and attempt < 4:
                wait = 20 * attempt
                print(f"\n[RETRY] Попытка {attempt}/4 — перегружен, ждём {wait}с...")
                time.sleep(wait)
            else:
                raise

    print("\n")

    out_path = ROOT / "exports" / "karakulina_psychology_types.txt"
    out_path.write_text(result, encoding="utf-8")
    print(f"[SAVED] {out_path}")


if __name__ == "__main__":
    main()
