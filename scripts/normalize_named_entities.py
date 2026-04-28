#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
normalize_named_entities.py — Name Normalizer (задача 014).

Детерминированная нормализация имён и топонимов в fact_map:
  1. Для каждой записи persons[] и locations[] генерирует варианты написания
  2. Ищет позиции всех вариантов в транскрипте
  3. Сливает записи с пересекающимися позициями (overlap ≥ MERGE_THRESHOLD)
  4. Обновляет все ID-ссылки по всему fact_map

Использование:
  python scripts/normalize_named_entities.py --fact-map path/fact_map.json \\
      --transcript path/cleaned.txt --output path/normalized.json
"""

import argparse
import copy
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# ─────────────────────────────────────────────────────────────────
# Константы
# ─────────────────────────────────────────────────────────────────

MERGE_THRESHOLD = 0.30      # мин. доля пересечения позиций для слияния
POSITION_WINDOW = 300       # ±N символов для сравнения позиций
MIN_NAME_LEN = 3            # не ищем по частям короче N символов

# Исторические и политические деятели — не добавляем в persons как персонажей биографии
HISTORICAL_BLOCKLIST = {
    "сталин", "горбачёв", "горбачев", "ленин", "хрущёв", "хрущев", "брежнев",
    "гитлер", "жуков", "путин", "ельцин", "андропов", "черненко", "маленков",
    "троцкий", "берия", "дзержинский", "молотов", "калинин", "буденный",
    "рокоссовский", "конев", "ворошилов", "тимошенко", "кириленко",
    "рейган", "черчилль", "черчилл", "де голль", "де-голль", "тито",
    "мао", "мао цзэдун", "чан кайши",
}

# Словарь диминутивов (имя → множество форм)
DIMINUTIVES: dict[str, set[str]] = {
    "владимир": {"владимир", "вова", "вовочка", "володя"},
    "александр": {"александр", "саша", "саня", "шура", "алекс"},
    "татьяна":   {"татьяна", "таня", "танечка"},
    "валерий":   {"валерий", "валера", "валерка"},
    "валентина": {"валентина", "валя", "валечка"},
    "дмитрий":   {"дмитрий", "дима", "димка", "митя"},
    "никита":    {"никита", "никиша"},
    "дарья":     {"дарья", "даша", "дашенька"},
    "александра": {"александра", "шура", "саша"},
    "николай":   {"николай", "коля", "николаша"},
    "анатолий":  {"анатолий", "толя", "толик"},
    "виктор":    {"виктор", "витя", "витек"},
    "михаил":    {"михаил", "миша", "мишка"},
    "наталья":   {"наталья", "наташа", "ната"},
    "мария":     {"мария", "маша", "маня"},
    "пелагея":   {"пелагея", "поля", "полина"},
    "иван":      {"иван", "ваня", "ванечка"},
}


# ─────────────────────────────────────────────────────────────────
# Утилиты
# ─────────────────────────────────────────────────────────────────

def _is_historical(name: str) -> bool:
    """Проверяет, является ли имя историческим деятелем из blocklist."""
    name_lower = name.lower().strip()
    for blocked in HISTORICAL_BLOCKLIST:
        if blocked in name_lower or name_lower in blocked:
            return True
    return False


def _generate_name_variants(name: str, aliases: list[str], asr_variants: list[str]) -> set[str]:
    """
    Генерирует множество вариантов написания для поиска в транскрипте.
    Включает: каноническое имя, aliases, asr_variants, перестановки, части, диминутивы.
    """
    variants: set[str] = set()
    all_forms = [name] + list(aliases or []) + list(asr_variants or [])

    for form in all_forms:
        if not form:
            continue
        form_s = form.strip()
        variants.add(form_s.lower())

        # Перестановка «Фамилия Имя» ↔ «Имя Фамилия»
        parts = form_s.split()
        if len(parts) == 2:
            variants.add(f"{parts[1]} {parts[0]}".lower())
        elif len(parts) == 3:
            # Фамилия Имя Отчество → Имя Отчество Фамилия
            variants.add(f"{parts[1]} {parts[2]} {parts[0]}".lower())

        # Отдельные части (только если достаточно длинные)
        for part in parts:
            if len(part) >= MIN_NAME_LEN:
                part_lower = part.lower()
                variants.add(part_lower)
                # Диминутивы
                for canonical, forms in DIMINUTIVES.items():
                    if part_lower in forms or part_lower == canonical:
                        variants.update(forms)

    # Убираем слишком короткие и пустые
    return {v for v in variants if v and len(v) >= MIN_NAME_LEN}


def _find_positions(text: str, variant: str) -> list[int]:
    """
    Находит все позиции вхождения variant в text (без учёта регистра).
    Возвращает список начальных позиций.
    """
    text_lower = text.lower()
    variant_lower = variant.lower()
    positions = []
    start = 0
    while True:
        pos = text_lower.find(variant_lower, start)
        if pos == -1:
            break
        positions.append(pos)
        start = pos + len(variant_lower)
    return positions


def _build_position_index(text: str, variants: set[str]) -> list[int]:
    """Возвращает объединённый список всех позиций для всех вариантов (дедуплицированный)."""
    all_positions: set[int] = set()
    for v in variants:
        for pos in _find_positions(text, v):
            all_positions.add(pos)
    return sorted(all_positions)


def _positions_overlap_ratio(pos_a: list[int], pos_b: list[int], window: int = POSITION_WINDOW) -> float:
    """
    Вычисляет долю позиций из pos_a, у которых есть «сосед» из pos_b в пределах window.
    Симметрично: берём max(len_a, len_b) как знаменатель.
    """
    if not pos_a or not pos_b:
        return 0.0
    matched = 0
    for pa in pos_a:
        for pb in pos_b:
            if abs(pa - pb) <= window:
                matched += 1
                break
    return matched / max(len(pos_a), len(pos_b))


def _pick_canonical(record_a: dict, record_b: dict) -> dict:
    """
    Выбирает каноническую запись из двух кандидатов.
    Предпочитает: более длинное имя (полное имя > первое имя), более высокий confidence.
    """
    name_a = record_a.get("name", "")
    name_b = record_b.get("name", "")
    conf_order = {"high": 2, "medium": 1, "low": 0}
    ca = conf_order.get(record_a.get("confidence", "low"), 0)
    cb = conf_order.get(record_b.get("confidence", "low"), 0)
    if len(name_a) >= len(name_b) and ca >= cb:
        return record_a, record_b
    if len(name_b) > len(name_a) or cb > ca:
        return record_b, record_a
    return record_a, record_b


def _merge_person_records(canonical: dict, duplicate: dict) -> dict:
    """Сливает duplicate в canonical: объединяет aliases, asr_variants, берёт лучшие поля."""
    result = copy.deepcopy(canonical)
    dup_name = duplicate.get("name", "")
    if dup_name and dup_name.lower() != result.get("name", "").lower():
        result.setdefault("aliases", [])
        if dup_name not in result["aliases"]:
            result["aliases"].append(dup_name)

    for field in ("aliases", "asr_variants"):
        canon_list = result.get(field) or []
        dup_list = duplicate.get(field) or []
        merged = list(dict.fromkeys(canon_list + dup_list))  # порядок сохраняется, дублей нет
        if merged:
            result[field] = merged

    # Берём description из duplicate если у canonical нет
    if not result.get("description") and duplicate.get("description"):
        result["description"] = duplicate["description"]

    # Если duplicate более достоверный по confidence — поднимаем
    conf_order = {"high": 2, "medium": 1, "low": 0}
    if conf_order.get(duplicate.get("confidence", "low"), 0) > conf_order.get(result.get("confidence", "low"), 0):
        result["confidence"] = duplicate["confidence"]

    return result


def _remap_ids_in_fact_map(fact_map: dict, id_remap: dict[str, str]) -> dict:
    """
    Заменяет все вхождения старых ID на новые по всему fact_map.
    Затрагивает: timeline[].participants, relationships[], character_traits[].described_by,
    quotes[].speaker, conflicts[].parties[], gaps[].related_persons[].

    Если id_remap[old_id] == "" — ID удаляется из списков (используется для исторических фигур).
    """
    if not id_remap:
        return fact_map

    fm = copy.deepcopy(fact_map)

    def _remap_list(lst: list[str]) -> list[str]:
        """Ремапит список ID: заменяет старые на новые, удаляет если новое == ""."""
        result = []
        for pid in lst:
            mapped = id_remap.get(pid, pid)
            if mapped:  # пустая строка → удалить из списка
                result.append(mapped)
        return result

    # timeline.participants
    for event in fm.get("timeline", []):
        event["participants"] = _remap_list(event.get("participants", []))

    # relationships
    for rel in fm.get("relationships", []):
        rel["person_a"] = id_remap.get(rel.get("person_a", ""), rel.get("person_a", ""))
        rel["person_b"] = id_remap.get(rel.get("person_b", ""), rel.get("person_b", ""))

    # character_traits.described_by
    for trait in fm.get("character_traits", []):
        trait["described_by"] = id_remap.get(trait.get("described_by", ""), trait.get("described_by", ""))

    # quotes.speaker
    for quote in fm.get("quotes", []):
        quote["speaker"] = id_remap.get(quote.get("speaker", ""), quote.get("speaker", ""))

    # conflicts[].parties[]
    for conflict in fm.get("conflicts", []):
        conflict["parties"] = _remap_list(conflict.get("parties", []))

    # gaps[].related_persons[]
    for gap in fm.get("gaps", []):
        gap["related_persons"] = _remap_list(gap.get("related_persons", []))

    return fm


def validate_fact_map_integrity(fact_map: dict) -> list[str]:
    """
    Проверяет целостность ссылок в fact_map после нормализации.
    Возвращает список ошибок (пустой если всё ОК).
    Проверяет: timeline[], relationships[], character_traits[], quotes[],
               conflicts[], gaps[].
    """
    errors = []
    person_ids = {p["id"] for p in fact_map.get("persons", []) if p.get("id")}
    narrator_ids = {"narrator_001", "narrator_002", "narrator_003"}
    valid_ids = person_ids | narrator_ids

    for event in fact_map.get("timeline", []):
        for pid in event.get("participants", []):
            if pid and pid not in valid_ids:
                errors.append(f"timeline[{event.get('id')}].participants: неизвестный id '{pid}'")

    for rel in fact_map.get("relationships", []):
        for field in ("person_a", "person_b"):
            pid = rel.get(field, "")
            if pid and pid not in valid_ids:
                errors.append(f"relationships: неизвестный {field}='{pid}'")

    for trait in fact_map.get("character_traits", []):
        pid = trait.get("described_by", "")
        if pid and pid not in valid_ids:
            errors.append(f"character_traits['{trait.get('trait','')}'].described_by: '{pid}'")

    for quote in fact_map.get("quotes", []):
        pid = quote.get("speaker", "")
        if pid and pid not in valid_ids:
            errors.append(f"quotes[{quote.get('id')}].speaker: '{pid}'")

    for conflict in fact_map.get("conflicts", []):
        for pid in conflict.get("parties", []):
            if pid and pid not in valid_ids:
                errors.append(f"conflicts[{conflict.get('id', '?')}].parties: неизвестный id '{pid}'")

    for gap in fact_map.get("gaps", []):
        for pid in gap.get("related_persons", []):
            if pid and pid not in valid_ids:
                errors.append(f"gaps[{gap.get('id', '?')}].related_persons: неизвестный id '{pid}'")

    return errors


# ─────────────────────────────────────────────────────────────────
# Основная функция
# ─────────────────────────────────────────────────────────────────

def normalize_named_entities(fact_map: dict, transcript: str) -> tuple[dict, list[dict]]:
    """
    Нормализует persons[] и locations[] в fact_map.

    Алгоритм:
      0. Фильтрует исторических деятелей из persons[] (blocklist + _is_historical)
      1. Для каждой записи генерирует варианты написания
      2. Находит позиции в транскрипте
      3. Ищет пары с пересечением ≥ MERGE_THRESHOLD
      4. Сливает пары, обновляет ID-ссылки
      5. Валидирует целостность

    Возвращает:
      (normalized_fact_map, merged_pairs_log)
        merged_pairs_log — список {"canonical": str, "merged": str, "overlap": float, "field": str}
    """
    fm = copy.deepcopy(fact_map)
    merged_pairs_log: list[dict] = []

    # ── Шаг 0: удаляем исторических деятелей из persons[] ──────────────────────
    # Защита от LLM-ошибок: Auditor иногда добавляет исторических фигур в auto_enrich.
    # Промпт фильтрует, но LLM нестабилен — код является второй линией защиты.
    # Ссылки на удалённые ID: убираем из всех списков (participants, parties, etc.)
    # через _remap_ids_in_fact_map с пустой строкой как целевым значением (→ удалить из списка).
    historical_remap: dict[str, str] = {}
    filtered_persons = []
    for person in fm.get("persons", []):
        name = person.get("name", "")
        if _is_historical(name):
            pid = person.get("id") or name
            historical_remap[pid] = ""  # пустая строка → удалить из списков
            print(f"[NAME NORMALIZER] filtered: historical figure '{name}' (id={pid})")
        else:
            filtered_persons.append(person)

    if historical_remap:
        fm["persons"] = filtered_persons
        fm = _remap_ids_in_fact_map(fm, historical_remap)
        print(f"[NAME NORMALIZER] удалено {len(historical_remap)} исторических деятелей из persons[]")

    # ── Шаги 1–4: нормализация дублей ──────────────────────────────────────────
    for field, entity_key in [("persons", "name"), ("locations", "name")]:
        entities = fm.get(field, [])
        if len(entities) < 2:
            continue

        # Шаг 1: строим индекс позиций для каждой записи
        position_index: dict[str, list[int]] = {}
        for entity in entities:
            eid = entity.get("id") or entity.get("name", "")
            variants = _generate_name_variants(
                entity.get("name", ""),
                entity.get("aliases", []),
                entity.get("asr_variants", []),
            )
            positions = _build_position_index(transcript, variants)
            position_index[eid] = positions

        # Шаг 2: ищем пары с перекрытием ≥ MERGE_THRESHOLD
        merged_ids: dict[str, str] = {}  # старый_id → канонический_id
        id_to_entity: dict[str, dict] = {
            (e.get("id") or e.get("name", "")): e for e in entities
        }

        entity_ids = list(id_to_entity.keys())
        for i in range(len(entity_ids)):
            for j in range(i + 1, len(entity_ids)):
                id_a = entity_ids[i]
                id_b = entity_ids[j]

                # Если уже слиты в один кластер — пропускаем
                canon_a = merged_ids.get(id_a, id_a)
                canon_b = merged_ids.get(id_b, id_b)
                if canon_a == canon_b:
                    continue

                pos_a = position_index.get(id_a, [])
                pos_b = position_index.get(id_b, [])

                # Записи без позиций в транскрипте — не сливаем
                if not pos_a or not pos_b:
                    continue

                overlap = _positions_overlap_ratio(pos_a, pos_b)
                if overlap < MERGE_THRESHOLD:
                    continue

                # Определяем канон
                entity_a = id_to_entity[id_a]
                entity_b = id_to_entity[id_b]
                canonical, duplicate = _pick_canonical(entity_a, entity_b)
                canonical_id = canonical.get("id") or canonical.get("name", "")
                duplicate_id = duplicate.get("id") or duplicate.get("name", "")

                merged_pairs_log.append({
                    "field": field,
                    "canonical": canonical.get("name", ""),
                    "canonical_id": canonical_id,
                    "merged": duplicate.get("name", ""),
                    "merged_id": duplicate_id,
                    "overlap": round(overlap, 3),
                })

                merged_ids[duplicate_id] = canonical_id
                id_to_entity[canonical_id] = _merge_person_records(
                    id_to_entity[canonical_id], id_to_entity[duplicate_id]
                )

        # Шаг 3: убираем дубли из списка, применяем слияния
        if merged_ids:
            removed_ids = set(merged_ids.keys())
            fm[field] = [
                id_to_entity.get(eid, e)
                for eid, e in id_to_entity.items()
                if eid not in removed_ids
            ]
            # Обновляем все ID-ссылки
            fm = _remap_ids_in_fact_map(fm, merged_ids)
            print(f"[NAME NORMALIZER] {field}: слито {len(merged_ids)} дублей")

    # Шаг 4: валидация
    errors = validate_fact_map_integrity(fm)
    if errors:
        print(f"[NAME NORMALIZER] ⚠️  Ошибки целостности после нормализации ({len(errors)}):")
        for err in errors[:10]:
            print(f"  - {err}")
    else:
        print("[NAME NORMALIZER] ✅ Целостность fact_map подтверждена")

    return fm, merged_pairs_log


# ─────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Name Normalizer — нормализация имён в fact_map")
    parser.add_argument("--fact-map", required=True, help="Путь к fact_map.json")
    parser.add_argument("--transcript", required=True, help="Путь к cleaned_transcript.txt")
    parser.add_argument("--output", default=None, help="Путь для сохранения (по умолчанию — перезапись)")
    parser.add_argument("--log", default=None, help="Путь для сохранения лога слияний (JSON)")
    args = parser.parse_args()

    fact_map_path = Path(args.fact_map)
    transcript_path = Path(args.transcript)
    output_path = Path(args.output) if args.output else fact_map_path
    log_path = Path(args.log) if args.log else None

    if not fact_map_path.exists():
        print(f"[ERROR] Файл не найден: {fact_map_path}"); sys.exit(1)
    if not transcript_path.exists():
        print(f"[ERROR] Файл не найден: {transcript_path}"); sys.exit(1)

    fact_map = json.loads(fact_map_path.read_text(encoding="utf-8"))
    transcript = transcript_path.read_text(encoding="utf-8")

    persons_before = len(fact_map.get("persons", []))
    locs_before = len(fact_map.get("locations", []))

    print(f"[NAME NORMALIZER] Входной fact_map: {persons_before} персон, {locs_before} локаций")
    print(f"[NAME NORMALIZER] Транскрипт: {len(transcript):,} символов")

    normalized, log = normalize_named_entities(fact_map, transcript)

    persons_after = len(normalized.get("persons", []))
    locs_after = len(normalized.get("locations", []))
    print(f"[NAME NORMALIZER] После нормализации: {persons_after} персон (-{persons_before - persons_after}), "
          f"{locs_after} локаций (-{locs_before - locs_after})")

    output_path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[SAVED] {output_path}")

    if log_path and log:
        log_path.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[SAVED] {log_path} ({len(log)} пар слито)")

    if log:
        print("\nСлитые пары:")
        for pair in log:
            print(f"  [{pair['field']}] '{pair['merged']}' → '{pair['canonical']}' "
                  f"(overlap={pair['overlap']})")


if __name__ == "__main__":
    main()
