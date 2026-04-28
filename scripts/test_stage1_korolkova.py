#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stage 1: Fact Extractor для Корольковой Елены Андреевны
Транскрипт уже очищен — запускаем с --skip-cleaner.

Использование:
    python scripts/test_stage1_korolkova.py
"""
import argparse
import json
import os
import sys
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

from pipeline_utils import load_config, run_cleaner, run_fact_extractor, print_stats

# ──────────────────────────────────────────────────────────────────
# Параметры субъекта
# ──────────────────────────────────────────────────────────────────
CHARACTER_NAME = "Королькова Елена Андреевна"
NARRATOR_NAME = "Дочь"
NARRATOR_RELATION = "дочь"
KNOWN_BIRTH_YEAR = 1932
KNOWN_DETAILS = "Девичья фамилия: Соловьёва. Родилась 1 апреля 1932, деревня Русино, Ромешковский район, Калининская область."
PROJECT_ID = "korolkova_v2_test"

MIN_TRANSCRIPT_CHARS = 5_000

# ──────────────────────────────────────────────────────────────────
# Чек-лист (на основе старой fact_map + транскрипта)
# ──────────────────────────────────────────────────────────────────
CHECKLIST = {
    "persons": [
        ("Соловьёва/Королькова Елена Андреевна (субъект)", ["елена", "корольков"]),
        ("Соловьёв Андрей (отец)", ["соловьёв", "андрей"]),
        ("Соловьёва (мать)", ["соловьёва", "мать"]),
        ("Александра / Шура (родственница)", ["александр", "шура"]),
        ("Антонина / Тоня", ["антонин", "тоня"]),
        ("Людмила / Люда", ["людмил", "люда"]),
        ("Алексей / дядя Лёша", ["алексей", "лёша"]),
        ("Маруся / тётя Маруся", ["маруся"]),
    ],
    "locations": [
        ("деревня Русино, Калининская обл. (рождение)", ["русин", "калинин"]),
        ("Ромешковский / Ромашковский район", ["ромеш", "ромашк"]),
    ],
    "events": [
        ("Рождение 1 апреля 1932", ["1932", "апрел"]),
        ("Замужество / фамилия Королькова", ["корольков", "замуж"]),
    ],
    "traits": [
        ("Личностные черты", ["характер", "добр", "трудолюб", "сильн"]),
    ],
}


def check_fact_map(fact_map: dict) -> dict:
    all_text = json.dumps(fact_map, ensure_ascii=False).lower()
    results = {}
    for section, items in CHECKLIST.items():
        results[section] = [(label, any(k in all_text for k in keys)) for label, keys in items]
    return results


def print_checklist(results: dict):
    print("\n" + "=" * 60)
    print("ЧЕК-ЛИСТ ПО КОРОЛЬКОВОЙ")
    print("=" * 60)
    for section, items in results.items():
        ok = sum(1 for _, f in items if f)
        print(f"\n{section.upper()} ({ok}/{len(items)}):")
        for label, found in items:
            print(f"  {'[OK]' if found else '[--]'} {label}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--transcript",
        default=str(ROOT / "exports" / "korolkova_cleaned_transcript.txt"),
        help="Путь к транскрипту.",
    )
    parser.add_argument("--output-dir", default=str(ROOT / "exports"))
    parser.add_argument("--skip-cleaner", action="store_true", default=True)
    args = parser.parse_args()

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("[ERROR] ANTHROPIC_API_KEY не задан")
        sys.exit(1)

    transcript_path = Path(args.transcript)
    if not transcript_path.exists():
        print(f"[ERROR] Транскрипт не найден: {transcript_path}")
        sys.exit(1)

    raw_text = transcript_path.read_text(encoding="utf-8")
    if len(raw_text) < MIN_TRANSCRIPT_CHARS:
        print(f"[WARNING] Транскрипт слишком короткий: {len(raw_text)} символов")

    print(f"\n[START] {CHARACTER_NAME} | {len(raw_text)} символов | {transcript_path.name}")

    cfg = load_config()
    print(f"[CONFIG] FactExtractor: {cfg['fact_extractor']['model']} max_tokens={cfg['fact_extractor']['max_tokens']}")
    print(f"[CONFIG] Промпт: {cfg['fact_extractor']['prompt_file']}")

    client = anthropic.Anthropic(api_key=api_key)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Шаг 1: Fact Extractor (Cleaner пропускаем — транскрипт уже очищен)
    import time
    print("\n[FACT EXTRACTOR] Запускаем...")
    for attempt in range(1, 6):
        try:
            fact_map = run_fact_extractor(
                client, raw_text,
                subject_name=CHARACTER_NAME,
                narrator_name=NARRATOR_NAME,
                narrator_relation=NARRATOR_RELATION,
                project_id=PROJECT_ID,
                known_birth_year=KNOWN_BIRTH_YEAR,
                known_details=KNOWN_DETAILS,
                cfg=cfg,
            )
            break
        except Exception as e:
            err = str(e)
            if "overloaded" in err.lower() and attempt < 5:
                wait = 20 * attempt
                print(f"[RETRY] Попытка {attempt}/5 — API перегружен, ждём {wait}с...")
                time.sleep(wait)
            else:
                raise

    out_path = out_dir / "korolkova_fact_map_v2.json"
    out_path.write_text(json.dumps(fact_map, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[SAVED] Fact map: {out_path}")

    print_stats(fact_map, raw_text, label="КОРОЛЬКОВА")
    checklist = check_fact_map(fact_map)
    print_checklist(checklist)

    ok = sum(1 for items in checklist.values() for _, f in items if f)
    total = sum(len(items) for items in checklist.values())
    print(f"\n[RESULT] Покрытие: {ok}/{total} ({100*ok//total if total else 0}%)")
    print(f"[RESULT] Fact map: {out_path}")


if __name__ == "__main__":
    main()
