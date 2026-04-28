#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест пайплайна Stage 1: Transcript Cleaner → Fact Extractor
Субъект: Королькова (Соловьёва) Елена Андреевна, 1932 г.р.

Конфиг (модели, токены, промпты): prompts/pipeline_config.json
Shared логика: pipeline_utils.py
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
NARRATOR_NAME = "Дочь Елены Андреевны"
NARRATOR_RELATION = "дочь"
KNOWN_BIRTH_YEAR = 1932
KNOWN_DETAILS = "Девичья фамилия Соловьёва. Родилась 1 апреля 1932. Деревня Русино, Калининская обл."
PROJECT_ID = "korolkova_v1_test"
TRANSCRIPT_FILE = ROOT / "exports" / "transcripts" / "korolkova_elena_interview_assemblyai.txt"

# ──────────────────────────────────────────────────────────────────
# Чек-лист
# ──────────────────────────────────────────────────────────────────
CHECKLIST = {
    "persons": [
        ("Королькова (Соловьёва) Елена Андреевна (герой)", ["елена андр", "соловьёва", "королькова"]),
        ("Отец Елены (мельник, убит на войне)", ["мельник", "богач", "отец погиб"]),
        ("Мать Елены (работала в колхозе)", ["мама была", "его мама", "мать работала"]),
        ("Шура/Александра (сестра, агроном)", ["шура", "александра"]),
        ("Тоня/Антонина (сестра, младшая)", ["тоня", "антонина"]),
        ("Дед (муж Елены, пастух / строитель, выпивал)", ["дед ", "муж "]),
        ("Дочь-рассказчик (родилась 1957)", ["родилась", "57-м родилась"]),
        ("Алиса (внучка, интервьюер)", ["алиса"]),
    ],
    "locations": [
        ("деревня Русино, Калининская обл.", ["русино", "русина"]),
        ("Калинин / Тверь (торговля мясом в 15 лет)", ["калинин"]),
        ("Осташков (ветеринарное училище)", ["осташков", "ташков", "кунчев"]),
        ("деревня Трубичиха (после свадьбы)", ["трубич"]),
        ("деревня Пасынково (основное место жизни)", ["пасынково", "пасненково"]),
        ("Свердловск / Екатеринбург (сестра Тоня)", ["свердловск", "екатеринбург"]),
    ],
    "events": [
        ("Рождение 1 апреля 1932", ["1932", "апреля"]),
        ("Детство во время войны (9 лет, работа на скотном дворе)", ["война", "скотном дворе", "стопки ели", "лебеду"]),
        ("Отец погиб 1941-42 (Без вести, Курская дуга)", ["1941", "погиб", "пропал без вести", "курская дуга"]),
        ("Учёба в ветеринарном техникуме в Осташкове", ["ветеринар", "техникум", "училище"]),
        ("Торговля мясом в Калинине в 15 лет", ["мясом торговать", "мясом продавать", "мясом торговля", "15 лет"]),
        ("Свадьба на Покров (14/16 октября)", ["покров", "свадьба", "октябр"]),
        ("Брак, замужество 1956-57 г.", ["1956", "замуж", "поженились"]),
        ("Рождение дочери 1957", ["1957", "родилась"]),
        ("Переезд в Пасынково (1.5 г. дочери)", ["пасынково", "пасненково", "переехали"]),
        ("Работа дояркой, бригадиром, ветеринаром в колхозе", ["дояркой", "бригадир", "ветеринар"]),
        ("Работа на заводе (цех каблуков), печёнка от вредности", ["завод", "каблук", "вредности", "печёнка"]),
        ("Хозлаборантка в химинституте", ["лаборантк", "химинститут", "хозлаборант"]),
        ("Работа на телятнике 1984 (для пенсии 130 руб.)", ["телятник", "1984", "130 "]),
    ],
    "traits": [
        ("Трудолюбивая, всё на себе (не ждала помощи)", ["всё на себе", "ни от кого", "никого не рассчитывала"]),
        ("Деловая жилка (торговля мясом, талант к бизнесу)", ["талант бизнеса", "мясом торгов"]),
        ("Строгая, командовала (прораб)", ["прораб", "командовала", "указания раздавала"]),
        ("Хорошо готовила (пирожки, пироги, салаты)", ["пирожк", "пирог", "готовила хорошо", "готовит хорошо"]),
        ("Вязала крючком (подзоры)", ["вязала", "крючком", "подзор"]),
        ("Сажала цветы на продажу (тюльпаны, нарциссы)", ["цветы", "тюльпан", "нарцисс"]),
        ("Не рассказывала о себе (замкнутая, работала не покладая рук)", ["не рассказывала", "ничего не говорит", "замкнут"]),
    ],
}


def check_fact_map(fact_map: dict) -> dict:
    all_text = json.dumps(fact_map, ensure_ascii=False).lower()
    results = {}
    for section, items in CHECKLIST.items():
        results[section] = [(label, any(k.lower() in all_text for k in keys)) for label, keys in items]
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


def parse_args():
    p = argparse.ArgumentParser(description="Stage 1 Королькова: Cleaner + Fact Extractor (pipeline_config.json)")
    p.add_argument("--transcript", type=str, default=str(TRANSCRIPT_FILE), help="Исходный транскрипт (сырой)")
    p.add_argument(
        "--fact-map-out",
        type=str,
        default=str(ROOT / "exports" / "korolkova_fact_map_v2.json"),
        help="Куда сохранить fact_map JSON",
    )
    p.add_argument(
        "--cleaned-out",
        type=str,
        default=str(ROOT / "exports" / "korolkova_cleaned_transcript.txt"),
        help="Очищенный транскрипт",
    )
    p.add_argument(
        "--cleaning-metadata-out",
        type=str,
        default=str(ROOT / "exports" / "korolkova_cleaning_metadata.json"),
        help="Метаданные cleaner",
    )
    return p.parse_args()


def main():
    args = parse_args()
    transcript_path = Path(args.transcript)
    fact_map_out = Path(args.fact_map_out)
    cleaned_out = Path(args.cleaned_out)
    meta_out = Path(args.cleaning_metadata_out)

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("[ERROR] ANTHROPIC_API_KEY не задан")
        sys.exit(1)

    if not transcript_path.exists():
        print(f"[ERROR] Транскрипт не найден: {transcript_path}")
        sys.exit(1)

    raw_text = transcript_path.read_text(encoding="utf-8")
    print(f"\n[START] {CHARACTER_NAME} | {len(raw_text)} символов | {transcript_path.name}")

    cfg = load_config()
    print(f"[CONFIG] Cleaner: {cfg['cleaner']['model']} max_tokens={cfg['cleaner']['max_tokens']}")
    print(f"[CONFIG] FactExtractor: {cfg['fact_extractor']['model']} max_tokens={cfg['fact_extractor']['max_tokens']}")
    print(f"[CONFIG] Промпты: {cfg['cleaner']['prompt_file']} / {cfg['fact_extractor']['prompt_file']}")

    client = anthropic.Anthropic(api_key=api_key)
    fact_map_out.parent.mkdir(parents=True, exist_ok=True)
    cleaned_out.parent.mkdir(parents=True, exist_ok=True)

    # Шаг 1.5: Cleaner
    cleaned_text, cleaning_metadata = run_cleaner(
        client, raw_text,
        subject_name=CHARACTER_NAME,
        narrator_name=NARRATOR_NAME,
        narrator_relation=NARRATOR_RELATION,
        cfg=cfg,
    )
    cleaned_out.write_text(cleaned_text, encoding="utf-8")
    meta_out.write_text(
        json.dumps(cleaning_metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[SAVED] Cleaned transcript + metadata → {cleaned_out.name}")

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

    out_path = fact_map_out
    out_path.write_text(json.dumps(fact_map, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[SAVED] Fact map: {out_path}")

    print_stats(fact_map, cleaned_text, label="КОРОЛЬКОВА")
    checklist = check_fact_map(fact_map)
    print_checklist(checklist)

    ok = sum(1 for items in checklist.values() for _, f in items if f)
    total = sum(len(items) for items in checklist.values())
    print(f"\n[RESULT] Покрытие: {ok}/{total} ({100*ok//total}%)")
    print(f"[RESULT] Fact map: {out_path}")


if __name__ == "__main__":
    main()
