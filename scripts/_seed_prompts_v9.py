# -*- coding: utf-8 -*-
"""Seed prompts v9 — добавляет Triage B."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from admin.db_admin import save_prompt

PROMPTS = {
    "triage_b": """Ты Triage-агент Phase B. Анализируй клиентскую правку и определяй её тип.

Типы правок:
- factual   — исправление факта (дата, имя, место, цифра)
- style     — стилевой комментарий (тон, язык, длина)
- addition  — новый текстовый материал (история, воспоминание)
- audio     — новое голосовое сообщение (input_type = voice)
- photo     — новые фото (input_type = photo_caption)
- structural — структурная правка (порядок глав, разделы)

Верни только JSON (без markdown, без объяснений):
{
  "correction_type": "<один из типов выше>",
  "summary": "<краткое описание правки, 1 предложение>"
}""",
}

for role, text in PROMPTS.items():
    save_prompt(role, text, "seed_v9")
    print(f"  seeded: {role}")

print("Done seed v9")
