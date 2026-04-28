#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stage 1: Transcript Cleaner → Fact Extractor для Дмитриева Сергея Александровича

Транскрипт из 6 аудиофайлов (3 рассказчика):
  - Лена (дочь) — основная запись, папа.m4a
  - Дима (сын) — папад1-3.m4a
  - Катя (дочь) — папак1-2.m4a

Использование:
    python scripts/test_stage1_dmitriev.py
    python scripts/test_stage1_dmitriev.py --skip-cleaner
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
CHARACTER_NAME = "Дмитриев Сергей Александрович"
NARRATOR_NAME = "Лена, Дима и Катя Дмитриевы"
NARRATOR_RELATION = "дети (дочь Лена, сын Дима, дочь Катя)"
KNOWN_BIRTH_YEAR = 1955
KNOWN_DETAILS = (
    "Родился 10 марта 1955 года в г. Тверь (Калинин). "
    "Умер 24 ноября 2001 года, рак лёгких 4-й стадии, 46 лет. "
    "Работал водителем на почте (автобаза связи). "
    "Служил в ВДВ, Каунас. "
    "Жена: Валентина Александровна (Королькова). "
    "Дети: Дмитрий (1978), Екатерина и Елена (близняшки, 1981)."
)
PROJECT_ID = "dmitriev_v1"

MIN_TRANSCRIPT_CHARS = 10_000

# ──────────────────────────────────────────────────────────────────
# Чек-лист
# ──────────────────────────────────────────────────────────────────
CHECKLIST = {
    "persons": [
        ("Дмитриев Сергей Александрович (субъект)", ["сергей", "дмитриев"]),
        ("Екатерина Егоровна (мать)", ["екатерин", "бабушк"]),
        ("Александр Дмитриевич (отец, осуждён)", ["александр", "отец"]),
        ("Валентина Александровна (жена)", ["валентин", "мам"]),
        ("Дмитрий / Дима (сын)", ["дима", "дмитрий"]),
        ("Екатерина / Катя (дочь)", ["катя", "екатерин"]),
        ("Елена / Лена (дочь)", ["лена", "елен"]),
        ("Шигин (друг)", ["шигин"]),
    ],
    "locations": [
        ("Тверь / Калинин (место рождения и жизни)", ["тверь", "калинин"]),
        ("Заволжский район Твери", ["заволж"]),
        ("Каунас, Прибалтика (служба ВДВ)", ["каунас", "прибалт"]),
        ("Деревня (огород, хозяйство)", ["деревн"]),
    ],
    "events": [
        ("Рождение 10 марта 1955", ["1955", "март"]),
        ("Отец пил, бил, посадили в тюрьму", ["тюрьм", "посадил"]),
        ("Учёба в индустриальном техникуме", ["техникум"]),
        ("Служба в ВДВ, прыжок с парашютом, сломал руку", ["парашют", "сломал", "вдв"]),
        ("Знакомство с Валентиной на свадьбе", ["свадьб", "познакомил"]),
        ("Трое детей: Дима 1978, Катя и Лена 1981", ["1978", "1981"]),
        ("Получили 4-комнатную квартиру ~1988", ["квартир", "четырёх", "четырех"]),
        ("Перестройка — трудные времена, смена работ", ["перестроеч", "перестройк"]),
        ("Поездка в Париж от предприятия", ["париж"]),
        ("Рак лёгких, умер 24 ноября 2001", ["рак", "2001", "умер"]),
    ],
    "traits": [
        ("Добрый, дружелюбный, открытый", ["добр", "дружелюб"]),
        ("Любил читать (фантастика, исторические)", ["читал", "книг", "фантаст"]),
        ("Не пил (насмотрелся на отца)", ["не пил", "не пить", "почти не пил"]),
        ("Усы носил всю жизнь", ["усы", "усов"]),
        ("Рано вставал, читал до работы", ["четыре", "рано вставал", "до работы"]),
        ("Любил готовить, творческий беспорядок", ["готовил", "готовить", "суп"]),
        ("Любил фотографировать", ["фотограф"]),
        ("Цитата: «молодые все красивые»", ["молодые все красивые"]),
    ],
}


def check_fact_map(fact_map: dict) -> dict:
    all_text = json.dumps(fact_map, ensure_ascii=False).lower()
    results = {}
    for section, items in CHECKLIST.items():
        results[section] = [
            (label, any(k in all_text for k in keys))
            for label, keys in items
        ]
    return results


def print_checklist(results: dict):
    print("\n" + "=" * 60)
    print("ЧЕК-ЛИСТ ПО ДМИТРИЕВУ")
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
        default=str(ROOT / "exports" / "transcripts" / "dmitriev_combined_transcript.txt"),
    )
    parser.add_argument("--output-dir", default=str(ROOT / "exports"))
    parser.add_argument("--skip-cleaner", action="store_true")
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
        print(f"[WARNING] Транскрипт короткий: {len(raw_text)} символов (минимум {MIN_TRANSCRIPT_CHARS})")
        answer = input("Продолжить? [y/N]: ").strip().lower()
        if answer != "y":
            sys.exit(1)

    print(f"\n[START] {CHARACTER_NAME} | {len(raw_text)} символов | {transcript_path.name}")
    print(f"[INFO] Рассказчики: {NARRATOR_NAME}")

    cfg = load_config()
    print(f"[CONFIG] Cleaner: {cfg['cleaner']['model']} max_tokens={cfg['cleaner']['max_tokens']}")
    print(f"[CONFIG] FactExtractor: {cfg['fact_extractor']['model']} max_tokens={cfg['fact_extractor']['max_tokens']}")

    client = anthropic.Anthropic(api_key=api_key)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Шаг 1: Cleaner
    if args.skip_cleaner:
        cleaned_text = raw_text
        cleaning_metadata = {"cleaning_applied": False, "reason": "skipped"}
        print("[CLEANER] Пропущен (--skip-cleaner)")
    else:
        cleaned_text, cleaning_metadata = run_cleaner(
            client, raw_text,
            subject_name=CHARACTER_NAME,
            narrator_name=NARRATOR_NAME,
            narrator_relation=NARRATOR_RELATION,
            cfg=cfg,
        )

    cleaned_path = out_dir / "dmitriev_cleaned_transcript.txt"
    meta_path = out_dir / "dmitriev_cleaning_metadata.json"
    cleaned_path.write_text(cleaned_text, encoding="utf-8")
    meta_path.write_text(
        json.dumps(cleaning_metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[SAVED] {cleaned_path.name} ({len(cleaned_text)} символов)")

    # Шаг 2: Fact Extractor
    fact_map = run_fact_extractor(
        client, cleaned_text,
        subject_name=CHARACTER_NAME,
        narrator_name=NARRATOR_NAME,
        narrator_relation=NARRATOR_RELATION,
        project_id=PROJECT_ID,
        known_birth_year=KNOWN_BIRTH_YEAR,
        known_details=KNOWN_DETAILS,
        cfg=cfg,
    )

    out_path = out_dir / "dmitriev_fact_map_v1.json"
    out_path.write_text(json.dumps(fact_map, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[SAVED] {out_path.name}")

    print_stats(fact_map, cleaned_text, label="ДМИТРИЕВ")
    checklist = check_fact_map(fact_map)
    print_checklist(checklist)

    ok = sum(1 for items in checklist.values() for _, f in items if f)
    total = sum(len(items) for items in checklist.values())
    print(f"\n[RESULT] Покрытие чек-листа: {ok}/{total} ({100*ok//total}%)")
    print(f"[RESULT] Fact map: {out_path}")


if __name__ == "__main__":
    main()
