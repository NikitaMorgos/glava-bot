#!/usr/bin/env python3
"""
Прогон транскрипта интервью через ChatGPT — биография.
Запуск: python scripts/run_interview_bio.py [файл.txt]
        или: python scripts/run_interview_bio.py  (читает из stdin)
"""
import os
import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root))

# Загружаем .env
from dotenv import load_dotenv
load_dotenv(_root / ".env")

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("OPENAI_API_KEY не задан в .env")
    sys.exit(1)

from llm_bio import process_transcript_to_bio

if len(sys.argv) > 1:
    path = Path(sys.argv[1])
    if not path.exists():
        print(f"Файл не найден: {path}")
        sys.exit(1)
    transcript = path.read_text(encoding="utf-8")
    print(f"Загружено {len(transcript)} символов из {path}")
else:
    print("Вставь транскрипт (Ctrl+Z+Enter в Windows или Ctrl+D в Unix для завершения):")
    transcript = sys.stdin.read()

if not transcript.strip():
    print("Транскрипт пуст")
    sys.exit(1)

print("\n--- Запуск ChatGPT (модель из OPENAI_BIO_MODEL, по умолчанию gpt-4o) ---\n")
bio = process_transcript_to_bio(transcript, api_key=api_key)

if bio:
    print("=== РЕЗУЛЬТАТ ===\n")
    print(bio)
    # Сохранить в файл
    out_path = _root / "exports" / "bio_output.txt"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(bio, encoding="utf-8")
    print(f"\n\nСохранено в: {out_path}")
else:
    print("Ошибка: LLM не вернул текст")
