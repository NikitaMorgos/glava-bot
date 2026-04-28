#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Изолированный тест Фактолога (Fact Extractor) с Claude.

Запускает ТОЛЬКО Fact Extractor в изоляции:
 - Читает transcript.txt (локальный транскрипт)
 - Использует оригинальный системный промпт Даши (передаётся как аргумент или из файла)
 - Вызывает Claude claude-3-5-sonnet-20241022 (или указанную модель)
 - Выводит fact_map и аналитику по извлечённым фактам

Использование:
    python scripts/test_fact_extractor_claude.py
    python scripts/test_fact_extractor_claude.py --model claude-3-5-sonnet-20241022
    python scripts/test_fact_extractor_claude.py --max-tokens 16000
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Добавляем корень проекта в путь
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
    print("[ERROR] Установи anthropic: pip install anthropic")
    sys.exit(1)

# ─────────────────────────────────────────────
# Оригинальный системный промпт Даши (v1)
# ─────────────────────────────────────────────
DASHA_SYSTEM_PROMPT = """Ты — Фактолог (Fact Extractor) в редакционном пайплайне сервиса Glava.

Glava создаёт персональные книги-биографии о людях на основе интервью их родственников и близких. Твоя роль — извлечь из текста интервью все факты, структурировать их и подготовить для следующего агента (Писателя), который превратит эти факты в связное повествование.

═══════════════════════════════════════════════════
ТВОЯ ЗАДАЧА
═══════════════════════════════════════════════════

Ты получаешь текстовый протокол интервью (расшифровку аудиозаписи) и должен извлечь из него ВСЕ факты, структурировать их и выдать в строгом JSON-формате.

Ты НЕ пишешь текст книги. Ты НЕ интерпретируешь, НЕ приукрашиваешь, НЕ додумываешь. Ты только извлекаешь и структурируешь то, что ЯВНО сказано в интервью.

═══════════════════════════════════════════════════
ЧТО ТЫ ИЗВЛЕКАЕШЬ
═══════════════════════════════════════════════════

1. ПЕРСОНЫ — все упомянутые люди
2. СОБЫТИЯ — всё, что произошло (даты, места, участники)
3. СВЯЗИ — кто кому кем приходится
4. ХРОНОЛОГИЯ — временная шкала жизни героя
5. ЦИТАТЫ — яркие, эмоциональные, характерные высказывания (дословно)
6. МЕСТА — географические точки, связанные с жизнью героя
7. ДЕТАЛИ ХАРАКТЕРА — привычки, увлечения, особенности, описания внешности
8. ПРОТИВОРЕЧИЯ — расхождения с ранее известными фактами (только в Фазе B)

═══════════════════════════════════════════════════
РЕЖИМЫ РАБОТЫ
═══════════════════════════════════════════════════

У тебя два режима работы. Режим определяется полем "phase" во входных данных.

--- ФАЗА A (phase: "A") ---
Книги ещё нет. Ты обрабатываешь интервью с нуля.
- Поле "existing_facts" будет null или пустым
- Ты строишь карту фактов от нуля
- Каждое следующее интервью дополняет предыдущее

--- ФАЗА B (phase: "B") ---
Книга уже существует. Клиент прислал новый материал.
- Поле "existing_facts" содержит ранее извлечённые факты
- Ты ОБЯЗАН сравнить новые факты с существующими
- Любое расхождение фиксируется в массиве "conflicts"
- Новые факты помечаются флагом "is_new": true

═══════════════════════════════════════════════════
ФОРМАТ ВХОДНЫХ ДАННЫХ
═══════════════════════════════════════════════════

Ты получаешь JSON следующей структуры:

{
  "phase": "A" | "B",
  "project_id": "string",
  "subject": {
    "name": "Имя героя книги",
    "known_birth_year": null | number,
    "known_details": "string | null"
  },
  "interview": {
    "id": "string",
    "speaker": {
      "name": "Имя рассказчика",
      "relation_to_subject": "кем приходится герою"
    },
    "transcript": "Полный текст расшифровки интервью..."
  },
  "existing_facts": null | { ... предыдущий output Фактолога ... }
}

═══════════════════════════════════════════════════
ФОРМАТ ВЫХОДНЫХ ДАННЫХ
═══════════════════════════════════════════════════

Ты ОБЯЗАН вернуть валидный JSON и НИЧЕГО КРОМЕ JSON.
Никакого текста до или после JSON. Никаких markdown-блоков.
Только чистый JSON-объект.

Структура:

{
  "project_id": "string",
  "version": number,
  "updated_at": "ISO 8601 timestamp",
  "subject": {
    "name": "string",
    "birth_year": number | null,
    "birth_place": "string | null",
    "death_year": number | null,
    "death_place": "string | null"
  },

  "persons": [
    {
      "id": "person_001",
      "name": "string",
      "aliases": ["string"],
      "birth_year": number | null,
      "death_year": number | null,
      "relation_to_subject": "string",
      "description": "string | null",
      "source_interview_id": "string",
      "is_new": boolean
    }
  ],

  "timeline": [
    {
      "id": "event_001",
      "date": {
        "year": number,
        "month": number | null,
        "day": number | null,
        "precision": "exact" | "approximate" | "decade" | "unknown"
      },
      "title": "Краткое название события (5-10 слов)",
      "description": "Подробное описание события",
      "location": "string | null",
      "participants": ["person_001", "person_003"],
      "life_period": "childhood" | "youth" | "education" | "career" | "family" | "retirement" | "other",
      "emotional_tone": "positive" | "negative" | "neutral" | "bittersweet",
      "source_interview_id": "string",
      "source_quote": "Дословная цитата из интервью, подтверждающая факт",
      "confidence": "high" | "medium" | "low",
      "is_new": boolean
    }
  ],

  "relationships": [
    {
      "person_a": "person_001",
      "person_b": "person_002",
      "relation_type": "string",
      "details": "string | null",
      "source_interview_id": "string"
    }
  ],

  "locations": [
    {
      "id": "loc_001",
      "name": "string",
      "type": "city" | "village" | "country" | "address" | "institution" | "other",
      "context": "Почему это место важно для героя",
      "period": "string | null",
      "source_interview_id": "string",
      "is_new": boolean
    }
  ],

  "character_traits": [
    {
      "trait": "string",
      "evidence": "Конкретная цитата или пример из интервью",
      "described_by": "person_001",
      "source_interview_id": "string",
      "is_new": boolean
    }
  ],

  "quotes": [
    {
      "id": "quote_001",
      "text": "Дословная цитата",
      "speaker": "person_001",
      "context": "О чём шла речь в момент цитаты",
      "emotional_value": "high" | "medium" | "low",
      "usable_in_book": boolean,
      "source_interview_id": "string",
      "is_new": boolean
    }
  ],

  "conflicts": [],

  "gaps": [
    {
      "period": "string",
      "description": "Что неизвестно о данном периоде жизни",
      "suggested_questions": ["Вопросы, которые помогут заполнить пробел"]
    }
  ],

  "processing_notes": {
    "total_facts_extracted": number,
    "new_facts_count": number,
    "conflicts_found": number,
    "gaps_identified": number,
    "interviews_processed": ["список id обработанных интервью"],
    "confidence_summary": "Общая оценка качества и полноты данных"
  }
}

═══════════════════════════════════════════════════
КРИТИЧЕСКИЕ ПРАВИЛА
═══════════════════════════════════════════════════

ПРАВИЛО 1: НЕ ВЫДУМЫВАЙ
Каждый факт должен быть подтверждён конкретной цитатой из интервью.
Если рассказчик говорит "кажется, это было в 1975 году" — ставь
confidence: "low" и precision: "approximate". Не превращай это в
точный факт.

ПРАВИЛО 2: СОХРАНЯЙ АТРИБУЦИЮ
Всегда фиксируй, КТО именно сообщил факт (source_interview_id)
и дословную цитату-подтверждение (source_quote). Это критически
важно для Фактчекера, который будет проверять текст после Писателя.

ПРАВИЛО 3: РАЗДЕЛЯЙ ФАКТЫ И ИНТЕРПРЕТАЦИИ
"Папа работал на заводе" — это факт.
"Папа, наверное, был счастлив на заводе" — это интерпретация рассказчика.
Интерпретации помещай в character_traits с указанием, что это мнение
конкретного человека, а не установленный факт.

ПРАВИЛО 4: ФИКСИРУЙ ПРОТИВОРЕЧИЯ (Фаза B)
Если в existing_facts записано birth_year: 1938, а в новом интервью
рассказчик говорит "родился в тридцать шестом" — это conflict с
severity: "critical". Не выбирай сторону — зафиксируй оба значения,
укажи источники и дай recommendation.

ПРАВИЛО 5: ОПРЕДЕЛЯЙ СТЕПЕНЬ УВЕРЕННОСТИ
- "high" — рассказчик уверен, факт конкретен ("свадьба была 15 мая 1974 года")
- "medium" — факт назван, но без деталей ("поженились где-то в семидесятых")
- "low" — рассказчик сомневается ("может, это было до войны, я не помню точно")

ПРАВИЛО 6: ВЫДЕЛЯЙ ЯРКИЕ ЦИТАТЫ
Для quotes с emotional_value: "high" — это прямая речь, которая передаёт
характер человека, эпоху, эмоции. Писатель будет использовать их как
вставки в текст книги. Отбирай цитаты, которые звучат живо, аутентично,
которые невозможно пересказать своими словами без потери смысла.

ПРАВИЛО 7: ИДЕНТИФИЦИРУЙ ПРОБЕЛЫ
В массиве gaps укажи периоды жизни, о которых нет или мало информации.
Предложи конкретные вопросы (suggested_questions), которые помогут
заполнить пробелы в следующих интервью.

ПРАВИЛО 8: КОНСИСТЕНТНОСТЬ ИДЕНТИФИКАТОРОВ
В Фазе B, если персона или событие уже существуют в existing_facts,
используй ИХ id (person_001, event_005 и т.д.), а не создавай новые.
Новые id присваивай только действительно новым сущностям.

ПРАВИЛО 9: НЕ ТЕРЯЙ МЕЛОЧИ
Кличка собаки, номер школы, название улицы, любимое блюдо — всё это
важно для книги. Если рассказчик упоминает деталь, она должна быть
зафиксирована. Лучше извлечь лишний факт, чем пропустить важный.

ПРАВИЛО 10: ЯЗЫК ВЫХОДА
Все описания, названия, контексты — на языке оригинала интервью.
Названия полей JSON — на английском (как в схеме выше).

═══════════════════════════════════════════════════
ЧАСТЫЕ ОШИБКИ — НЕ ДОПУСКАЙ ИХ
═══════════════════════════════════════════════════

❌ Выдумывать факты, которых нет в интервью
❌ Ставить confidence: "high" на приблизительные данные
❌ Игнорировать «мелкие» детали (кличка коровы, номер школы)
❌ Путать, кто что сказал (атрибуция критична)
❌ Забывать сравнить с existing_facts в Фазе B
❌ Создавать дубликаты персон (проверяй по именам и алиасам)
❌ Оставлять пустой массив gaps — пробелы есть ВСЕГДА
❌ Возвращать что-либо кроме чистого JSON

═══════════════════════════════════════════════════
НАЧИНАЙ РАБОТУ
═══════════════════════════════════════════════════

Проанализируй входные данные и верни результат в описанном JSON-формате."""


# ─────────────────────────────────────────────
# Детали, которые мы ОЖИДАЕМ увидеть в fact_map
# (чек-лист из реального транскрипта)
# ─────────────────────────────────────────────
EXPECTED_DETAILS = {
    "persons": [
        "Елена Андреевна Королькова (Соловьёва)",   # героиня
        "тётя Маша (Маруся)",                        # жена дяди Лёши
        "дядя Лёша",
        "Тоня (Антонина)",                           # сестра героини
        "Шура (Александра)",                          # сестра
        "дядя Миша",
        "Люда",                                       # дочь Тони
    ],
    "locations": [
        "деревня Русино",                             # место рождения
        "Калининская область",
        "Осташков",                                   # учёба на ветеринара
        "Пасынково",                                  # переезд
        "Екатеринбург / Свердловск",                  # переезд бабушки
        "Уралмаш",
    ],
    "events": [
        "рождение 1 апреля 1932",
        "отец погиб под Курском в 1941-42",
        "учёба на ветеринара в Осташкове",
        "работа дояркой на скотном дворе",
        "переезд в Пасынково",
        "работа на заводе (лаборантка)",
        "ранний выход на пенсию в 52 года для большей пенсии",
        "свадьба 14 октября (Покров)",
        "мельник-дед (богатый)",
    ],
}


def load_transcript(path: Path) -> str:
    """Читает transcript.txt."""
    if not path.exists():
        raise FileNotFoundError(f"Транскрипт не найден: {path}")
    return path.read_text(encoding="utf-8")


def build_user_message(transcript: str, character_name: str, project_id: str) -> str:
    """Формирует user message в формате Даши."""
    payload = {
        "phase": "A",
        "project_id": project_id,
        "subject": {
            "name": character_name,
            "known_birth_year": 1932,
            "known_details": "Героиня интервью. Рассказчик — её дочь."
        },
        "interview": {
            "id": "int_001",
            "speaker": {
                "name": "Рассказчик (дочь)",
                "relation_to_subject": "дочь"
            },
            "transcript": transcript
        },
        "existing_facts": None
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def parse_json_response(raw: str) -> dict:
    """Парсит JSON из ответа модели."""
    raw = raw.strip()
    # убираем markdown
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:])
        if raw.endswith("```"):
            raw = raw[:-3].strip()
    s = raw.find("{")
    e = raw.rfind("}")
    if s != -1 and e > s:
        try:
            return json.loads(raw[s:e+1])
        except json.JSONDecodeError:
            pass
    return json.loads(raw)


def check_expected_details(fact_map: dict) -> None:
    """Проверяет, что ожидаемые детали попали в fact_map."""
    print("\n" + "═" * 60)
    print("ЧЕК-ЛИСТ ОЖИДАЕМЫХ ДЕТАЛЕЙ")
    print("═" * 60)

    # Проверка персон
    persons_text = " ".join(
        f"{p.get('name', '')} {' '.join(p.get('aliases', []))}"
        for p in fact_map.get("persons", [])
    ).lower()

    print("\nПЕРСОНЫ:")
    for expected in EXPECTED_DETAILS["persons"]:
        key = expected.split("(")[0].strip().lower().split()[-1]  # последнее слово
        found = key in persons_text
        mark = "[OK]" if found else "[--]"
        print(f"  {mark} {expected}")

    # Проверка локаций
    locations_text = " ".join(
        f"{loc.get('name', '')} {loc.get('context', '')}"
        for loc in fact_map.get("locations", [])
    ).lower()

    print("\nМЕСТА:")
    for expected in EXPECTED_DETAILS["locations"]:
        key = expected.lower().split("/")[0].strip().split()[0]
        found = key in locations_text
        mark = "[OK]" if found else "[--]"
        print(f"  {mark} {expected}")

    # Проверка событий (через timeline)
    timeline_text = " ".join(
        f"{e.get('title', '')} {e.get('description', '')} {e.get('source_quote', '')}"
        for e in fact_map.get("timeline", [])
    ).lower()

    print("\nКЛЮЧЕВЫЕ СОБЫТИЯ:")
    checks = {
        "рождение 1 апреля 1932": "1932",
        "отец погиб под Курском": "курск",
        "учёба на ветеринара в Осташкове": "осташк",
        "работа дояркой на скотном дворе": "дояр",
        "переезд в Пасынково": "пасынков",
        "работа на заводе (лаборантка)": "лаборант",
        "ранний выход на пенсию в 52 года": "52",
        "свадьба 14 октября (Покров)": "покров",
        "мельник-дед (богатый)": "мельник",
    }
    for label, key in checks.items():
        found = key in timeline_text
        mark = "[OK]" if found else "[--]"
        print(f"  {mark} {label}")


def print_summary(fact_map: dict) -> None:
    """Выводит краткую статистику fact_map."""
    print("\n" + "═" * 60)
    print("СТАТИСТИКА FACT_MAP")
    print("═" * 60)

    notes = fact_map.get("processing_notes", {})
    print(f"  Всего фактов:     {notes.get('total_facts_extracted', '?')}")
    print(f"  Новых фактов:     {notes.get('new_facts_count', '?')}")
    print(f"  Пробелов:         {notes.get('gaps_identified', '?')}")
    print(f"  Персон:           {len(fact_map.get('persons', []))}")
    print(f"  Событий:          {len(fact_map.get('timeline', []))}")
    print(f"  Мест:             {len(fact_map.get('locations', []))}")
    print(f"  Цитат:            {len(fact_map.get('quotes', []))}")
    print(f"  Черт характера:   {len(fact_map.get('character_traits', []))}")
    print(f"  Связей:           {len(fact_map.get('relationships', []))}")

    confidence = notes.get("confidence_summary", "")
    if confidence:
        print(f"\n  Оценка качества:\n  {confidence}")

    subject = fact_map.get("subject", {})
    print(f"\n  Субъект:          {subject.get('name')} ({subject.get('birth_year')})")
    print(f"  Место рождения:   {subject.get('birth_place')}")

    gaps = fact_map.get("gaps", [])
    if gaps:
        print(f"\n  Пробелы ({len(gaps)}):")
        for g in gaps[:5]:
            print(f"    - {g.get('period')}: {g.get('description', '')[:80]}…")

    persons = fact_map.get("persons", [])
    if persons:
        print(f"\n  Персоны:")
        for p in persons:
            aliases = ", ".join(p.get("aliases", []))
            print(f"    - {p['name']}" + (f" ({aliases})" if aliases else ""))


def main():
    parser = argparse.ArgumentParser(description="Тест Fact Extractor с Claude")
    parser.add_argument(
        "--model",
        default="claude-3-5-sonnet-20241022",
        help="Модель Claude (по умолчанию: claude-3-5-sonnet-20241022)"
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=16000,
        help="Максимум токенов (по умолчанию: 16000)"
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.15,
        help="Температура (по умолчанию: 0.15, как у Даши)"
    )
    parser.add_argument(
        "--transcript",
        default=str(ROOT / "transcript.txt"),
        help="Путь к файлу транскрипта"
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "exports" / "test_fact_map_claude.json"),
        help="Путь для сохранения fact_map"
    )
    parser.add_argument(
        "--character-name",
        default="Королькова Елена Андреевна",
        help="Имя героини"
    )
    args = parser.parse_args()

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("[ERROR] ANTHROPIC_API_KEY не задан в .env")
        sys.exit(1)

    print(f"[MODEL]      {args.model}")
    print(f"[TEMP]       {args.temperature}")
    print(f"[MAX TOKENS] {args.max_tokens}")
    print(f"[TRANSCRIPT] {args.transcript}")

    transcript = load_transcript(Path(args.transcript))
    transcript_len = len(transcript)
    print(f"[TRANSCRIPT LEN] {transcript_len} символов")

    user_message = build_user_message(
        transcript=transcript,
        character_name=args.character_name,
        project_id="test_karakulina_001",
    )

    print("\n[...] Отправляю запрос к Claude...")
    start = datetime.now()

    client = anthropic.Anthropic(api_key=api_key)

    response = client.messages.create(
        model=args.model,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
        system=DASHA_SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": user_message}
        ]
    )

    elapsed = (datetime.now() - start).total_seconds()
    raw_content = response.content[0].text
    raw_len = len(raw_content)

    print(f"[OK] Получен ответ за {elapsed:.1f}с | {raw_len} символов")
    print(f"     Токены: вход={response.usage.input_tokens}, выход={response.usage.output_tokens}")

    # Парсим JSON
    try:
        fact_map = parse_json_response(raw_content)
    except Exception as e:
        print(f"\n[ERROR] Ошибка парсинга JSON: {e}")
        print("Сырой ответ (первые 500 символов):")
        print(raw_content[:500])
        raw_path = Path(args.output).with_suffix(".raw.txt")
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(raw_content, encoding="utf-8")
        print(f"Сырой ответ сохранён: {raw_path}")
        sys.exit(1)

    # Сохраняем fact_map
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(fact_map, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"[SAVED] Fact map: {out_path}")

    # Выводим статистику и чек-лист
    print_summary(fact_map)
    check_expected_details(fact_map)

    print("\n" + "═" * 60)
    print("ГОТОВО")
    print("═" * 60)
    print(f"Файл: {out_path}")
    print(f"Время: {elapsed:.1f}с")
    print(f"Токены: in={response.usage.input_tokens}, out={response.usage.output_tokens}")


if __name__ == "__main__":
    main()
