#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест пайплайна Stage 1: Transcript Cleaner → Fact Extractor
Субъект: Каракулина Валентина Ивановна

Конфиг (модели, токены, промпты): prompts/pipeline_config.json
Shared логика: pipeline_utils.py

ВАЖНО: используем ПОЛНЫЙ ASR-транскрипт (exports/transcripts/),
       а не ручные конспекты или частичные файлы.
       Минимальный порог: MIN_TRANSCRIPT_CHARS = 10_000 символов.

Использование:
    python scripts/test_stage1_pipeline.py
    python scripts/test_stage1_pipeline.py --transcript /path/to/transcript.txt
"""
import argparse
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

from pipeline_utils import (
    load_config,
    run_cleaner,
    run_fact_extractor,
    print_stats,
    save_run_manifest,
)

# ──────────────────────────────────────────────────────────────────
# Параметры субъекта
# ──────────────────────────────────────────────────────────────────
CHARACTER_NAME = "Каракулина Валентина Ивановна"
NARRATOR_NAME = "Татьяна Каракулина"
NARRATOR_RELATION = "дочь"
KNOWN_BIRTH_YEAR = None
KNOWN_DETAILS = None
PROJECT_ID = "karakulina_v3.1_test"

# Минимальный порог для полного транскрипта (конспекты меньше ~3000 символов)
MIN_TRANSCRIPT_CHARS = 10_000

# ──────────────────────────────────────────────────────────────────
# Чек-лист
# ──────────────────────────────────────────────────────────────────
CHECKLIST = {
    "persons": [
        ("Валентина Ивановна Каракулина (Руда)", ["валентина", "каракулина"]),
        ("Руда Иван Андреевич (отец)", ["иван", "руда"]),
        ("Руда Пелагея Алексеевна (мать)", ["пелагея", "руда"]),
        ("Полина / тётя Поля (сестра)", ["полина", "поля"]),
        ("Дмитрий Каракулин (муж)", ["дмитрий", "каракул"]),
        ("Валерий Каракулин (сын)", ["валерий"]),
        ("Татьяна Каракулина (дочь)", ["татьяна"]),
        ("тётя Шура", ["шура"]),
        ("Владимир Маргось (муж Татьяны)", ["владимир", "маргос"]),
        ("Олег Кужба (второй муж Татьяны)", ["олег", "кужб"]),
    ],
    "locations": [
        ("Марьевка, Кировоградская обл. (место рождения)", ["марьевк", "кировоград"]),
        ("Старобельск, Луганская обл.", ["старобельск"]),
        ("Германия (1946–1961)", ["германи"]),
        ("Венгрия (1958–1961)", ["венгри"]),
        ("Тверь (Химинститут)", ["тверь", "химинститут"]),
        ("Кирсанов, Тамбовская обл.", ["кирсанов"]),
    ],
    "events": [
        ("Рождение 17 декабря 1920", ["1920", "17 декабря"]),
        ("Голод 1933, смерть матери, детдом", ["1933", "голод", "детдом"]),
        ("Акушерское училище 1938–1940", ["акушерск", "1938", "1940"]),
        ("Призыв на войну 23 июня 1941", ["1941", "23 июня"]),
        ("Лейтенант медслужбы, боевые награды", ["лейтенант", "наград"]),
        ("Свадьба 12 июля 1946, Старобельск", ["1946", "свадьб"]),
        ("Переезд в Германию 1946", ["германи"]),
        ("Переезд в Венгрию 1958, конкретные города", ["венгри", "кечкемет", "кишкун"]),
        ("Операция на желудок 1960", ["операци", "желудок"]),
        ("Дача появилась 1960", ["дач", "1960"]),
        ("Переезд в Тверь 1956", ["1956", "тверь"]),
        ("Замужество Татьяны 1977 (Владимир Маргось)", ["1977", "маргос"]),
        ("Смерть мужа 1978", ["1978", "умер"]),
        ("Пенсия 1994", ["1994", "пенси"]),
        ("Второй брак Татьяны 1996 (Олег Кужба)", ["1996", "кужб"]),
        ("Смерть 3 октября 2015", ["2015"]),
    ],
    "traits": [
        ("Трудолюбивая", ["трудолюб"]),
        ("Аккуратная, дезинфицировала всё", ["аккурат", "дезинфекц", "дезинфицир"]),
        ("Атеистка, коммунистка", ["атеист", "коммунист", "бог"]),
        ("Хороший голос, любила петь", ["пела", "голос"]),
        ("Хороший вкус в одежде, шляпки", ["шляпк", "одежд"]),
        ("Гостеприимная, хлебосольная", ["гостеприимн", "хлебосольн"]),
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
    print(f"ЧЕК-ЛИСТ ПО КАРАКУЛИНОЙ")
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
        default=str(ROOT / "exports" / "transcripts" / "karakulina_valentina_interview_assemblyai.txt"),
        help="Путь к полному ASR-транскрипту (exports/transcripts/). НЕ используйте ручные конспекты.",
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

    # Валидация: защита от случайной подачи ручного конспекта
    if len(raw_text) < MIN_TRANSCRIPT_CHARS:
        print(f"[WARNING] ⚠️  Транскрипт подозрительно короткий: {len(raw_text)} символов (минимум {MIN_TRANSCRIPT_CHARS}).")
        print(f"[WARNING] Убедитесь, что подаёте полный ASR-файл из exports/transcripts/, а не ручной конспект.")
        answer = input("Продолжить всё равно? [y/N]: ").strip().lower()
        if answer != "y":
            print("[ABORT] Прерван. Укажите полный транскрипт через --transcript.")
            sys.exit(1)
    print(f"\n[START] {CHARACTER_NAME} | {len(raw_text)} символов | {transcript_path.name}")

    cfg = load_config()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    print(f"[CONFIG] Cleaner: {cfg['cleaner']['model']} max_tokens={cfg['cleaner']['max_tokens']}")
    print(f"[CONFIG] FactExtractor: {cfg['fact_extractor']['model']} max_tokens={cfg['fact_extractor']['max_tokens']}")
    print(f"[CONFIG] Промпты: {cfg['cleaner']['prompt_file']} / {cfg['fact_extractor']['prompt_file']}")

    client = anthropic.Anthropic(api_key=api_key)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Шаг 1.5: Cleaner
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

    (out_dir / "karakulina_cleaned_transcript.txt").write_text(cleaned_text, encoding="utf-8")
    (out_dir / "karakulina_cleaning_metadata.json").write_text(
        json.dumps(cleaning_metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[SAVED] Cleaned transcript + metadata")

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

    out_path = out_dir / "test_fact_map_karakulina_v5.json"
    out_path.write_text(json.dumps(fact_map, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[SAVED] Fact map: {out_path}")

    print_stats(fact_map, cleaned_text, label="КАРАКУЛИНА")
    checklist = check_fact_map(fact_map)
    print_checklist(checklist)

    ok = sum(1 for items in checklist.values() for _, f in items if f)
    total = sum(len(items) for items in checklist.values())
    print(f"\n[RESULT] Покрытие: {ok}/{total} ({100*ok//total}%)")
    print(f"[RESULT] Fact map: {out_path}")

    save_run_manifest(
        output_dir=out_dir,
        prefix="karakulina",
        stage="stage1",
        project_id=PROJECT_ID,
        cfg=cfg,
        ts=ts,
        inputs={
            "transcript_path": str(transcript_path),
            "transcript_chars": len(raw_text),
            "skip_cleaner": args.skip_cleaner,
        },
        outputs={
            "cleaned_transcript_path": str(out_dir / "karakulina_cleaned_transcript.txt"),
            "cleaning_metadata_path": str(out_dir / "karakulina_cleaning_metadata.json"),
            "fact_map_path": str(out_path),
            "checklist_coverage": {"ok": ok, "total": total},
        },
    )


if __name__ == "__main__":
    main()
