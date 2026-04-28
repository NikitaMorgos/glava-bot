#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import sys

src = "exports/karakulina_book_draft_stage3_20260327_190422.json"
dst = "exports/karakulina_stage3_FINAL_20260327.txt"

with open(src, encoding="utf-8") as f:
    data = json.load(f)

bd = data.get("book_draft", data)
chapters = bd.get("chapters", [])

lines = []
for ch in chapters:
    lines.append("=" * 60)
    lines.append(f"{ch.get('id', '')} | {ch.get('title', '')}")
    lines.append("=" * 60)
    lines.append(ch.get("content", ""))
    lines.append("")

text = "\n".join(lines)
with open(dst, "w", encoding="utf-8") as f:
    f.write(text)

print(f"OK: {len(chapters)} глав, {len(text)} символов")
print(f"Сохранено: {dst}")
