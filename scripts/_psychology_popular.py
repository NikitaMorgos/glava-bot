#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Переписываем психологический анализ Каракулиной в популярный стиль.
"""
import os, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

import anthropic

SOURCE = (ROOT / "exports" / "karakulina_psychology_types.txt").read_text(encoding="utf-8")

PROMPT = """
Ты — редактор популярного психологического журнала. Умеешь писать про сложные типологии так, 
чтобы читатель с улицы понял и увлёкся, а не заснул.

Перед тобой — психологический разбор реального человека по нескольким типологиям.

Твоя задача: переписать этот материал в лёгком, живом стиле.

Правила:
— Убери термины там, где можно обойтись без них. Если термин нужен — объясни его в одной фразе.
— Сохрани ВСЕ конкретные детали из биографии (чашки кипятком, уколы бесплатно, авоська из зонтика, французские духи в 85 лет и т.д.) — это самое ценное.
— Каждый раздел должен начинаться с яркого тезиса, а не с названия системы.
— Тон: как будто умный друг рассказывает про свою бабушку.
— Длина: примерно такая же, как оригинал. Не сокращай смысл, только стиль.
— Не используй слова: «таким образом», «следует отметить», «данный», «является».
— В конце — синтез: одна страница про суть этого человека, без типологических ярлыков вообще.
"""

def main():
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("[ERROR] ANTHROPIC_API_KEY не задан"); sys.exit(1)

    print("[START] Переписываем в популярный стиль...\n")
    client = anthropic.Anthropic(api_key=api_key)

    result = ""
    for attempt in range(1, 5):
        try:
            with client.messages.stream(
                model="claude-sonnet-4-20250514",
                max_tokens=8000,
                temperature=0.7,
                system=PROMPT,
                messages=[{"role": "user", "content": SOURCE}]
            ) as stream:
                for text in stream.text_stream:
                    result += text
                    print(text, end="", flush=True)
            break
        except Exception as e:
            if "overloaded" in str(e).lower() and attempt < 4:
                wait = 20 * attempt
                print(f"\n[RETRY] {attempt}/4 — перегружен, ждём {wait}с...")
                time.sleep(wait)
            else:
                raise

    print("\n")
    out = ROOT / "exports" / "karakulina_psychology_popular.txt"
    out.write_text(result, encoding="utf-8")
    print(f"[SAVED] {out}")

if __name__ == "__main__":
    main()
