#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Финальная точечная правка черновика этапа 2.

Исправляет:
1. Написания имён собственных по fact_map (против ASR-ошибок в транскрипте)
   - Новомергородский → Новомиргородский
   - Новомергородского → Новомиргородского
   - Керсанов → Кирсанов
   - Капашвара → Капошвара

2. Хеджинг для needs_verification: true фактов (Венгрия 1958)
   - «В 1958 году семья переехала в Венгрию» →
     «Предположительно в 1958 году семья переехала в Венгрию»
"""
import json
import sys
from pathlib import Path
from datetime import datetime

DRAFT_PATH = "/opt/glava/exports/karakulina_book_draft_v3_20260327_062706.json"
OUT_PREFIX = "/opt/glava/exports/karakulina_book_draft_final"

REPLACEMENTS = [
    # Имена — fact_map vs ASR
    ("Новомергородский", "Новомиргородский"),
    ("Новомергородского", "Новомиргородского"),
    ("Новомергородской", "Новомиргородской"),
    ("Керсанов", "Кирсанов"),
    ("Капашвара", "Капошвара"),
    # Хеджинг Венгрия 1958 — только точная фраза без оговорки
    ("В 1958 году семья переехала в Венгрию",
     "Предположительно в 1958 году семья переехала в Венгрию"),
]

def fix_text(text: str) -> tuple[str, list[str]]:
    changes = []
    for old, new in REPLACEMENTS:
        if old in text:
            count = text.count(old)
            text = text.replace(old, new)
            changes.append(f"  ✓ «{old}» → «{new}» ({count}×)")
    return text, changes

def main():
    with open(DRAFT_PATH, encoding="utf-8") as f:
        draft = json.load(f)

    chapters = draft.get("chapters", [])
    total_changes = []

    for ch in chapters:
        content = ch.get("content", "")
        if content:
            fixed, changes = fix_text(content)
            if changes:
                ch["content"] = fixed
                total_changes.append(f"\n[{ch.get('id', '?')}] {ch.get('title', '')}")
                total_changes.extend(changes)

    if not total_changes:
        print("Нет изменений — текст уже корректен")
        return

    print("Внесённые правки:")
    print("\n".join(total_changes))

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = f"{OUT_PREFIX}_{ts}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(draft, f, ensure_ascii=False, indent=2)
    print(f"\n[SAVED] {out_path}")

if __name__ == "__main__":
    main()
