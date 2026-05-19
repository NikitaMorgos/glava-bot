#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pipeline_utils.py — Общий модуль пайплайна Glava (Stage 1).

Загружает конфиг и промпты из prompts/pipeline_config.json.
Все скрипты тестирования используют этот модуль — изменение
конфига или промпта сразу применяется везде.

Структура prompts/:
  pipeline_config.json       — модели, max_tokens, имена промптов
  01_cleaner_v1.md           — системный промпт Cleaner'а
  02_fact_extractor_v3.1.md  — системный промпт Фактолога (текущая версия)
"""

import json
import hashlib
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROMPTS_DIR = ROOT / "prompts"
CONFIG_FILE = PROMPTS_DIR / "pipeline_config.json"

# Импортируем checkpoint_utils если доступен (graceful degradation)
try:
    from checkpoint_utils import save_checkpoint as _save_checkpoint
    _CHECKPOINTS_ENABLED = True
except ImportError:
    _CHECKPOINTS_ENABLED = False

def _auto_checkpoint(project: str, stage: str, content: dict,
                     transcript_text: str = None, source_file: str = None):
    """Авто-сохраняет результат этапа в checkpoint. Не падает при ошибке."""
    if not _CHECKPOINTS_ENABLED or not project:
        return
    try:
        _save_checkpoint(project, stage, content,
                         transcript_text=transcript_text,
                         source_file=source_file)
    except Exception as e:
        print(f"[CHECKPOINT] ⚠️  Не удалось сохранить {project}/{stage}: {e}")


# ─────────────────────────────────────────────────────────────────
# Загрузка конфига и промптов
# ─────────────────────────────────────────────────────────────────


def prepare_book_for_layout(book: dict) -> dict:
    """Создаёт пронумерованные абзацы paragraphs[] из полного text content для Layout Designer.

    Всегда разбивает chapter.content по двойным переносам строки.
    Игнорирует существующие paragraphs[] — они могут быть короткими резюме из
    предыдущих стадий пайплайна (пруфридер, факт-чекер), а не полным текстом.
    Layout Designer должен получать ПОЛНЫЙ текст для корректного распределения
    по страницам и последующего lookup по paragraph_id в pdf_renderer.

    Присваивает id p1, p2, p3...

    Подзаголовки в legacy format (## Текст, ### Текст) автоматически нормализуются
    в структурный тип `subheading`. Лог-предупреждение: GW должен генерировать
    {"type": "subheading"} напрямую, не markdown-маркеры.
    """
    import copy
    import re as _re
    book = copy.deepcopy(book)
    for ch in book.get("chapters", []):
        content = ch.get("content") or ""
        paras = [p.strip() for p in content.split("\n\n") if p.strip()]
        if paras:
            items = []
            for i, p in enumerate(paras):
                pid = f"p{i + 1}"
                m = _re.match(r'^#{2,3}\s+(.+)$', p.strip())
                if m:
                    heading_text = m.group(1).strip()
                    print(
                        f"[BOOK-NORMALIZE] auto-detected subheading in {ch.get('id','?')}/{pid}: "
                        f'"{heading_text[:60]}" (legacy ## / ### → subheading). '
                        f"GW должен эмитировать {{\"type\": \"subheading\"}} явно."
                    )
                    items.append({"id": pid, "type": "subheading", "text": heading_text})
                else:
                    items.append({"id": pid, "text": p})
            ch["paragraphs"] = items
        elif not ch.get("paragraphs"):
            ch["paragraphs"] = []
    return book


# ─────────────────────────────────────────────────────────────────
# Task 027: bio_data completeness enforcement (post-Stage-2)
# ─────────────────────────────────────────────────────────────────

_FAMILY_RELATIONS = {
    "муж", "жена", "сын", "дочь", "отец", "мать", "брат", "сестра",
    "дедушка", "бабушка", "внук", "внучка", "дядя", "тётя",
    "племянник", "племянница", "свёкор", "свекровь", "зять", "невестка",
    "золовка", "шурин", "деверь",
}

_FAMILY_NAME_MARKERS = {
    "тётя", "дядя", "брат", "сестра", "дедушка", "бабушка",
    "мама", "папа", "внук", "внучка", "племянник", "племянница",
}

_UNKNOWN_RELATIONS = {"", "?", "неизвестно", "unknown", "н/а", "н.а.", "-"}


def _is_family_person(person: dict) -> bool:
    """True if this person is a family member (by relation field or name markers).

    Checks both 'relation_to_subject' (fact_map Stage 1 format) and legacy 'relation' key.
    If relation is filled and not in _FAMILY_RELATIONS, name markers are NOT checked
    (prevents false positives like neighbour 'тётя Маша' with relation='соседка').
    """
    relation = (
        person.get("relation_to_subject") or person.get("relation") or ""
    ).strip().lower()
    name = (person.get("name") or "").strip().lower()

    if relation and relation not in _UNKNOWN_RELATIONS:
        for frel in _FAMILY_RELATIONS:
            if frel in relation:
                return True
        # relation is filled but not a family relation — do not fall through to name markers
        return False

    # relation unknown/empty — fall back to name markers
    for marker in _FAMILY_NAME_MARKERS:
        if marker in name:
            return True

    return False


def _name_in_family_entries(name: str, family_entries: list) -> bool:
    """Check if person name (or any significant part) appears in existing bio_data.family."""
    name_norm = name.strip().lower()
    if not name_norm:
        return False
    name_parts = [p for p in name_norm.split() if len(p) >= 4]
    for entry in family_entries:
        entry_text = ((entry.get("value") or "") + " " + (entry.get("label") or "")).lower()
        if name_norm in entry_text:
            return True
        for part in name_parts:
            if part in entry_text:
                return True
    return False


def enforce_bio_data_completeness(book_final: dict, fact_map: dict, strict: bool = False) -> dict:
    """Task 027: ensure bio_data.family in ch_01 covers all family persons from fact_map.

    Called after Stage 2 (Ghostwriter). Checks that every family person from fact_map
    is mentioned somewhere in bio_data.family.

    Default: auto-fill missing entries with source="auto-filled".
    strict=True: raise RuntimeError instead of auto-filling (for prod override).
    """
    import copy
    book_final = copy.deepcopy(book_final)

    persons = fact_map.get("persons", [])
    if not persons:
        print("[BIO-COMPLETENESS] fact_map.persons пустой — пропускаем проверку.")
        return book_final

    chapters = book_final.get("chapters", [])
    ch01 = next((ch for ch in chapters if ch.get("id") == "ch_01"), None)
    if ch01 is None:
        print("[BIO-COMPLETENESS] WARN: ch_01 not found in book_final - skipping.")
        return book_final

    bio_data = ch01.get("bio_data")
    if bio_data is None:
        print("[BIO-COMPLETENESS] WARN: bio_data absent in ch_01 - creating empty.")
        bio_data = {}
        ch01["bio_data"] = bio_data

    family = bio_data.get("family")
    if family is None:
        family = []
        bio_data["family"] = family

    family_persons = [p for p in persons if _is_family_person(p)]
    if not family_persons:
        print("[BIO-COMPLETENESS] Семейных персон в fact_map не найдено — пропускаем.")
        return book_final

    missing = [
        p for p in family_persons
        if (p.get("name") or "").strip()
        and not _name_in_family_entries((p.get("name") or "").strip(), family)
    ]

    if not missing:
        print(
            f"[BIO-COMPLETENESS] OK bio_data.family: {len(family)} entries, "
            f"all {len(family_persons)} family persons from fact_map mentioned."
        )
        return book_final

    missing_names = [p.get("name", "?") for p in missing]

    if strict:
        raise RuntimeError(
            f"[BIO-COMPLETENESS] STRICT: в bio_data.family не упомянуты {len(missing)} персон: "
            f"{missing_names}. Исправьте Ghostwriter или запустите без --strict-bio-data."
        )

    for person in missing:
        name = (person.get("name") or "").strip()
        relation = (
            person.get("relation_to_subject") or person.get("relation") or ""
        ).strip()
        label = relation if relation and relation not in _UNKNOWN_RELATIONS else "родственник"
        confidence = (person.get("confidence") or "").lower()
        entry: dict = {"label": label, "value": name, "source": "auto-filled"}
        if confidence == "low":
            entry["needs_verification"] = True
        family.append(entry)

    print(
        f"[BIO-COMPLETENESS] auto-filled {len(missing)} персон в bio_data.family: "
        f"{missing_names}"
    )
    return book_final


# ─────────────────────────────────────────────────────────────────
# Task 042: Subject age enrichment
# ─────────────────────────────────────────────────────────────────

def enrich_timeline_with_subject_age(fact_map: dict) -> dict:
    """Task 042: добавить subject_age к каждому event в fact_map.timeline.

    subject_age = year − birth_year.
    Для precision="decade": mid-decade (1960 → 1965).
    Идемпотентна: пропускает уже обогащённые events.
    Персоны с отсутствующим birth_year → предупреждение, fact_map без изменений.
    """
    import copy
    fact_map = copy.deepcopy(fact_map)

    birth_year = (fact_map.get("subject") or {}).get("birth_year")
    if birth_year is None:
        print("[AGE-ENRICH] subject.birth_year отсутствует — пропускаем обогащение возрастом.")
        return fact_map

    timeline = fact_map.get("timeline", [])
    enriched = 0
    skipped = 0

    for event in timeline:
        if "subject_age" in event:
            continue  # idempotent

        date = event.get("date") or {}
        year = date.get("year")
        precision = (date.get("precision") or "").lower()

        if year is None:
            skipped += 1
            continue

        if precision == "decade":
            event_year = year + 5  # середина декады: 1960 → 1965
        else:
            event_year = year

        event["subject_age"] = event_year - birth_year
        enriched += 1

    print(
        f"[AGE-ENRICH] subject_age добавлен для {enriched} events; "
        f"пропущено {skipped} (год не задан)."
    )
    return fact_map


# ─────────────────────────────────────────────────────────────────
# Task 040: ASR normalize gazeteer
# ─────────────────────────────────────────────────────────────────

_TOPO_SKIP_FIELDS = frozenset({
    "source_quote", "evidence", "transcript_quote", "asr_variants", "reasoning",
})


def normalize_topo_via_gazeteer(text: str, gazeteer: dict) -> tuple:
    """Task 040: нормализация ASR-искажений топонимов по словарю gazeteer.

    Case-preserving, word-boundary aware, idempotent.
    Не трогает source_quote / evidence / transcript_quote (внешняя логика caller'а).
    Returns (normalized_text, list_of_replacements).
    """
    topo_corrections = gazeteer.get("topo_corrections", {})
    replacements = []

    for wrong, correct in topo_corrections.items():
        pattern = r'\b' + re.escape(wrong) + r'\b'

        def _make_replacer(c: str):
            def _replacer(m: re.Match) -> str:
                orig = m.group(0)
                if orig.isupper():
                    return c.upper()
                if orig[0].isupper():
                    return c[0].upper() + c[1:]
                return c.lower()
            return _replacer

        new_text, count = re.subn(pattern, _make_replacer(correct), text, flags=re.IGNORECASE)
        if count > 0:
            replacements.append({"wrong": wrong, "correct": correct, "count": count})
            text = new_text

    return text, replacements


def _normalize_topo_value(value: object, gazeteer: dict, acc: list) -> object:
    """Рекурсивно нормализует строки в dict/list, пропуская protected поля."""
    if isinstance(value, str):
        normalized, reps = normalize_topo_via_gazeteer(value, gazeteer)
        acc.extend(reps)
        return normalized
    if isinstance(value, list):
        return [_normalize_topo_value(item, gazeteer, acc) for item in value]
    if isinstance(value, dict):
        return {
            k: (v if k in _TOPO_SKIP_FIELDS else _normalize_topo_value(v, gazeteer, acc))
            for k, v in value.items()
        }
    return value


def normalize_fact_map_topo(fact_map: dict, gazeteer: dict) -> tuple:
    """Task 040: применить gazeteer normalize к fact_map (кроме protected полей).

    Returns (normalized_fact_map, replacements_list).
    """
    import copy
    fact_map = copy.deepcopy(fact_map)
    replacements: list = []

    for key in list(fact_map.keys()):
        if key in _TOPO_SKIP_FIELDS:
            continue
        fact_map[key] = _normalize_topo_value(fact_map[key], gazeteer, replacements)

    total = sum(r["count"] for r in replacements)
    print(f"[TOPO-NORMALIZE fact_map] {len(replacements)} видов замен, {total} вхождений.")
    return fact_map, replacements


def normalize_book_topo(book: dict, gazeteer: dict) -> tuple:
    """Task 040: применить gazeteer normalize к book JSON (кроме protected полей).

    Returns (normalized_book, replacements_list).
    """
    import copy
    book = copy.deepcopy(book)
    replacements: list = []

    for key in list(book.keys()):
        if key in _TOPO_SKIP_FIELDS:
            continue
        book[key] = _normalize_topo_value(book[key], gazeteer, replacements)

    total = sum(r["count"] for r in replacements)
    print(f"[TOPO-NORMALIZE book] {len(replacements)} видов замен, {total} вхождений.")
    return book, replacements


# ─────────────────────────────────────────────────────────────────
# Task 039: Bio_data integrity — required fields + relation whitelist
# ─────────────────────────────────────────────────────────────────

_FAMILY_RELATION_WHITELIST = frozenset({
    "отец", "мать", "муж", "жена", "сын", "дочь",
    "брат", "сестра", "бабушка", "дедушка",
    "прабабушка", "прадедушка",
    "внук", "внучка",
    "тётя", "дядя",
    "племянник", "племянница",
    "золовка", "свекровь", "свёкор", "свёкр",
    "тесть", "тёща",
    "зять", "невестка",
    "кум", "кума",
    "сват", "сватья",
})


def _relation_in_whitelist(relation: str) -> bool:
    rel = relation.strip().lower()
    for r in _FAMILY_RELATION_WHITELIST:
        if r in rel:
            return True
    return False


def filter_bio_data_family_by_relation_whitelist(book: dict) -> tuple:
    """Task 039: удалить из bio_data.family персон с relation НЕ в whitelist.

    Whitelist включает все стандартные родственные отношения.
    Соседи, подруги, коллеги, знакомые — удаляются.
    Returns (patched_book, removed_entries_list).
    """
    import copy
    book = copy.deepcopy(book)
    removed = []

    chapters = book.get("chapters", [])
    ch01 = next((ch for ch in chapters if ch.get("id") == "ch_01"), None)
    if ch01 is None:
        return book, removed

    bio_data = ch01.get("bio_data") or {}
    family = bio_data.get("family")
    if not family:
        return book, removed

    kept = []
    for entry in family:
        label = (entry.get("label") or entry.get("relation") or "").strip()
        if not label or _relation_in_whitelist(label):
            kept.append(entry)
        else:
            removed.append({
                "label": label,
                "value": entry.get("value", "?"),
                "source": entry.get("source", ""),
            })
            print(
                f"[BIO-WHITELIST] Убрана не-родственник из family: "
                f"«{label}» ({entry.get('value', '?')})"
            )

    bio_data["family"] = kept
    ch01["bio_data"] = bio_data
    print(f"[BIO-WHITELIST] Оставлено {len(kept)} из {len(family)}, удалено {len(removed)}.")
    return book, removed


def validate_bio_data_required_fields(fact_map: dict, book: dict) -> tuple:
    """Task 039: проверить и авто-патч bio_data.family required fields.

    Проверяет:
    - Для spouse / детей в fact_map.persons: если есть death_year / birth_year,
      они должны быть в bio_data.family (в note-поле).
    - bio_data.awards должны покрывать ключевые звания из fact_map.

    Auto-patch: добавляет missing years в note ("(ум. YYYY)" или "(р. YYYY)").
    Returns (patched_book, issues_list).
    """
    import copy
    book = copy.deepcopy(book)
    issues: list = []

    chapters = book.get("chapters", [])
    ch01 = next((ch for ch in chapters if ch.get("id") == "ch_01"), None)
    if ch01 is None:
        return book, issues

    bio_data = ch01.get("bio_data") or {}
    family = bio_data.get("family", [])

    persons = fact_map.get("persons", [])
    for person in persons:
        name = (person.get("name") or "").strip()
        relation = (
            person.get("relation_to_subject") or person.get("relation") or ""
        ).strip().lower()
        if not name or not relation:
            continue

        death_year = person.get("death_year")
        birth_year = person.get("birth_year")
        if death_year is None and birth_year is None:
            continue

        matching = [
            e for e in family
            if name.lower() in (e.get("value") or "").lower()
            or (e.get("value") or "").lower() in name.lower()
        ]

        for entry in matching:
            entry_note = entry.get("note") or ""
            entry_value = entry.get("value") or ""
            combined = entry_note + " " + entry_value

            if death_year and str(death_year) not in combined:
                issues.append({
                    "type": "missing_field",
                    "entity": name,
                    "relation": relation,
                    "field": "death_year",
                    "expected": death_year,
                    "source": person.get("id", "?"),
                    "action": "auto-patched",
                })
                entry["note"] = (entry_note + f" (ум. {death_year})").strip()
                print(f"[BIO-INTEGRITY] {name}: добавлен death_year {death_year} в note.")

            if birth_year and str(birth_year) not in combined:
                if relation in {"сын", "дочь", "муж", "жена"}:
                    issues.append({
                        "type": "missing_field",
                        "entity": name,
                        "relation": relation,
                        "field": "birth_year",
                        "expected": birth_year,
                        "source": person.get("id", "?"),
                        "action": "auto-patched",
                    })
                    entry["note"] = (entry.get("note") or "" + f" (р. {birth_year})").strip()
                    print(f"[BIO-INTEGRITY] {name}: добавлен birth_year {birth_year} в note.")

    # Проверка bio_data.awards
    fm_award_events = [
        e for e in fact_map.get("timeline", [])
        if "удар" in (e.get("title") or "").lower()
        or "award" in (e.get("event_type") or e.get("type") or "").lower()
    ]
    bio_awards_raw = bio_data.get("awards", [])
    bio_awards_text = " ".join(
        (a.get("value") or a) if isinstance(a, dict) else str(a)
        for a in bio_awards_raw
    ).lower()

    for event in fm_award_events:
        title = event.get("title", "")
        if title and len(title) > 5 and title.lower() not in bio_awards_text:
            issues.append({
                "type": "missing_award",
                "entity": title,
                "source": event.get("id", "fact_map"),
            })
            print(f"[BIO-INTEGRITY] Звание «{title}» из fact_map отсутствует в bio_data.awards.")

    bio_data["family"] = family
    ch01["bio_data"] = bio_data

    patched_count = len([i for i in issues if i.get("action") == "auto-patched"])
    print(
        f"[BIO-INTEGRITY] validate_required_fields: {len(issues)} проблем, "
        f"{patched_count} авто-патчем."
    )
    return book, issues


def load_config() -> dict:
    """Загружает pipeline_config.json. Падает с ошибкой если файл не найден."""
    if not CONFIG_FILE.exists():
        print(f"[ERROR] Конфиг не найден: {CONFIG_FILE}")
        sys.exit(1)
    with open(CONFIG_FILE, encoding="utf-8") as f:
        cfg = json.load(f)
    return cfg


def load_prompt(prompt_file: str) -> str:
    """
    Загружает промпт из файла в prompts/.
    Если файл содержит блок ```...``` — извлекает текст внутри.
    """
    path = PROMPTS_DIR / prompt_file
    if not path.exists():
        print(f"[ERROR] Промпт не найден: {path}")
        sys.exit(1)
    content = path.read_text(encoding="utf-8")
    match = re.search(r"^```\s*\n(.*?)^```", content, re.DOTALL | re.MULTILINE)
    if match:
        prompt = match.group(1).strip()
    else:
        prompt = content.strip()
    print(f"[PROMPT] Загружен {prompt_file} ({len(prompt)} символов)")
    return prompt


def _file_sha256(path: Path) -> str | None:
    """Возвращает SHA256 файла или None, если файл отсутствует."""
    if not path.exists() or not path.is_file():
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def get_git_sha() -> str | None:
    """Возвращает текущий git SHA (short) или None вне git-репозитория."""
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        sha = (r.stdout or "").strip()
        return sha or None
    except Exception:
        return None


def get_active_prompts_snapshot(cfg: dict) -> dict:
    """Строит снимок активных prompt_file и их хэшей."""
    snapshot: dict = {}
    for role, role_cfg in cfg.items():
        if not isinstance(role_cfg, dict):
            continue
        prompt_file = role_cfg.get("prompt_file")
        if not prompt_file:
            continue
        prompt_path = PROMPTS_DIR / prompt_file
        snapshot[role] = {
            "prompt_file": prompt_file,
            "prompt_exists": prompt_path.exists(),
            "prompt_sha256": _file_sha256(prompt_path),
            "model": role_cfg.get("model"),
            "max_tokens": role_cfg.get("max_tokens"),
            "temperature": role_cfg.get("temperature"),
        }
    return snapshot


def _hash_input_files(inputs: dict) -> dict:
    """Вычисляет sha256[:16] для всех значений inputs, которые являются путями к существующим файлам."""
    hashes: dict[str, str] = {}
    for key, value in (inputs or {}).items():
        if not isinstance(value, str):
            continue
        p = Path(value)
        if p.exists() and p.is_file():
            try:
                h = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
                hashes[key] = f"sha256:{h}"
            except Exception:
                pass
    return hashes


def save_run_manifest(
    *,
    output_dir: Path,
    prefix: str,
    stage: str,
    project_id: str,
    cfg: dict,
    ts: str,
    inputs: dict | None = None,
    outputs: dict | None = None,
    checkpoints: dict | None = None,
    notes: dict | None = None,
) -> Path:
    """
    Сохраняет run_manifest для воспроизводимости прогона.

    Файл: {prefix}_{stage}_run_manifest_{ts}.json
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    config_sha = _file_sha256(CONFIG_FILE)
    manifest = {
        "project_id": project_id,
        "stage": stage,
        "timestamp": ts,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "git_sha": get_git_sha(),
        "config_file": str(CONFIG_FILE),
        "config_sha256": config_sha,
        "active_prompts": get_active_prompts_snapshot(cfg),
        "inputs": inputs or {},
        "inputs_sha256": _hash_input_files(inputs),
        "outputs": outputs or {},
        "checkpoints": checkpoints or {},
        "notes": notes or {},
    }
    path = output_dir / f"{prefix}_{stage}_run_manifest_{ts}.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[SAVED] run_manifest: {path.name}")
    return path


# ─────────────────────────────────────────────────────────────────
# Шаг 1.5: Transcript Cleaner
# ─────────────────────────────────────────────────────────────────

MIN_TRANSCRIPT_CHARS = 10_000  # полный ASR ≥ 10k символов; конспект меньше — стоп

def run_cleaner(client, raw_text: str, subject_name: str,
                narrator_name: str, narrator_relation: str,
                cfg: dict | None = None) -> tuple[str, dict]:
    """
    Запускает Transcript Cleaner.
    Параметры модели берутся из pipeline_config.json (или cfg).
    Возвращает (cleaned_text, cleaning_metadata).

    ВАЖНО: ожидает полный ASR-транскрипт из exports/transcripts/.
    Если текст короче MIN_TRANSCRIPT_CHARS — выводит предупреждение.
    """
    if len(raw_text) < MIN_TRANSCRIPT_CHARS:
        print(
            f"\n[CLEANER] ⚠️  ПРЕДУПРЕЖДЕНИЕ: транскрипт {len(raw_text)} символов "
            f"(минимум {MIN_TRANSCRIPT_CHARS}). "
            f"Возможно, подан ручной конспект вместо полного ASR-файла.\n"
            f"           Используйте файл из exports/transcripts/ для полного покрытия фактов.\n"
        )

    if cfg is None:
        cfg = load_config()

    cleaner_cfg = cfg["cleaner"]
    model = cleaner_cfg["model"]
    max_tokens = cleaner_cfg["max_tokens"]
    temperature = cleaner_cfg.get("temperature", 0.1)
    system_prompt = load_prompt(cleaner_cfg["prompt_file"])

    print(f"\n[CLEANER] Запускаю ({model}, max_tokens={max_tokens})...")
    print(f"[CLEANER] Герой: {subject_name} | Рассказчик: {narrator_name} ({narrator_relation})")
    start = datetime.now()

    user_message = (
        f"Контекст: герой книги — {subject_name}, "
        f"рассказчик — {narrator_name} ({narrator_relation}).\n\n"
        f"Транскрипт:\n{raw_text}"
    )

    # Streaming required for large outputs (max_tokens > ~16000 may exceed 10 min limit)
    cleaned_parts = []
    with client.messages.stream(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}]
    ) as stream:
        for text in stream.text_stream:
            cleaned_parts.append(text)
    response = stream.get_final_message()
    elapsed = (datetime.now() - start).total_seconds()
    cleaned = "".join(cleaned_parts)

    raw_len = len(raw_text)
    clean_len = len(cleaned)
    length_change_pct = round((clean_len - raw_len) / raw_len * 100, 1) if raw_len else 0
    significant_change = abs(clean_len - raw_len) / raw_len > 0.2 if raw_len else False
    length_ratio = clean_len / raw_len if raw_len else 0

    cleaning_metadata = {
        "cleaning_applied": length_ratio >= 0.5,
        "length_change_percent": length_change_pct,
        "cleaning_significant_change": significant_change,
        "multi_speaker": "Спикер A" in cleaned or "Speaker A" in cleaned,
        "raw_len": raw_len,
        "clean_len": clean_len,
        "model": model,
        "max_tokens_used": max_tokens,
        "output_tokens": response.usage.output_tokens,
        "truncated": response.usage.output_tokens >= max_tokens - 10,
    }

    print(f"[CLEANER] Готово за {elapsed:.1f}с | {raw_len} → {clean_len} символов ({length_change_pct:+.1f}%)")
    print(f"[CLEANER] Токены: in={response.usage.input_tokens}, out={response.usage.output_tokens}")

    if cleaning_metadata["truncated"]:
        print(f"[CLEANER] ⚠️  ВНИМАНИЕ: output_tokens={response.usage.output_tokens} ≈ max_tokens={max_tokens}. "
              f"Вероятно обрезание! Увеличь max_tokens в pipeline_config.json.")

    if significant_change:
        print(f"[CLEANER] WARNING: cleaning_significant_change=True (изменение >20%)")

    if length_ratio < 0.5:
        print(f"[CLEANER] WARNING: output слишком короткий — используем сырой текст")
        return raw_text, {**cleaning_metadata, "cleaning_applied": False, "reason": "output_too_short"}

    # Авто-чекпоинт: сохраняем очищенный транскрипт
    project_id = cleaning_metadata.get("project_id") or subject_name.lower().split()[0]
    _auto_checkpoint(project_id, "cleaner",
                     {"cleaned_text": cleaned, "metadata": cleaning_metadata},
                     transcript_text=raw_text)

    return cleaned, cleaning_metadata


# ─────────────────────────────────────────────────────────────────
# Шаг 2: Fact Extractor
# ─────────────────────────────────────────────────────────────────

def merge_fact_maps(base: dict, incremental: dict) -> dict:
    """
    Мержит incremental fact_map (из Phase B Фактолога) в base fact_map.
    Поля-списки объединяются без дублей (по id или name).
    Скалярные поля subject обновляются только если в incremental они не None.
    """
    if not incremental:
        return base
    result = json.loads(json.dumps(base))  # deep copy

    # Subject: не затираем существующие данные, только добавляем
    base_subj = result.get("subject") or {}
    inc_subj = incremental.get("subject") or {}
    for k, v in inc_subj.items():
        if v is not None and not base_subj.get(k):
            base_subj[k] = v
    result["subject"] = base_subj

    # Списки: persons, timeline, relationships, locations, character_traits, quotes
    list_fields = {
        "persons":          "id",
        "timeline":         "id",
        "relationships":    None,
        "locations":        "name",
        "character_traits": "trait",
        "quotes":           "id",
        "source_quotes":    "id",
    }
    for field, key in list_fields.items():
        base_list = result.get(field) or []
        inc_list = incremental.get(field) or []
        if not inc_list:
            continue
        if key:
            existing_keys = {item.get(key) for item in base_list if item.get(key)}
            for item in inc_list:
                item_key = item.get(key)
                if item_key and item_key not in existing_keys:
                    item["is_new"] = True
                    base_list.append(item)
                    existing_keys.add(item_key)
        else:
            # Без ключа дедупликации — просто добавляем с маркером is_new
            base_list_str = json.dumps(base_list, ensure_ascii=False)
            for item in inc_list:
                if json.dumps(item, ensure_ascii=False) not in base_list_str:
                    item["is_new"] = True
                    base_list.append(item)
        result[field] = base_list

    result["_merged_from_phase_b"] = True
    return result


def run_fact_extractor(client, cleaned_text: str, subject_name: str,
                       narrator_name: str, narrator_relation: str,
                       project_id: str, known_birth_year: int | None = None,
                       known_details: str | None = None,
                       existing_facts: dict | None = None,
                       phase: str = "A",
                       call_type: str = "initial",
                       cfg: dict | None = None) -> dict:
    """
    Запускает Fact Extractor.

    Параметры:
      phase: "A" (initial) или "B" (incremental — обогащение existing_facts).
        Используется в task 035 split-extract mode: TR1 → Phase A,
        TR2 → Phase B с existing_facts=fact_map_TR1.
      call_type: "initial" (Phase A первый запуск) или "incremental"
        (Phase B на дополнительном транскрипте).
      existing_facts: для Phase B — fact_map от предыдущего прохода.

    Параметры модели берутся из pipeline_config.json (или cfg).
    Возвращает fact_map (dict).
    """
    if cfg is None:
        cfg = load_config()

    fe_cfg = cfg["fact_extractor"]
    model = fe_cfg["model"]
    max_tokens = fe_cfg["max_tokens"]
    temperature = fe_cfg.get("temperature", 0.15)
    system_prompt = load_prompt(fe_cfg["prompt_file"])

    print(f"\n[FACT EXTRACTOR] Запускаю ({model}, max_tokens={max_tokens}, phase={phase})...")
    start = datetime.now()

    # Phase B instruction: incremental extraction
    if phase == "B" and existing_facts:
        instruction = (
            "Извлеки факты из дополнительного протокола интервью. "
            "Используй existing_facts как baseline: НЕ дублируй уже известные факты "
            "(те же persons/events/locations с теми же id). Извлекай ТОЛЬКО НОВЫЕ "
            "факты из этого транскрипта — эпизоды, имена, события которых нет в "
            "existing_facts. Если факт уточняет уже известный (например, добавляет "
            "детали к event_001) — верни его как is_refinement: true с тем же id."
        )
    else:
        instruction = "Извлеки все факты из протокола интервью. Построй карту фактов, хронологию, определи пробелы."

    user_message = {
        "context": {
            "project_id": project_id,
            "phase": phase,
            "call_type": call_type,
            "iteration": 1,
            "max_iterations": 1,
            "previous_agent": "transcript_cleaner",
            "instruction": instruction,
        },
        "data": {
            "subject": {
                "name": subject_name,
                "known_birth_year": known_birth_year,
                "known_details": known_details
            },
            "interview": {
                "id": "int_001",
                "speaker": {
                    "id": "narrator_001",
                    "name": narrator_name,
                    "relation_to_subject": narrator_relation
                },
                "transcript": cleaned_text
            },
            "existing_facts": existing_facts
        }
    }

    # Используем streaming — обязательно при max_tokens > ~16000 (требование Anthropic SDK)
    raw_parts = []
    input_tokens = 0
    output_tokens = 0
    with client.messages.stream(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system_prompt,
        messages=[{"role": "user", "content": json.dumps(user_message, ensure_ascii=False)}]
    ) as stream:
        for text in stream.text_stream:
            raw_parts.append(text)
        final_msg = stream.get_final_message()
        input_tokens = final_msg.usage.input_tokens
        output_tokens = final_msg.usage.output_tokens

    elapsed = (datetime.now() - start).total_seconds()
    raw = "".join(raw_parts)
    print(f"[FACT EXTRACTOR] Готово за {elapsed:.1f}с | {len(raw)} символов | "
          f"токены: in={input_tokens}, out={output_tokens}")

    if output_tokens >= max_tokens - 10:
        print(f"[FACT EXTRACTOR] ⚠️  ВНИМАНИЕ: output_tokens ≈ max_tokens. "
              f"Увеличь max_tokens в pipeline_config.json.")

    # Парсинг JSON
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:])
        if raw.endswith("```"):
            raw = raw[:-3].strip()
    s = raw.find("{")
    e = raw.rfind("}")
    if s != -1 and e > s:
        try:
            fact_map = json.loads(raw[s:e + 1])
        except Exception:
            fact_map = json.loads(raw)
    else:
        fact_map = json.loads(raw)

    # Авто-чекпоинт: сохраняем карту фактов
    _auto_checkpoint(project_id, "fact_map", fact_map,
                     transcript_text=cleaned_text)
    return fact_map


# ─────────────────────────────────────────────────────────────────
# Аудитор полноты (Completeness Auditor)
# ─────────────────────────────────────────────────────────────────

def run_completeness_auditor(
    client,
    cleaned_text: str,
    fact_map: dict,
    subject_name: str,
    narrator_name: str,
    narrator_relation: str,
    project_id: str,
    pin_list_fact_map: dict | None = None,
    pin_list_episodes: dict | None = None,
    cfg: dict | None = None,
) -> dict:
    """
    Запускает Completeness Auditor (агент 16).

    Принимает очищенный транскрипт и уже готовый fact_map от FE.
    Опционально принимает fact_map предыдущего прогона (pin_list_fact_map) как
    контрольный список: персоны из него считаются «закреплёнными» — если они
    были в предыдущем прогоне, но не найдены в текущем, Аудитор обязан перепроверить.

    Возвращает audit_result:
      {
        "auto_enrich":    частичный fact_map (persons/timeline/etc.) → мержится в основной
        "log_only_gaps":  {missing_persons, missing_events, ...} → только в логи
        "processing_notes": {...}
      }

    Вызывать ПОСЛЕ run_fact_extractor, ДО clean_fact_map_for_downstream.
    Применить auto_enrich через merge_fact_maps(base=fact_map, incremental=result["auto_enrich"]).
    """
    if cfg is None:
        cfg = load_config()

    ca_cfg = cfg.get("completeness_auditor")
    if not ca_cfg:
        print("[COMPLETENESS AUDITOR] ⚠️  Конфиг completeness_auditor отсутствует в pipeline_config.json — пропуск")
        return {"auto_enrich": {}, "log_only_gaps": {}, "processing_notes": {"skipped": True}}

    model = ca_cfg["model"]
    max_tokens = ca_cfg["max_tokens"]
    temperature = ca_cfg.get("temperature", 0.1)
    system_prompt = load_prompt(ca_cfg["prompt_file"])

    print(f"\n[COMPLETENESS AUDITOR] Запускаю ({model}, max_tokens={max_tokens})...")
    start = datetime.now()

    user_message = {
        "context": {
            "project_id": project_id,
            "narrator_name": narrator_name,
            "narrator_relation": narrator_relation,
        },
        "data": {
            "subject_name": subject_name,
            "cleaned_transcript": cleaned_text,
            "fact_map": fact_map,
        },
    }

    # Pin-list: персоны + events из предыдущего прогона или known_episodes файла (task 035 v1.2)
    if pin_list_fact_map:
        prev_persons = pin_list_fact_map.get("persons", []) or []
        prev_events = pin_list_fact_map.get("timeline", []) or pin_list_fact_map.get("events", []) or []
        if prev_persons or prev_events:
            pin_list = [
                {
                    "id": p.get("id", ""),
                    "name": p.get("name", ""),
                    "aliases": p.get("aliases", []),
                    "relation_to_subject": p.get("relation_to_subject", "unknown"),
                }
                for p in prev_persons
                if p.get("name")
            ]
            pin_events = [
                {
                    "id": e.get("id", ""),
                    "title": e.get("title", "") or e.get("description", "")[:80],
                    "year": e.get("year") or e.get("date") or e.get("period"),
                    "markers": e.get("markers", []),
                }
                for e in prev_events
                if e.get("id") or e.get("title")
            ]
            user_message["pin_list"] = {
                "source": "previous_run_fact_map_or_known_episodes",
                "description": (
                    "Контрольный список из предыдущего прогона или known_episodes файла. "
                    "Если персона/event был в предыдущем прогоне, но отсутствует в текущем fact_map — "
                    "обязательно проверить транскрипт. Если найден → auto_enrich; "
                    "если нет → log_only_gaps с пометкой 'was_in_pin_list'."
                ),
                "persons": pin_list,
                "events": pin_events,
            }
            print(f"[COMPLETENESS AUDITOR] Pin-list: {len(pin_list)} персон + {len(pin_events)} events из предыдущего прогона")

    # Task 041b/038b: known_episodes pin_list с bypass strict для CA v1.4
    if pin_list_episodes:
        ep_list = pin_list_episodes.get("episodes", [])
        req_persons = pin_list_episodes.get("required_persons", [])
        # Добавляем is_pin_list_required: true для всех элементов
        ep_with_flag = [{**ep, "is_pin_list_required": True} for ep in ep_list]
        rp_with_flag = [{**rp, "is_pin_list_required": True} for rp in req_persons]

        existing_pinlist = user_message.get("pin_list", {})
        user_message["pin_list"] = {
            **existing_pinlist,
            "source": "known_episodes_file",
            "description": (
                "Pin-list эпизодов из known_episodes файла. "
                "Элементы с is_pin_list_required=true: ПРАВИЛО 4 (strict description) НЕ применяется. "
                "Обязательно добавить в auto_enrich с was_in_pin_list=true, даже если confidence=low."
            ),
            "episodes": ep_with_flag,
            "required_persons": rp_with_flag,
        }
        print(f"[COMPLETENESS AUDITOR] Pin-list episodes: {len(ep_with_flag)} эпизодов + {len(rp_with_flag)} required_persons (bypass strict)")

    raw_chunks = []
    with client.messages.stream(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system_prompt,
        messages=[{"role": "user", "content": json.dumps(user_message, ensure_ascii=False)}],
    ) as stream:
        for text in stream.text_stream:
            raw_chunks.append(text)
        final_msg = stream.get_final_message()

    elapsed = (datetime.now() - start).total_seconds()
    raw = "".join(raw_chunks).strip()
    in_tok = final_msg.usage.input_tokens
    out_tok = final_msg.usage.output_tokens
    truncated = out_tok >= max_tokens - 10

    print(f"[COMPLETENESS AUDITOR] Готово за {elapsed:.1f}с | токены: in={in_tok}, out={out_tok}")
    if truncated:
        print(f"[COMPLETENESS AUDITOR] ⚠️  ВНИМАНИЕ: output_tokens={out_tok} ≈ max_tokens={max_tokens}. Возможно обрезание!")

    # Парсинг JSON
    try:
        if raw.startswith("```"):
            raw = re.sub(r"^```[a-z]*\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)
        result = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"[COMPLETENESS AUDITOR] ⚠️  JSON parse error: {e}. Возвращаю пустой результат.")
        return {"auto_enrich": {}, "log_only_gaps": {}, "processing_notes": {"parse_error": str(e)}}

    # Статистика
    notes = result.get("processing_notes", {})
    ae = result.get("auto_enrich", {})
    lg = result.get("log_only_gaps", {})
    ae_persons = len(ae.get("persons", []))
    ae_events = len(ae.get("timeline", []))
    ae_locs = len(ae.get("locations", []))
    ae_traits = len(ae.get("character_traits", []))
    lg_persons = len(lg.get("missing_persons", []))
    lg_events = len(lg.get("missing_events", []))
    lg_locs = len(lg.get("missing_locations", []))
    lg_traits = len(lg.get("missing_traits", []))

    print(f"[COMPLETENESS AUDITOR] auto_enrich: persons={ae_persons}, events={ae_events}, locs={ae_locs}, traits={ae_traits}")
    print(f"[COMPLETENESS AUDITOR] log_only:    persons={lg_persons}, events={lg_events}, locs={lg_locs}, traits={lg_traits}")
    if notes.get("summary"):
        print(f"[COMPLETENESS AUDITOR] {notes['summary']}")

    return result


def apply_completeness_enrichment(fact_map: dict, audit_result: dict) -> tuple[dict, dict]:
    """
    Применяет auto_enrich из результата Аудитора к fact_map.

    Возвращает (enriched_fact_map, enrichment_stats):
      enriched_fact_map — обогащённый fact_map (merge_fact_maps с auto_enrich)
      enrichment_stats  — статистика для manifest: сколько что добавлено
    """
    auto_enrich = audit_result.get("auto_enrich", {})
    log_only = audit_result.get("log_only_gaps", {})

    ae_persons = auto_enrich.get("persons", [])
    ae_events = auto_enrich.get("timeline", [])
    ae_locs = auto_enrich.get("locations", [])
    ae_traits = auto_enrich.get("character_traits", [])
    ae_quotes = auto_enrich.get("quotes", [])

    if not any([ae_persons, ae_events, ae_locs, ae_traits, ae_quotes]):
        print("[COMPLETENESS AUDITOR] auto_enrich пуст — fact_map не изменён")
        enriched = fact_map
    else:
        enriched = merge_fact_maps(fact_map, auto_enrich)
        print(f"[COMPLETENESS AUDITOR] Обогащён fact_map: +{len(ae_persons)} persons, "
              f"+{len(ae_events)} events, +{len(ae_locs)} locs, +{len(ae_traits)} traits")

    log_persons = log_only.get("missing_persons", [])
    log_events = log_only.get("missing_events", [])
    log_locs = log_only.get("missing_locations", [])
    log_traits = log_only.get("missing_traits", [])
    has_gaps = any([log_persons, log_events, log_locs, log_traits])

    if has_gaps:
        print(f"[COMPLETENESS AUDITOR] ⚠️  log_only gaps: "
              f"{len(log_persons)} persons, {len(log_events)} events, "
              f"{len(log_locs)} locs, {len(log_traits)} traits → проверь roles_checklist")

    enrichment_stats = {
        "completeness_status": "incomplete" if has_gaps else "ok",
        "auto_enriched": {
            "persons": len(ae_persons),
            "events": len(ae_events),
            "locations": len(ae_locs),
            "traits": len(ae_traits),
        },
        "log_only_gaps": {
            "missing_persons": log_persons,
            "missing_events": log_events,
            "missing_locations": log_locs,
            "missing_traits": log_traits,
        },
    }
    return enriched, enrichment_stats

def clean_fact_map_for_downstream(fact_map_full: dict) -> dict:
    """
    Убирает служебные поля (asr_variants, reasoning, confidence) из fact_map
    перед передачей в Stage 2 (Ghostwriter, Fact Checker).
    GW и FC должны работать только с полем name — без путаницы в служебных полях.
    Возвращает копию без мутации оригинала.
    """
    import copy
    fm = copy.deepcopy(fact_map_full)
    _STRIP_FIELDS = ("asr_variants", "reasoning", "confidence")
    for loc in fm.get("locations", []):
        for f in _STRIP_FIELDS:
            loc.pop(f, None)
    for p in fm.get("persons", []):
        for f in _STRIP_FIELDS:
            p.pop(f, None)
    return fm


def run_historian(client, fact_map: dict, cfg: dict | None = None) -> dict:
    """
    Запускает Историка-краеведа.
    Получает fact_map → возвращает исторический контекст (dict).
    Non-blocking: при ошибке возвращает пустой dict.
    """
    if cfg is None:
        cfg = load_config()

    hist_cfg = cfg["historian"]
    model = hist_cfg["model"]
    max_tokens = hist_cfg["max_tokens"]
    temperature = hist_cfg.get("temperature", 0.3)
    system_prompt = load_prompt(hist_cfg["prompt_file"])

    print(f"\n[HISTORIAN] Запускаю ({model}, max_tokens={max_tokens})...")
    start = datetime.now()

    user_message = {
        "subject": fact_map.get("subject", {}),
        "timeline": fact_map.get("timeline", []),
        "locations": fact_map.get("locations", []),
        "persons": fact_map.get("persons", []),
    }

    try:
        raw_chunks = []
        with client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": json.dumps(user_message, ensure_ascii=False)}]
        ) as stream:
            for text in stream.text_stream:
                raw_chunks.append(text)
            final_msg = stream.get_final_message()
        elapsed = (datetime.now() - start).total_seconds()
        raw = "".join(raw_chunks).strip()
        in_tok = final_msg.usage.input_tokens
        out_tok = final_msg.usage.output_tokens
        print(f"[HISTORIAN] Готово за {elapsed:.1f}с | {len(raw)} символов | токены: in={in_tok}, out={out_tok}")

        raw = raw.strip()
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[1:])
            if raw.endswith("```"):
                raw = raw[:-3].strip()
        s = raw.find("{")
        e = raw.rfind("}")
        if s != -1 and e > s:
            return json.loads(raw[s:e + 1])
        return json.loads(raw)
    except Exception as ex:
        print(f"[HISTORIAN] ⚠️  Ошибка: {ex}. Продолжаем без исторического контекста.")
        return {}


# ─────────────────────────────────────────────────────────────────
# Stage 2: Писатель (Ghostwriter)
# ─────────────────────────────────────────────────────────────────

def run_ghostwriter(client, fact_map: dict, transcripts: list[dict],
                    subject_name: str, project_id: str,
                    cfg: dict | None = None,
                    call_type: str = "initial",
                    current_book: dict | None = None,
                    historical_context: dict | None = None,
                    revision_scope: dict | None = None,
                    version: int = 1,
                    force_phase: str | None = None,
                    pin_list: dict | None = None) -> dict:
    """
    Запускает Писателя.
    call_type: "initial" (1-й проход) | "revision" (2-й проход с историком)
    force_phase: если задан ("A" или "B"), переопределяет автоматическое определение phase.
      Используй force_phase="A" для historian_integration (Phase A pass 2 по спеку v2.14).
    pin_list: dict из parse_pin_list_from_markdown() — task 041, Batch 2.
      Если задан, добавляется в user_message["pin_list"] для GW v2.19.
    Возвращает book_draft (dict).
    """
    if cfg is None:
        cfg = load_config()

    gw_cfg = cfg["ghostwriter"]
    model = gw_cfg["model"]
    max_tokens = gw_cfg["max_tokens"]
    temperature = gw_cfg.get("temperature", 0.5)
    system_prompt = load_prompt(gw_cfg["prompt_file"])

    if force_phase is not None:
        phase = force_phase
    else:
        phase = "B" if (current_book is not None and call_type == "revision") else "A"
    print(f"\n[GHOSTWRITER] Запускаю ({model}, max_tokens={max_tokens}, call_type={call_type})...")
    start = datetime.now()

    user_message: dict = {
        "phase": phase,
        "project_id": project_id,
        "subject": {"name": subject_name},
        "fact_map": fact_map,
        "transcripts": transcripts,
    }

    if call_type == "revision" and current_book:
        user_message["current_book"] = current_book
        user_message["revision_scope"] = revision_scope or {
            "type": "historian_integration",
            "affected_chapters": ["ch_01", "ch_02", "ch_03", "ch_04"],
            "instructions": "Интегрируй исторический контекст от Историка-краеведа. Дополняй, не переписывай."
        }
    if historical_context:
        # run_historian возвращает {"historical_context": [...], "era_glossary": [...]}.
        # Распаковываем внутренний массив, а не оборачиваем весь dict в список —
        # Ghostwriter ожидает historical_context как список объектов с suggested_insertions.
        if isinstance(historical_context, dict) and "historical_context" in historical_context:
            ctx_list = historical_context["historical_context"]
            glossary = historical_context.get("era_glossary", [])
        elif isinstance(historical_context, list):
            ctx_list = historical_context
            glossary = []
        else:
            ctx_list = [historical_context]
            glossary = []
        user_message["historical_context"] = ctx_list
        user_message["era_glossary"] = glossary

    # Task 041 (Batch 2): pin_list — обязательные эпизоды для GW v2.19
    if pin_list:
        user_message["pin_list"] = pin_list
        print(f"[GHOSTWRITER] pin_list: {len(pin_list.get('episodes', []))} эпизодов, "
              f"{len(pin_list.get('bytovye', []))} бытовых")

    # Streaming — обязательно при max_tokens >= 16000
    raw_parts = []
    with client.messages.stream(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system_prompt,
        messages=[{"role": "user", "content": json.dumps(user_message, ensure_ascii=False)}]
    ) as stream:
        for text in stream.text_stream:
            raw_parts.append(text)
        final_msg = stream.get_final_message()
    elapsed = (datetime.now() - start).total_seconds()
    raw = "".join(raw_parts).strip()
    print(f"[GHOSTWRITER] Готово за {elapsed:.1f}с | {len(raw)} символов | "
          f"токены: in={final_msg.usage.input_tokens}, out={final_msg.usage.output_tokens}")

    if final_msg.usage.output_tokens >= max_tokens - 10:
        print(f"[GHOSTWRITER] ⚠️  ВНИМАНИЕ: output_tokens ≈ max_tokens. Возможно обрезание.")

    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:])
        if raw.endswith("```"):
            raw = raw[:-3].strip()
    s = raw.find("{")
    e = raw.rfind("}")
    if s != -1 and e > s:
        try:
            return json.loads(raw[s:e + 1])
        except Exception:
            pass
    return json.loads(raw)


# ─────────────────────────────────────────────────────────────────
# Post-validator: anti-deletion guard для revision (волна 1.2.2)
# ─────────────────────────────────────────────────────────────────

REVISION_MIN_VOLUME_RATIO = 0.95  # объём после revision должен быть ≥ 95% от до


def _book_total_chars(book: dict) -> int:
    """Суммарный объём контента: chapters[].content + callouts[].text + historical_notes[].text."""
    total = 0
    for ch in book.get("chapters", []) or []:
        total += len(ch.get("content") or "")
    for co in book.get("callouts", []) or []:
        total += len(co.get("text") or "")
    for hn in book.get("historical_notes", []) or []:
        total += len(hn.get("text") or "")
    return total


def _normalize_for_evidence(text: str) -> str:
    """Нормализует текст для evidence-сравнения: lowercase + collapse whitespace.
    Не меняет content semantically — снимает только формат (пробелы, регистр)."""
    import re
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


# Стоп-слова для evidence-topic overlap: служебные/частотные русские слова,
# которые не несут смысла эпизода. Без них «общими словами» считаются только
# содержательные токены (имена, объекты, места, действия).
_EVIDENCE_STOPWORDS = {
    # союзы / частицы
    "что", "как", "это", "так", "там", "тот", "этот", "тоже", "также",
    "ещё", "уже", "когда", "если", "чтобы", "тогда", "хотя", "потому", "ведь",
    "только", "очень", "более", "менее", "потом", "затем", "куда", "откуда",
    "пока", "после", "перед", "теперь", "потому", "поэтому", "вместе",
    # местоимения
    "она", "его", "ему", "ей", "ним", "них", "которые", "которая", "которое",
    "которые", "себя", "свою", "своё", "свой", "своих", "сама", "сам",
    "одна", "один", "одно", "одни", "другой", "другая", "другое", "другие",
    "каждый", "каждая", "всё", "все", "кто", "что-то", "кто-то", "ничего",
    # глаголы общего действия
    "был", "была", "было", "были", "есть", "стал", "стала", "стало", "стали",
    "будет", "может", "можно", "нужно", "хочет", "сказал", "сказала",
    "говорит", "сделал", "сделала", "пришёл", "пришла", "ушёл", "ушла",
    "знает", "знал", "знала", "видел", "видела", "имел", "имела",
    # частые предлоги/наречия которые нужно отфильтровать на токенах ≥4 символов
    "сразу", "затем", "после", "потом", "тогда", "очень", "много", "мало",
    "часто", "редко", "сразу", "вдруг", "никогда", "всегда", "иногда",
    # обобщения тем (специально для семейных биографий)
    "семья", "семьи", "семью", "родители", "родственники", "близкие",
    "конфликт", "отношения", "разговор", "случай", "история", "эпизод",
    "однажды", "ситуация", "момент",
}


def _topic_tokens(text: str, min_len: int = 4) -> set[str]:
    """
    Извлекает значимые токены для topic-overlap сравнения.
    Lowercase, минимум `min_len` символов, не в стоп-словах.

    Цель: оставить только сущностные слова (имена, объекты, места,
    конкретные действия), отбросить служебные и общие.
    """
    import re
    if not text:
        return set()
    # Разбиваем по любому non-letter символу (включая дефисы для составных слов)
    tokens = re.findall(r"[а-яёa-z]+", text.lower())
    return {t for t in tokens if len(t) >= min_len and t not in _EVIDENCE_STOPWORDS}


# Минимальный overlap значимых токенов между evidence и удаляемым фрагментом.
# Ниже — считаем что evidence описывает другой эпизод (не дубль того что удаляется).
EVIDENCE_TOPIC_OVERLAP_MIN = 0.25  # 25% от меньшего из двух множеств

# Абсолютный минимум общих значимых токенов (волна 1.3.2): защита от случая
# когда множества маленькие и 25% — это всего 1 токен. v50: один общий токен
# («валентина» — имя субъекта) при множестве из 10 = 10% < 25%, но если
# множества по 4 токена каждое, 25% = 1 токен, что недостаточно для
# подтверждения тождества эпизода.
EVIDENCE_MIN_SHARED_TOKENS = 2


def _evidence_topic_overlap(evidence_quote: str, what_is_written: str) -> dict:
    """
    Считает topic-overlap между evidence quote и удаляемым фрагментом.

    Возвращает dict с:
      evidence_tokens_count, written_tokens_count
      shared_count: число общих значимых токенов
      shared: пересечение (top-10 для диагностики)
      overlap_ratio: |shared| / min(|evidence|, |written|)
      passed: True если выполнены ОБА условия:
        1. overlap_ratio >= EVIDENCE_TOPIC_OVERLAP_MIN (25%)
        2. shared_count >= EVIDENCE_MIN_SHARED_TOKENS (2)

      Оба условия защищают от разных провалов:
      - ratio: «множества большие, общих мало» — т.е. эпизоды не пересекаются
      - shared_count: «множества маленькие, 1 общий токен это случайность»
        (v50 кейс — общая «валентина», но конкретные объекты эпизодов разные)
    """
    ev_tokens = _topic_tokens(evidence_quote)
    wr_tokens = _topic_tokens(what_is_written)
    shared = ev_tokens & wr_tokens

    smaller = min(len(ev_tokens), len(wr_tokens))
    if smaller == 0:
        # Один из текстов пустой по значимым токенам — не можем сравнить
        return {
            "evidence_tokens_count": len(ev_tokens),
            "written_tokens_count": len(wr_tokens),
            "shared_count": 0,
            "shared": [],
            "overlap_ratio": None,
            "passed": False,
            "reason": "insufficient_tokens",
        }

    overlap_ratio = len(shared) / smaller
    ratio_ok = overlap_ratio >= EVIDENCE_TOPIC_OVERLAP_MIN
    abs_ok = len(shared) >= EVIDENCE_MIN_SHARED_TOKENS
    passed = ratio_ok and abs_ok

    return {
        "evidence_tokens_count": len(ev_tokens),
        "written_tokens_count": len(wr_tokens),
        "shared_count": len(shared),
        "shared": sorted(shared)[:10],  # для диагностики, top-10
        "overlap_ratio": round(overlap_ratio, 3),
        "min_shared_tokens": EVIDENCE_MIN_SHARED_TOKENS,
        "ratio_check_passed": ratio_ok,
        "abs_check_passed": abs_ok,
        "passed": passed,
    }


def _chapter_content(book: dict, chapter_id: str) -> str:
    """Возвращает content главы по id или пустую строку."""
    for ch in book.get("chapters", []) or []:
        if ch.get("id") == chapter_id:
            return ch.get("content") or ""
    return ""


def _verify_evidence_in_book(
    err: dict,
    book_after: dict,
) -> tuple[bool, str, dict]:
    """
    Для error с legitimate_deletion=true — проверяет evidence_in_other_chapter
    (если задано) против реального содержимого book_after, и дополнительно
    (волна 1.3.1) проверяет что evidence quote описывает ТОТ ЖЕ ЭПИЗОД,
    не «общую тему» (через topic-overlap значимых токенов).

    Возвращает (passed, reason, topic_overlap):
      passed=True — всё ок (либо evidence не нужен, либо все проверки прошли)
      passed=False — evidence указан но какая-то проверка провалилась
      topic_overlap: dict с метриками overlap (или {} если не считалось)

    Проверки последовательно:
      0. err.type != framing_distortion → evidence не нужен (variant A)
      1. evidence не указан / quote < 30 символов → blocked_missing_evidence
      2. evidence.chapter_id указывает на пустую главу → blocked
      3. evidence.quote не найдена в book_after.chapter_id.content → blocked_phantom_evidence
      4. topic-overlap между evidence.quote и err.what_is_written < EVIDENCE_TOPIC_OVERLAP_MIN
         → blocked_evidence_topic_mismatch (волна 1.3.1)
    """
    err_type = err.get("type", "")

    # Только для cross-chapter (framing_distortion) требуется evidence
    if err_type != "framing_distortion":
        return True, "non_cross_chapter_legitimate_deletion", {}

    evidence = err.get("evidence_in_other_chapter") or {}
    ev_chapter = evidence.get("chapter_id", "")
    ev_quote = evidence.get("quote", "")

    if not ev_chapter or not ev_quote:
        return False, (
            f"FC error {err.get('id')}: framing_distortion + legitimate_deletion=true "
            f"требует evidence_in_other_chapter (chapter_id + quote ≥30 символов). "
            f"Не указано — потенциальная галлюцинация cross-chapter дубля."
        ), {}

    if len(ev_quote) < 30:
        return False, (
            f"FC error {err.get('id')}: evidence_in_other_chapter.quote слишком короткая "
            f"({len(ev_quote)} символов, требуется ≥30) — недостаточная верификация."
        ), {}

    chapter_content = _chapter_content(book_after, ev_chapter)
    if not chapter_content:
        return False, (
            f"FC error {err.get('id')}: evidence ссылается на ch={ev_chapter}, "
            f"но эта глава пустая или отсутствует в book_after."
        ), {}

    # Сравниваем нормализованно — допускаем минимальные изменения formatting'а после GW revision
    if _normalize_for_evidence(ev_quote) not in _normalize_for_evidence(chapter_content):
        return False, (
            f"FC error {err.get('id')}: evidence quote не найдена в book_after.{ev_chapter}.content. "
            f"Возможная галлюцинация дубля или эпизод исчез из обеих глав. "
            f"Quote (первые 80 симв): {ev_quote[:80]!r}"
        ), {}

    # Волна 1.3.1 + 1.3.2: topic-overlap проверка — evidence quote должна
    # описывать тот же эпизод что удаляется, не «общую тему». Два условия:
    # (a) ratio >= 25% от меньшего из множеств (волна 1.3.1)
    # (b) abs >= 2 общих значимых токенов (волна 1.3.2 — защита от случая
    #     когда множества маленькие и 25% это всего 1 токен).
    what_is_written = err.get("what_is_written", "")
    overlap = _evidence_topic_overlap(ev_quote, what_is_written)
    if not overlap["passed"]:
        # Конкретизируем причину для диагностики
        if overlap.get("reason") == "insufficient_tokens":
            cause = "недостаточно значимых токенов в evidence или удаляемом фрагменте"
        elif not overlap.get("ratio_check_passed", True) and not overlap.get("abs_check_passed", True):
            cause = (
                f"и ratio ({overlap['overlap_ratio']} < {EVIDENCE_TOPIC_OVERLAP_MIN}), "
                f"и абсолютное число общих токенов ({overlap['shared_count']} < "
                f"{EVIDENCE_MIN_SHARED_TOKENS}) — оба условия провалились"
            )
        elif not overlap.get("ratio_check_passed", True):
            cause = (
                f"ratio {overlap['overlap_ratio']} < {EVIDENCE_TOPIC_OVERLAP_MIN}"
            )
        else:
            cause = (
                f"общих значимых токенов всего {overlap['shared_count']} "
                f"< минимума {EVIDENCE_MIN_SHARED_TOKENS} (защита от случая "
                f"когда совпадает только имя субъекта или общая тема, "
                f"но не предметные маркеры эпизода)"
            )
        return False, (
            f"FC error {err.get('id')}: evidence quote семантически не покрывает "
            f"удаляемый фрагмент: {cause}. "
            f"Shared tokens: {overlap.get('shared', [])}. "
            f"Возможно FC галлюцинирует семантическое тождество разных эпизодов "
            f"одной темы (v49: огурцы vs счётчик; v50: один общий токен «валентина»)."
        ), overlap

    return True, "evidence_verified", overlap


def merge_revision_out_of_scope_chapters(
    book_before: dict,
    book_after: dict,
    affected_chapters: list[str] | None,
) -> tuple[dict, dict]:
    """
    Защита волны 1.3.3: GW out-of-scope guardrail при revision.

    Гарантирует архитектурно (не промптом), что Ghostwriter при revision не
    меняет главы вне revision_scope.affected_chapters. Главы вне scope
    физически копируются из book_before snapshot, независимо от того, что
    вернул GW.

    История класса (v52, 2026-05-08):
      FC v2.13 нашёл 8 ошибок в ch_01/ch_02 (`legitimate_deletion=False` —
      требуется fact_correction). GW v2.15 при revision вернул книгу с
      пустыми ch_03/ch_04/epilogue (52.8% drop). GW v2.15 промпт явно
      содержит SCOPE LOCK правило (строки 1383-1385 v2.15) — модель
      его проигнорировала. validate_revision_volume поймал на
      blocked_unauthorized_deletion, прогон остановился с откатом.

      Этот merge переводит защиту scope с промпт-уровня (ненадёжный) на
      код-уровень (детерминированный). После merge validate_revision_volume
      остаётся как secondary защита (если merge сам сломается).

    Алгоритм:
      1. chapters в affected_chapters: берутся из book_after (результат GW)
      2. chapters вне affected_chapters: восстанавливаются из book_before
      3. callouts/historical_notes с chapter_id вне scope:
         восстанавливаются из book_before (если в book_after отсутствуют
         или изменены — восстанавливаем по chapter_id принадлежности)
      4. callouts/historical_notes БЕЗ chapter_id (глобальные): pass-through
         из book_after
      5. Top-level fields (title, и т.д.) — pass-through из book_after

    Edge cases:
      - affected_chapters=None или []: ничего не модифицируется (нет scope —
        нет защиты, GW работал во всех главах). Возвращает book_after as-is
        с пометкой no_scope_provided.
      - Глава отсутствует в book_after, но есть в book_before: восстанавливается.
      - Новая глава в book_after, которой нет в book_before: добавляется
        ТОЛЬКО если её id в affected_chapters (иначе считается out-of-scope
        новотворчеством GW и отбрасывается).

    Args:
      book_before: snapshot книги до GW revision
      book_after: результат GW revision
      affected_chapters: список chapter_id из revision_scope.affected_chapters

    Returns:
      (merged_book, details):
        merged_book: dict — результат scope-aware merge
        details: dict — диагностика модификаций
    """
    import copy

    if not affected_chapters:
        return copy.deepcopy(book_after), {
            "scope_enforcement": "skipped",
            "reason": "no_scope_provided",
            "affected_chapters": affected_chapters,
            "chapters_restored": [],
            "callouts_restored": 0,
            "historical_notes_restored": 0,
            "chars_restored": 0,
        }

    affected_set = set(affected_chapters)
    chars_before_total = _book_total_chars(book_before)
    chars_after_total = _book_total_chars(book_after)

    chapters_before_by_id = {
        ch.get("id"): ch for ch in (book_before.get("chapters") or []) if ch.get("id")
    }
    chapters_after_by_id = {
        ch.get("id"): ch for ch in (book_after.get("chapters") or []) if ch.get("id")
    }

    merged = copy.deepcopy(book_after)

    chapters_restored = []
    new_out_of_scope_dropped = []

    # Сохраняем порядок глав из book_before. Если в book_after появились
    # in-scope главы которых не было в before — добавляем в конец.
    merged_chapters = []
    seen_ids = set()
    for ch_before in (book_before.get("chapters") or []):
        chid = ch_before.get("id")
        if not chid:
            continue
        seen_ids.add(chid)
        if chid in affected_set:
            ch_after = chapters_after_by_id.get(chid)
            if ch_after is not None:
                merged_chapters.append(copy.deepcopy(ch_after))
            else:
                # GW потерял главу из scope — восстанавливаем из before
                merged_chapters.append(copy.deepcopy(ch_before))
                chapters_restored.append({
                    "chapter_id": chid,
                    "reason": "in_scope_but_missing_in_after",
                    "chars_restored": len(ch_before.get("content") or ""),
                })
        else:
            ch_after = chapters_after_by_id.get(chid)
            chars_in_before = len(ch_before.get("content") or "")
            chars_in_after = len((ch_after or {}).get("content") or "")
            if ch_after is None or chars_in_after != chars_in_before or \
                    (ch_after.get("content") or "") != (ch_before.get("content") or ""):
                # Out-of-scope глава была изменена/удалена — восстанавливаем
                chapters_restored.append({
                    "chapter_id": chid,
                    "reason": "out_of_scope_modified",
                    "chars_before": chars_in_before,
                    "chars_after_gw": chars_in_after,
                    "chars_restored": chars_in_before,
                })
            merged_chapters.append(copy.deepcopy(ch_before))

    # Главы из book_after которых не было в book_before
    for ch_after in (book_after.get("chapters") or []):
        chid = ch_after.get("id")
        if not chid or chid in seen_ids:
            continue
        if chid in affected_set:
            merged_chapters.append(copy.deepcopy(ch_after))
            seen_ids.add(chid)
        else:
            # GW добавил главу вне scope — отбрасываем
            new_out_of_scope_dropped.append({
                "chapter_id": chid,
                "chars": len(ch_after.get("content") or ""),
            })
            seen_ids.add(chid)

    merged["chapters"] = merged_chapters

    # callouts: filter by chapter_id scope
    callouts_restored_count = _restore_chapter_scoped_items(
        merged, book_before, book_after, "callouts", affected_set, seen_ids
    )

    # historical_notes: filter by chapter_id scope
    notes_restored_count = _restore_chapter_scoped_items(
        merged, book_before, book_after, "historical_notes", affected_set, seen_ids
    )

    chars_after_merged = _book_total_chars(merged)
    chars_restored_total = sum(c["chars_restored"] for c in chapters_restored)

    details = {
        "scope_enforcement": "applied",
        "affected_chapters": list(affected_chapters),
        "chapters_restored": chapters_restored,
        "callouts_restored": callouts_restored_count,
        "historical_notes_restored": notes_restored_count,
        "new_out_of_scope_dropped": new_out_of_scope_dropped,
        "chars_before_total": chars_before_total,
        "chars_after_gw": chars_after_total,
        "chars_after_merged": chars_after_merged,
        "chars_restored": chars_restored_total,
    }

    return merged, details


def _restore_chapter_scoped_items(
    merged: dict,
    book_before: dict,
    book_after: dict,
    field: str,
    affected_set: set[str],
    valid_chapter_ids: set[str],
) -> int:
    """
    Helper для merge_revision_out_of_scope_chapters: восстанавливает
    out-of-scope элементы массива (callouts/historical_notes) по chapter_id.

    Логика:
      - Элементы с chapter_id вне affected_set: должны быть byte-identical
        с book_before. Если в book_after изменены/удалены — восстанавливаем
        ВСЕ соответствующие элементы из book_before.
      - Элементы с chapter_id в affected_set: pass-through из book_after.
      - Элементы без chapter_id (глобальные): pass-through из book_after.
      - Удаление дубликатов по id, если есть.

    Возвращает число восстановленных элементов.
    """
    items_before = book_before.get(field) or []
    items_after = book_after.get(field) or []

    in_scope_after = [
        it for it in items_after
        if (it.get("chapter_id") in affected_set) or (it.get("chapter_id") is None)
    ]

    out_of_scope_before = [
        it for it in items_before
        if it.get("chapter_id") and it.get("chapter_id") not in affected_set
    ]

    out_of_scope_after = [
        it for it in items_after
        if it.get("chapter_id") and it.get("chapter_id") not in affected_set
    ]

    # Сравниваем out-of-scope содержимое: если изменилось — restore из before
    out_of_scope_modified = (
        len(out_of_scope_before) != len(out_of_scope_after)
        or any(
            (b.get("id"), (b.get("text") or ""))
            != (a.get("id"), (a.get("text") or ""))
            for b, a in zip(out_of_scope_before, out_of_scope_after)
        )
    )

    if out_of_scope_modified:
        import copy
        merged_items = list(in_scope_after) + [copy.deepcopy(it) for it in out_of_scope_before]
        merged[field] = merged_items
        # Считаем сколько элементов реально вернули
        before_ids = {it.get("id") for it in out_of_scope_before if it.get("id")}
        after_ids = {it.get("id") for it in out_of_scope_after if it.get("id")}
        restored = len(before_ids - after_ids)
        # Если у элементов нет id, считаем по разнице длин
        if not before_ids and not after_ids:
            restored = max(0, len(out_of_scope_before) - len(out_of_scope_after))
        return restored

    return 0


def preserve_chapter_structural_fields(
    book_before_le: dict,
    book_after_le: dict,
    le_mutable_fields: tuple[str, ...] = ("content", "is_modified", "paragraphs"),
) -> tuple[dict, dict]:
    """
    Защита Этапа 1 (task 034): Literary Editor может изменять только
    `content` главы и `callouts/historical_notes` верхнего уровня. Все
    остальные структурные поля главы (`bio_data`, `timeline`, `facts_used`,
    `id`, `title`, `order`) программно копируются из book_before_le.

    История класса (v53b регрессия, 2026-05-08):
      Stage 2 GW v2.16 на TR2 правильно генерирует `chapters[ch_01].timeline`
      с 6 этапами жизни (1920-1933 детство, ..., 1994-2005 пенсия). Stage 3
      LE v3.0 возвращает главу без поля timeline (output schema LE не
      описывает структурные поля главы → модель их не возвращает →
      теряются). Результат: ch_01 в book_FINAL_stage3 пуст.

    Эта функция переводит защиту с промпт-уровня (ненадёжный) на код-уровень
    (детерминированный). LE v3.1 промпт явно описывает правило, но code
    копирование — гарантия независимо от того, послушалась ли модель.

    Алгоритм:
      Для каждой главы в book_after_le по id:
        - Берём соответствующую главу из book_before_le
        - Копируем все non-mutable поля из before → after
        - Mutable поля (content, is_modified, paragraphs) — оставляем из after
      Главы которые есть в before но нет в after — игнорируются (это другой
      класс проблем, scope merge задача).

    Args:
        book_before_le: snapshot book после Stage 2 (вход LE)
        book_after_le: book после LE (выход)
        le_mutable_fields: поля которые LE может изменять (default: content/
            is_modified/paragraphs)

    Returns:
        (merged_book, details):
            merged_book: dict — book_after_le с восстановленными
                структурными полями
            details: dict — что было восстановлено (диагностика)
    """
    import copy

    chapters_before_by_id = {
        ch.get("id"): ch
        for ch in (book_before_le.get("chapters") or [])
        if ch.get("id")
    }

    merged = copy.deepcopy(book_after_le)
    restorations: list[dict] = []

    for ch_after in merged.get("chapters") or []:
        chid = ch_after.get("id")
        if not chid:
            continue
        ch_before = chapters_before_by_id.get(chid)
        if not ch_before:
            continue

        restored_keys: list[str] = []
        for key, value in ch_before.items():
            if key in le_mutable_fields:
                continue
            if key not in ch_after or ch_after.get(key) != value:
                ch_after[key] = copy.deepcopy(value)
                restored_keys.append(key)

        if restored_keys:
            restorations.append({
                "chapter_id": chid,
                "restored_fields": restored_keys,
            })

    details = {
        "le_mutable_fields": list(le_mutable_fields),
        "chapters_with_restored_fields": len(restorations),
        "restorations": restorations,
    }

    if restorations:
        details["reason"] = (
            f"LE returned {len(restorations)} chapter(s) with missing or modified "
            f"structural fields (timeline / bio_data / facts_used / etc.). "
            f"Restored from book_before_le snapshot. v53b regression: LE v3.0 "
            f"dropped chapters[ch_01].timeline (6 etapas) — fixed by v3.1 prompt + "
            f"this programmatic copy."
        )

    return merged, details


def validate_revision_volume(
    book_before: dict,
    book_after: dict,
    fc_report: dict | None = None,
    min_ratio: float = REVISION_MIN_VOLUME_RATIO,
) -> tuple[bool, dict]:
    """
    Проверяет что после revision-вызова Ghostwriter объём контента не упал
    больше чем на (1 - min_ratio). Защита от регрессии #3 v43:
    GW «исправил» ошибку через удаление эпизода вместо корректировки факта.

    Снижение объёма допускается только если в fc_report есть errors с
    legitimate_deletion=true. Дополнительно (v1.2.3): для cross-chapter
    framing_distortion проверяется что evidence_in_other_chapter.quote
    реально присутствует в book_after — иначе FC галлюцинирует дубль
    (v47 регрессия #3 второй проявок).

    Возвращает (passed, details):
      passed: bool — True если объём допустим
      details: dict — chars_before, chars_after, ratio, threshold, verdict,
        legitimate_deletions (число помеченных эпизодов), evidence_failures

    Verdict'ы:
      - ok_within_threshold              — ratio >= min_ratio (нормальный revision)
      - ok_with_legitimate_deletion      — ratio < min_ratio + все evidence verified
      - blocked_unauthorized_deletion    — ratio < min_ratio + нет legitimate_deletion
      - blocked_phantom_evidence         — есть legitimate, но evidence не подтверждён
                                            в book_after или topic-overlap слишком мал
                                            (волна 1.3.1: семантическое тождество ≠ формальное)
    """
    chars_before = _book_total_chars(book_before)
    chars_after = _book_total_chars(book_after)

    if chars_before == 0:
        # Edge case: пустая исходная книга. Любой объём после OK.
        return True, {
            "chars_before": 0,
            "chars_after": chars_after,
            "ratio": None,
            "threshold": min_ratio,
            "reason": "empty_book_before",
        }

    ratio = chars_after / chars_before

    legitimate_deletions = []
    if fc_report:
        for err in fc_report.get("errors", []) or []:
            if err.get("legitimate_deletion") is True:
                legitimate_deletions.append({
                    "id": err.get("id"),
                    "chapter_id": err.get("chapter_id"),
                    "type": err.get("type"),
                    "fix_instruction": (err.get("fix_instruction") or "")[:120],
                    "evidence_in_other_chapter": err.get("evidence_in_other_chapter"),
                })

    details = {
        "chars_before": chars_before,
        "chars_after": chars_after,
        "ratio": round(ratio, 4),
        "threshold": min_ratio,
        "drop_chars": max(0, chars_before - chars_after),
        "legitimate_deletions_count": len(legitimate_deletions),
        "legitimate_deletions": legitimate_deletions,
        "evidence_failures": [],
    }

    # Шаг 1 (волна 1.3.1): evidence-check ВСЕГДА выполняется при наличии
    # legitimate_deletion=true, независимо от volume ratio. Это закрывает
    # пробел v49: маленькое удаление (300 chars / 2.3%) обходило evidence
    # проверку через ratio >= 0.95 → ok_within_threshold.
    if fc_report:
        for err in fc_report.get("errors", []) or []:
            if err.get("legitimate_deletion") is True:
                ev_passed, ev_reason, topic_overlap = _verify_evidence_in_book(err, book_after)
                if not ev_passed:
                    details["evidence_failures"].append({
                        "error_id": err.get("id"),
                        "reason": ev_reason,
                        "topic_overlap": topic_overlap,
                    })

    if details["evidence_failures"]:
        details["verdict"] = "blocked_phantom_evidence"
        details["reason"] = (
            f"{len(details['evidence_failures'])} legitimate_deletion-flag(s) не "
            f"подтверждены: либо evidence quote отсутствует в book_after, либо "
            f"topic-overlap с удаляемым фрагментом ниже {EVIDENCE_TOPIC_OVERLAP_MIN}. "
            f"FC v2.12 требует не только наличие quote, но и совпадение по "
            f"конкретному эпизоду (волна 1.3.1: защита от семантического "
            f"тождества разных эпизодов одной темы, v49 регрессия)."
        )
        return False, details

    # Шаг 2: volume threshold check (как было)
    if ratio >= min_ratio:
        details["verdict"] = "ok_within_threshold"
        return True, details

    if not legitimate_deletions:
        details["verdict"] = "blocked_unauthorized_deletion"
        details["reason"] = (
            f"Объём после revision упал на {details['drop_chars']} символов "
            f"({(1 - ratio) * 100:.1f}%), порог снижения {(1 - min_ratio) * 100:.1f}%. "
            f"FC отчёт не содержит errors с legitimate_deletion=true. "
            f"GW нарушил anti-deletion правило (GW v2.15)."
        )
        return False, details

    # Шаг 3: ratio < min_ratio + есть legitimate_deletions + evidence все verified
    details["verdict"] = "ok_with_legitimate_deletion"
    return True, details


# ─────────────────────────────────────────────────────────────────
# Stage 2: Фактчекер
# ─────────────────────────────────────────────────────────────────

def run_fact_checker(client, book_draft: dict, fact_map: dict,
                     transcripts: list[dict], project_id: str,
                     phase: str = "A", iteration: int = 1,
                     max_iterations: int = 3,
                     affected_chapters: list[str] | None = None,
                     historical_context: dict | list | None = None,
                     cfg: dict | None = None) -> dict:
    """
    Запускает Фактчекера.

    historical_context (волна 1.3): output Историка-краеведа (агент 12).
    Принимает либо dict {"historical_context": [...], "era_glossary": [...]} —
    точно как возвращает run_historian — либо распакованный список contextов.
    FC v2.11+ использует это как ТРЕТИЙ валидный источник наряду с transcript
    и fact_map. Текст в book.chapter, совпадающий с historian.suggested_insertions,
    НЕ помечается как hallucination. До v2.11 параметр игнорировался.

    Возвращает отчёт с verdict ("pass" | "fail") и списком ошибок.
    """
    if cfg is None:
        cfg = load_config()

    fc_cfg = cfg["fact_checker"]
    model = fc_cfg["model"]
    max_tokens = fc_cfg["max_tokens"]
    temperature = fc_cfg.get("temperature", 0.1)
    system_prompt = load_prompt(fc_cfg["prompt_file"])

    print(f"\n[FACT_CHECKER] Запускаю ({model}, max_tokens={max_tokens}, iteration={iteration}/{max_iterations})...")
    start = datetime.now()

    user_message = {
        "phase": phase,
        "project_id": project_id,
        "iteration": iteration,
        "max_iterations": max_iterations,
        "book_draft": book_draft,
        "fact_map": fact_map,
        "transcripts": transcripts,
    }
    if affected_chapters is not None:
        user_message["affected_chapters"] = affected_chapters
    if historical_context:
        # Распаковка как в run_ghostwriter: dict-обёртку разворачиваем,
        # список — как есть, прочее — в список.
        if isinstance(historical_context, dict) and "historical_context" in historical_context:
            user_message["historical_context"] = historical_context["historical_context"]
            if historical_context.get("era_glossary"):
                user_message["era_glossary"] = historical_context["era_glossary"]
        elif isinstance(historical_context, list):
            user_message["historical_context"] = historical_context
        else:
            user_message["historical_context"] = [historical_context]
        n_ctx = len(user_message.get("historical_context") or [])
        print(f"[FACT_CHECKER] historical_context передан: {n_ctx} контекстных блоков "
              f"(FC v2.11+ использует как третий источник вместе с transcript и fact_map).")

    # Streaming — обязательно при max_tokens >= 16000
    raw_parts = []
    with client.messages.stream(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system_prompt,
        messages=[{"role": "user", "content": json.dumps(user_message, ensure_ascii=False)}]
    ) as stream:
        for text in stream.text_stream:
            raw_parts.append(text)
        final_msg = stream.get_final_message()
    elapsed = (datetime.now() - start).total_seconds()
    raw = "".join(raw_parts).strip()
    print(f"[FACT_CHECKER] Готово за {elapsed:.1f}с | токены: in={final_msg.usage.input_tokens}, out={final_msg.usage.output_tokens}")

    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:])
        if raw.endswith("```"):
            raw = raw[:-3].strip()
    s = raw.find("{")
    e = raw.rfind("}")
    if s != -1 and e > s:
        try:
            return json.loads(raw[s:e + 1])
        except Exception:
            pass
    return json.loads(raw)


def print_fact_check_report(report: dict):
    """Выводит отчёт Фактчекера в читаемом виде."""
    verdict = report.get("verdict", "?")
    symbol = "✅" if verdict == "pass" else "❌"
    summary = report.get("summary", {})

    print("\n" + "=" * 60)
    print(f"ОТЧЁТ ФАКТЧЕКЕРА  {symbol} {verdict.upper()}")
    print("=" * 60)
    print(f"  Critical: {summary.get('critical_errors', 0)}")
    print(f"  Major:    {summary.get('major_errors', 0)}")
    print(f"  Minor:    {summary.get('minor_errors', 0)}")
    print(f"  Warnings: {summary.get('warnings_count', 0)}")
    print(f"\n  {summary.get('overall_assessment', '')}")

    errors = report.get("errors", [])
    if errors:
        print(f"\n  ОШИБКИ ({len(errors)}):")
        for err in errors:
            sev = err.get("severity", "?").upper()
            etype = err.get("type", "?")
            chapter = err.get("chapter_id", "?")
            print(f"  [{sev}] [{etype}] {chapter}: {err.get('what_is_written', '')[:70]}")
            print(f"    → {err.get('fix_instruction', '')[:80]}")

    completeness = report.get("completeness_check", {})
    if completeness:
        total = completeness.get("total_facts_in_map", 0)
        referenced = completeness.get("facts_referenced_in_text", 0)
        ok = completeness.get("facts_verified_ok", 0)
        missing = completeness.get("facts_missing_from_text", [])
        print(f"\n  ПОЛНОТА: {referenced}/{total} фактов в тексте, {ok} проверены OK, {len(missing)} пропущено")


def print_book_stats(book_draft: dict):
    """Выводит статистику черновика книги."""
    chapters = book_draft.get("chapters", [])
    callouts = book_draft.get("callouts", [])
    hist_notes = book_draft.get("historical_notes", [])
    writing_notes = book_draft.get("writing_notes", {})
    total_chars = sum(len(ch.get("content") or "") for ch in chapters)

    print("\n" + "=" * 60)
    print("СТАТИСТИКА ЧЕРНОВИКА КНИГИ")
    print("=" * 60)
    print(f"  Глав: {len(chapters)} | Выносок: {len(callouts)} | Ист.вставок: {len(hist_notes)}")
    print(f"  Общий объём: {total_chars} символов")
    print(f"  Фактов использовано: {writing_notes.get('facts_incorporated', '?')} из {writing_notes.get('total_facts_in_map', '?')}")

    for ch in chapters:
        ch_len = len(ch.get("content") or "")
        facts = len(ch.get("facts_used", []))
        modified = " [modified]" if ch.get("is_modified") else ""
        print(f"    {ch['id']}: {ch.get('title', '')} — {ch_len} симв, {facts} фактов{modified}")

    omitted = writing_notes.get("facts_omitted", [])
    if omitted:
        print(f"\n  Пропущено фактов ({len(omitted)}):")
        for o in omitted[:5]:
            print(f"    - {o.get('fact_id', '?')}: {o.get('reason', '')[:60]}")


# ─────────────────────────────────────────────────────────────────
# Общий вывод статистики
# ─────────────────────────────────────────────────────────────────

def print_stats(fact_map: dict, cleaned_text: str, label: str = ""):
    print("\n" + "=" * 60)
    print(f"СТАТИСТИКА FACT_MAP{(' — ' + label) if label else ''}")
    print("=" * 60)

    notes = fact_map.get("processing_notes", {})
    persons = fact_map.get("persons", [])
    timeline = fact_map.get("timeline", [])
    quotes = fact_map.get("quotes", [])
    gaps = fact_map.get("gaps", [])
    traits = fact_map.get("character_traits", [])
    locations = fact_map.get("locations", [])
    conflicts = fact_map.get("conflicts", [])

    direct_quotes = [q for q in quotes if q.get("type") == "direct"]
    indirect_quotes = [q for q in quotes if q.get("type") == "indirect"]
    usable_quotes = [q for q in quotes if q.get("usable_in_book")]

    print(f"  Всего фактов:          {notes.get('total_facts_extracted', '?')}")
    print(f"  Персон:                {len(persons)}")
    print(f"  Событий:               {len(timeline)}")
    print(f"  Мест:                  {len(locations)}")
    print(f"  Черт характера:        {len(traits)}")
    print(f"  Цитат всего:           {len(quotes)}")
    print(f"    - прямых (direct):   {len(direct_quotes)}")
    print(f"    - косвенных:         {len(indirect_quotes)}")
    print(f"    - usable_in_book:    {len(usable_quotes)}")
    print(f"  Пробелов (gaps):       {len(gaps)}")
    print(f"  Противоречий:          {len(conflicts)}")
    print(f"  Длина cleaned_text:    {len(cleaned_text)}")

    subject = fact_map.get("subject", {})
    print(f"\n  Субъект:    {subject.get('name')} ({subject.get('birth_year')}–{subject.get('death_year', '?')})")
    print(f"  Родился(ась): {subject.get('birth_place')}")

    print(f"\n  Персоны:")
    for p in persons:
        ver = " [?]" if p.get("needs_verification") else ""
        print(f"    {p['id']} | {p['name']}{ver} | {p.get('relation_to_subject', '')}")

    print(f"\n  Цитаты:")
    for q in quotes:
        t = q.get("type", "?")
        v = "[usable]" if q.get("usable_in_book") else ""
        print(f"    [{t}] {v} \"{q.get('text', '')[:80]}\"")

    print(f"\n  Gaps:")
    for g in gaps:
        trigger = g.get("trigger", "")
        print(f"    - {g.get('period')}: {g.get('description', '')[:60]}")
        if trigger:
            print(f"      trigger: {trigger[:60]}")
        for q_text in g.get("suggested_questions", [])[:2]:
            print(f"      ? {q_text[:70]}")

    if conflicts:
        print(f"\n  Противоречия:")
        for c in conflicts:
            print(f"    [{c.get('severity', '?')}] {c.get('description', '')[:80]}")


# ─────────────────────────────────────────────────────────────────
# Stage 3: Literary Editor
# ─────────────────────────────────────────────────────────────────

def run_literary_editor(client, book_draft: dict, fact_checker_warnings: list,
                        project_id: str, phase: str = "A",
                        cfg: dict | None = None) -> dict:
    """
    Запускает Литературного редактора.
    Возвращает отредактированный черновик книги (dict с chapters).
    """
    if cfg is None:
        cfg = load_config()

    le_cfg = cfg["literary_editor"]
    model = le_cfg["model"]
    max_tokens = le_cfg["max_tokens"]
    temperature = le_cfg.get("temperature", 0.5)
    system_prompt = load_prompt(le_cfg["prompt_file"])

    print(f"\n[LITERARY_EDITOR] Запускаю ({model}, max_tokens={max_tokens})...")
    start = datetime.now()

    user_message = {
        "phase": phase,
        "project_id": project_id,
        "call_type": "initial",
        "book_draft": book_draft,
        "fact_checker_warnings": fact_checker_warnings,
    }

    raw_parts = []
    input_tokens = output_tokens = 0
    with client.messages.stream(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system_prompt,
        messages=[{"role": "user", "content": json.dumps(user_message, ensure_ascii=False)}]
    ) as stream:
        for text in stream.text_stream:
            raw_parts.append(text)
        final_msg = stream.get_final_message()
        input_tokens = final_msg.usage.input_tokens
        output_tokens = final_msg.usage.output_tokens

    elapsed = (datetime.now() - start).total_seconds()
    raw = "".join(raw_parts).strip()
    print(f"[LITERARY_EDITOR] Готово за {elapsed:.1f}с | токены: in={input_tokens}, out={output_tokens}")

    if output_tokens >= max_tokens - 10:
        print(f"[LITERARY_EDITOR] WARNING: output_tokens близко к max_tokens — возможное обрезание")

    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:])
        if raw.endswith("```"):
            raw = raw[:-3].strip()
    s = raw.find("{")
    e = raw.rfind("}")
    if s != -1 and e > s:
        try:
            result = json.loads(raw[s:e + 1])
        except Exception:
            result = json.loads(raw)
    else:
        result = json.loads(raw)

    _auto_checkpoint(project_id, "liteditor", result)
    return result


# ─────────────────────────────────────────────────────────────────
# Stage 4: Proofreader
# ─────────────────────────────────────────────────────────────────

def run_proofreader(client, book_draft: dict, project_id: str,
                   cfg: dict | None = None) -> dict:
    """
    Запускает Корректора.
    Возвращает финальный проверенный текст книги (dict с chapters).
    """
    if cfg is None:
        cfg = load_config()

    pr_cfg = cfg["proofreader"]
    model = pr_cfg["model"]
    max_tokens = pr_cfg["max_tokens"]
    temperature = pr_cfg.get("temperature", 0.0)
    system_prompt = load_prompt(pr_cfg["prompt_file"])

    print(f"\n[PROOFREADER] Запускаю ({model}, max_tokens={max_tokens})...")
    start = datetime.now()

    user_message = {
        "project_id": project_id,
        "book_draft": book_draft,
    }

    raw_parts = []
    input_tokens = output_tokens = 0
    with client.messages.stream(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system_prompt,
        messages=[{"role": "user", "content": json.dumps(user_message, ensure_ascii=False)}]
    ) as stream:
        for text in stream.text_stream:
            raw_parts.append(text)
        final_msg = stream.get_final_message()
        input_tokens = final_msg.usage.input_tokens
        output_tokens = final_msg.usage.output_tokens

    elapsed = (datetime.now() - start).total_seconds()
    raw = "".join(raw_parts).strip()
    print(f"[PROOFREADER] Готово за {elapsed:.1f}с | токены: in={input_tokens}, out={output_tokens}")

    if output_tokens >= max_tokens - 10:
        print(f"[PROOFREADER] WARNING: output_tokens близко к max_tokens — возможное обрезание")

    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:])
        if raw.endswith("```"):
            raw = raw[:-3].strip()
    s = raw.find("{")
    e = raw.rfind("}")
    if s != -1 and e > s:
        try:
            result = json.loads(raw[s:e + 1])
        except Exception:
            result = json.loads(raw)
    else:
        result = json.loads(raw)

    _auto_checkpoint(project_id, "proofreader", result)
    return result


# ══════════════════════════════════════════════════════════════════════════════
# BATCH 2 — Tasks 044, 045, 043, 038, 041
# ══════════════════════════════════════════════════════════════════════════════

# ─── Task 044: Relation overrides + persona notes preservation ─────────────

def apply_relation_overrides(fact_map: dict, overrides_config: dict) -> tuple:
    """Task 044: корректировать relation_to_subject в fact_map.persons по ручным overrides.

    Применяется ДО filter_bio_data_family_by_relation_whitelist, чтобы whitelist
    получил уже скорректированные relation'ы (тётя Маша = соседка → будет отфильтрована).

    Returns (patched_fact_map, corrections_list).
    """
    import copy
    fact_map = copy.deepcopy(fact_map)
    corrections = []

    overrides = overrides_config.get("overrides", [])
    if not overrides:
        return fact_map, corrections

    persons = fact_map.get("persons", [])
    for person in persons:
        name = (person.get("name") or "").strip()
        if not name:
            continue
        for override in overrides:
            canonical_name = override.get("person_name", "")
            aliases = [canonical_name] + override.get("aliases", [])
            matched = any(
                alias.lower() in name.lower() or name.lower() in alias.lower()
                for alias in aliases
            )
            if not matched:
                continue

            old_relation = person.get("relation_to_subject") or person.get("relation") or ""
            new_relation = override.get("real_relation", old_relation)
            in_family = override.get("in_bio_data_family", True)

            if old_relation != new_relation or person.get("in_bio_data_family") != in_family:
                corrections.append({
                    "person_name": name,
                    "ca_relation": old_relation,
                    "real_relation": new_relation,
                    "in_bio_data_family": in_family,
                })
                person["relation_to_subject"] = new_relation
                person["relation"] = new_relation
                person["relation_corrected"] = True
                person["in_bio_data_family"] = in_family
                print(
                    f"[RELATION-OVERRIDE] «{name}»: «{old_relation}» → «{new_relation}» "
                    f"(in_family={in_family})"
                )

    print(f"[RELATION-OVERRIDE] Скорректировано {len(corrections)} персон из {len(persons)}.")
    return fact_map, corrections


def enforce_persona_notes(book: dict, persona_notes_config: dict) -> tuple:
    """Task 044: зафиксировать обязательные notes в bio_data.family и разделить склеенные записи.

    Вызывать ПОСЛЕ enforce_bio_data_completeness и filter_bio_data_family_by_relation_whitelist.
    Returns (patched_book, enforcement_log).
    """
    import copy
    book = copy.deepcopy(book)
    log = []

    chapters = book.get("chapters", [])
    ch01 = next((ch for ch in chapters if ch.get("id") == "ch_01"), None)
    if ch01 is None:
        return book, log

    bio_data = ch01.get("bio_data") or {}
    family = bio_data.get("family")
    if not family:
        return book, log

    required_notes = persona_notes_config.get("required_notes", [])
    separate_required = persona_notes_config.get("separate_entries_required", [])

    # Step 1: enforce required notes
    for rule in required_notes:
        label_match = rule.get("label_match", "").lower()
        required_note = rule.get("note", "")
        note_keywords = [kw.lower() for kw in rule.get("note_keywords", [])]
        policy = rule.get("replacement_policy", "replace_if_missing")

        for entry in family:
            entry_value = (entry.get("value") or "").lower()
            entry_label = (entry.get("label") or "").lower()
            if label_match not in entry_value and label_match not in entry_label:
                continue

            current_note = (entry.get("note") or "").strip()
            note_present = any(kw in current_note.lower() for kw in note_keywords) if note_keywords else bool(current_note)

            if policy == "replace_if_conflict":
                if not note_present:
                    old_note = current_note
                    entry["note"] = required_note
                    log.append({
                        "action": "replaced_note",
                        "label_match": label_match,
                        "old_note": old_note,
                        "new_note": required_note,
                        "entry_value": entry.get("value", ""),
                    })
                    print(f"[PERSONA-NOTES] «{label_match}»: note заменён «{old_note[:40]}» → «{required_note}»")
            elif policy in ("replace_if_missing", "append_if_missing"):
                if not note_present:
                    old_note = current_note
                    if policy == "append_if_missing" and current_note:
                        entry["note"] = f"{current_note}; {required_note}"
                    else:
                        entry["note"] = required_note
                    log.append({
                        "action": "set_note",
                        "label_match": label_match,
                        "old_note": old_note,
                        "new_note": entry["note"],
                        "entry_value": entry.get("value", ""),
                    })
                    print(f"[PERSONA-NOTES] «{label_match}»: note установлен «{entry['note']}»")

    # Step 2: split merged entries (e.g. "Внуки: Никита, Даша" → separate)
    new_family = []
    for entry in family:
        entry_label = (entry.get("label") or "").lower()
        entry_value = (entry.get("value") or "")
        split_done = False
        for sep_rule in separate_required:
            pattern = sep_rule.get("merged_label_pattern", "").lower()
            if pattern not in entry_label:
                continue
            split_into = sep_rule.get("split_into", [])
            found_parts = []
            for part in split_into:
                kw = part.get("value_keyword", "")
                if kw.lower() in entry_value.lower():
                    found_parts.append((part["label"], kw))
            if len(found_parts) >= 2:
                for lbl, val in found_parts:
                    new_entry = dict(entry)
                    new_entry["label"] = lbl
                    new_entry["value"] = val
                    new_family.append(new_entry)
                log.append({
                    "action": "split_entry",
                    "original_label": entry.get("label"),
                    "original_value": entry_value,
                    "split_into": [{"label": l, "value": v} for l, v in found_parts],
                })
                print(f"[PERSONA-NOTES] Разделена запись «{entry.get('label')}»: {[v for _, v in found_parts]}")
                split_done = True
                break
        if not split_done:
            new_family.append(entry)

    bio_data["family"] = new_family
    ch01["bio_data"] = bio_data
    print(f"[PERSONA-NOTES] Применено {len(log)} изменений. Семья: {len(new_family)} записей.")
    return book, log


# ─── Task 045: Timeline structural anchors ────────────────────────────────

def _extract_bio_data_timeline(book: dict) -> list:
    """Извлечь периоды из bio_data.timeline или из ch_01.content (markdown)."""
    import re
    chapters = book.get("chapters", [])
    ch01 = next((ch for ch in chapters if ch.get("id") == "ch_01"), None)
    if ch01 is None:
        return []

    bio_data = ch01.get("bio_data") or {}
    timeline = bio_data.get("timeline", [])
    if timeline:
        return timeline

    # Fallback: parse markdown periods from ch_01.content
    content = ch01.get("content") or ""
    periods = []
    for match in re.finditer(r"\*\*(\d{4}[–\-–—]\d{4}[^*]*?)\*\*[.\s]*([^\n*]*)", content):
        title_raw = match.group(1).strip()
        text_snippet = match.group(2).strip()
        periods.append({"title": title_raw, "text": text_snippet, "source": "markdown"})
    return periods


def _parse_markdown_timeline_periods(ch01_content: str) -> list:
    """Task 045b: извлечь периоды биографии из markdown **YYYY[-YYYY]. Title** в ch_01.content."""
    import re
    if not ch01_content:
        return []
    # Match **1920–1933. Детство и сиротство** or **1962. Работа** etc.
    PERIOD_RE = re.compile(
        r"\*\*(\d{4}(?:[–\-]\d{4})?)[.\s]+([^*\n]+)\*\*",
        re.MULTILINE,
    )
    periods = []
    for m in PERIOD_RE.finditer(ch01_content):
        year_range = m.group(1).strip()
        title = m.group(2).strip()
        periods.append({"title": f"{year_range}. {title}", "year_range": year_range, "source": "markdown"})
    return periods


def validate_timeline_anchors(book: dict, anchors_config: dict) -> dict:
    """Task 045/045b: проверить bio_data.timeline на наличие всех обязательных anchor-периодов.

    Falls back to parsing **YYYY. Title** markdown in ch_01.content if JSON array is empty.
    Returns {anchors_found, anchors_missing, merges, issues_count}.
    Idempotent — только чтение, не изменяет book.
    """
    import re
    anchors = anchors_config.get("anchors", [])
    min_periods = anchors_config.get("min_periods", len(anchors))

    periods = _extract_bio_data_timeline(book)

    chapters = book.get("chapters", [])
    ch01 = next((ch for ch in chapters if ch.get("id") == "ch_01"), None)
    ch01_content = ""
    if ch01:
        ch01_content = (ch01.get("content") or "") + " ".join(
            p.get("text", "") for p in ch01.get("paragraphs", [])
        )

    # Task 045b: fallback to markdown parsing if JSON array is empty or too small
    markdown_periods = _parse_markdown_timeline_periods(ch01_content)
    if len(periods) < min_periods and len(markdown_periods) >= len(periods):
        print(f"[TIMELINE-ANCHORS] JSON array={len(periods)} < min={min_periods}, "
              f"fallback → markdown parsing ({len(markdown_periods)} periods found)")
        periods = markdown_periods

    full_text = ch01_content

    found_anchor_ids = []
    missing_anchor_ids = []
    merges = []

    for anchor in anchors:
        anchor_id = anchor["anchor_id"]
        title_keywords = [kw.lower() for kw in anchor.get("title_keywords", [])]

        matched_period = None
        for period in periods:
            period_text = (
                (period.get("title") or "") + " " + (period.get("text") or "")
            ).lower()
            if any(kw in period_text for kw in title_keywords):
                matched_period = period
                break

        if matched_period is None:
            if any(kw in full_text.lower() for kw in title_keywords):
                matched_period = {"title": "found_in_content", "source": "content_search"}

        if matched_period is not None:
            found_anchor_ids.append(anchor_id)
        else:
            missing_anchor_ids.append(anchor_id)
            print(f"[TIMELINE-ANCHORS] ⚠️ Anchor отсутствует: {anchor_id} (keywords={title_keywords[:2]})")

    # Detect merges: two merge-forbidden anchors in same period
    for period in periods:
        period_text = (
            (period.get("title") or "") + " " + (period.get("text") or "")
        ).lower()
        period_matched_anchors = []
        for anchor in anchors:
            title_keywords = [kw.lower() for kw in anchor.get("title_keywords", [])]
            if any(kw in period_text for kw in title_keywords):
                period_matched_anchors.append(anchor["anchor_id"])

        if len(period_matched_anchors) >= 2:
            for a1 in period_matched_anchors:
                a1_spec = next((a for a in anchors if a["anchor_id"] == a1), {})
                for a2 in period_matched_anchors:
                    if a1 >= a2:
                        continue
                    if a2 in a1_spec.get("merge_forbidden_with", []):
                        merges.append({
                            "period_title": period.get("title", "?"),
                            "merged_anchor_ids": [a1, a2],
                            "severity": "error",
                        })
                        print(
                            f"[TIMELINE-ANCHORS] ❌ MERGE: {a1} + {a2} "
                            f"в периоде «{period.get('title', '?')}»"
                        )

    total_periods = len(periods)
    # v62a-045e: strict period separation check for overlapping year_ranges
    absorbed = []
    for anchor_a in anchors:
        yr_a = anchor_a.get("year_range", "")
        for anchor_b in anchors:
            if anchor_a["anchor_id"] >= anchor_b["anchor_id"]:
                continue
            yr_b = anchor_b.get("year_range", "")
            # Parse year ranges
            def _parse_yr(yr: str):
                import re as _re2
                m = _re2.match(r'(\d{4})-(\d{4})', yr)
                return (int(m.group(1)), int(m.group(2))) if m else (None, None)
            a_start, a_end = _parse_yr(yr_a)
            b_start, b_end = _parse_yr(yr_b)
            if None in (a_start, a_end, b_start, b_end):
                continue
            # Check overlap
            overlap = min(a_end, b_end) - max(a_start, b_start)
            if overlap <= 0:
                continue
            # Both must appear as separate **YYYY-YYYY. Title** blocks in ch_01.content
            PERIOD_BLOCK_RE = re.compile(r'\*\*(\d{4})(?:[–\-](\d{4}))?\.\s+([^*]+)\*\*')
            blocks_in_content = PERIOD_BLOCK_RE.findall(ch01_content)
            # Check if anchor_a keywords and anchor_b keywords each match a distinct block
            a_kws = [kw.lower() for kw in anchor_a.get("title_keywords", [])]
            b_kws = [kw.lower() for kw in anchor_b.get("title_keywords", [])]
            a_block = next(
                (b for b in blocks_in_content if any(kw in b[2].lower() for kw in a_kws)), None
            )
            b_block = next(
                (b for b in blocks_in_content if any(kw in b[2].lower() for kw in b_kws)), None
            )
            if a_block and b_block and a_block == b_block:
                absorbed.append({
                    "absorbed_anchor": anchor_b["anchor_id"],
                    "absorbing_anchor": anchor_a["anchor_id"],
                    "shared_block_title": a_block[2],
                    "severity": "error",
                })
                print(
                    f"[TIMELINE-ANCHORS] ⚠️ ABSORBED: {anchor_b['anchor_id']} absorbed into "
                    f"{anchor_a['anchor_id']} block «{a_block[2][:40]}»"
                )
            elif (a_block is None or b_block is None) and overlap > 0:
                # One of the anchors present only in content search, not as distinct block
                # Already flagged as missing above; no duplicate flag needed
                pass

    report = {
        "anchors_found": found_anchor_ids,
        "anchors_missing": missing_anchor_ids,
        "merges": merges,
        "absorbed": absorbed,
        "total_periods_found": total_periods,
        "min_periods_required": min_periods,
        "issues_count": len(missing_anchor_ids) + len(merges) + len(absorbed),
        "period_count_ok": total_periods >= min_periods,
    }
    print(
        f"[TIMELINE-ANCHORS] Found={len(found_anchor_ids)}/{len(anchors)}, "
        f"Missing={len(missing_anchor_ids)}, Merges={len(merges)}, "
        f"Periods={total_periods}/{min_periods}"
    )
    return report


def enforce_timeline_anchors(book: dict, anchors_config: dict, fact_map: dict) -> tuple:
    """Task 045: автоматически разделить склеенные периоды если оба контента явно присутствуют.

    Auto-split ТОЛЬКО если оба anchor contents явно присутствуют в склеенном периоде.
    Иначе — flag, не патчить.
    Returns (patched_book, enforcement_report).
    """
    import copy
    book = copy.deepcopy(book)
    report = {"actions": [], "skipped": []}

    validation = validate_timeline_anchors(book, anchors_config)
    if not validation["merges"]:
        return book, report

    chapters = book.get("chapters", [])
    ch01 = next((ch for ch in chapters if ch.get("id") == "ch_01"), None)
    if ch01 is None:
        return book, report

    bio_data = ch01.get("bio_data") or {}
    timeline = bio_data.get("timeline", [])
    if not timeline:
        report["skipped"].append({
            "reason": "no_structured_timeline",
            "detail": "timeline field empty; auto-split requires structured data",
        })
        return book, report

    anchors_by_id = {a["anchor_id"]: a for a in anchors_config.get("anchors", [])}
    new_timeline = []

    for period in timeline:
        period_text = ((period.get("title") or "") + " " + (period.get("text") or "")).lower()
        period_matched_anchors = [
            aid for aid, anchor in anchors_by_id.items()
            if any(kw.lower() in period_text for kw in anchor.get("title_keywords", []))
        ]

        split_performed = False
        for a1 in period_matched_anchors:
            a1_spec = anchors_by_id.get(a1, {})
            for a2 in period_matched_anchors:
                if a1 >= a2 or a2 not in a1_spec.get("merge_forbidden_with", []):
                    continue

                a1_kws = [kw.lower() for kw in anchors_by_id[a1].get("required_events", [])]
                a2_kws = [kw.lower() for kw in anchors_by_id[a2].get("required_events", [])]
                period_text_full = period.get("text") or ""
                text_lower = period_text_full.lower()

                a1_present = sum(1 for kw in a1_kws if any(w in text_lower for w in kw.split())) >= max(1, len(a1_kws) // 2)
                a2_present = sum(1 for kw in a2_kws if any(w in text_lower for w in kw.split())) >= max(1, len(a2_kws) // 2)

                if not (a1_present and a2_present):
                    report["skipped"].append({
                        "reason": "insufficient_content_for_split",
                        "period_title": period.get("title"),
                        "merged_anchors": [a1, a2],
                        "a1_content_present": a1_present,
                        "a2_content_present": a2_present,
                    })
                    print(
                        f"[TIMELINE-ANCHORS] ⚠️ Auto-split невозможен для «{period.get('title')}» "
                        f"— нет контента для {a1 if not a1_present else a2}. Human review needed."
                    )
                    new_timeline.append(period)
                    split_performed = True
                    break

                a1_anchor = anchors_by_id[a1]
                a2_anchor = anchors_by_id[a2]
                period_1 = {
                    "title": f"{a1_anchor.get('year_range', '')}. {a1_anchor['title_keywords'][0].capitalize()}",
                    "text": period_text_full,
                    "source": f"auto-split from: {period.get('title')}",
                    "anchor_id": a1,
                }
                period_2 = {
                    "title": f"{a2_anchor.get('year_range', '')}. {a2_anchor['title_keywords'][0].capitalize()}",
                    "text": period_text_full,
                    "source": f"auto-split from: {period.get('title')}",
                    "anchor_id": a2,
                }
                new_timeline.extend([period_1, period_2])
                report["actions"].append({
                    "action": "split",
                    "original_title": period.get("title"),
                    "split_into": [period_1["title"], period_2["title"]],
                    "merged_anchors": [a1, a2],
                })
                print(
                    f"[TIMELINE-ANCHORS] ✅ Auto-split: «{period.get('title')}» → "
                    f"[«{period_1['title']}», «{period_2['title']}»]"
                )
                split_performed = True
                break
            if split_performed:
                break

        if not split_performed:
            new_timeline.append(period)

    bio_data["timeline"] = new_timeline
    ch01["bio_data"] = bio_data
    return book, report


# ─── Task 043: Epilogue stop-phrases + paspart format + Class 11 awkward ──

def _lemmatize_pattern(phrase: str) -> str:
    """Task 043b: грубая лемматизация — добавляет \\w{0,4} к словам с флективными суффиксами."""
    import re
    VOWELS = "аеиоыуяюэёАЕИОЫУЯЮЭЁ"
    words = phrase.split()
    pat = []
    for w in words:
        if len(w) >= 5 and w[-1] in VOWELS:
            pat.append(re.escape(w[:-1]) + r"\w{0,4}")
        else:
            pat.append(re.escape(w))
    return r"\b" + r"\s+".join(pat) + r"\b"


def validate_epilogue_stop_phrases(book: dict, stop_list_config: dict) -> dict:
    """Task 043/043b: проверить epilogue и нарративные главы на пластиковые шаблонные фразы (Класс 6).

    Поддерживает как literal substring, так и regex patterns (суффикс-aware через _lemmatize_pattern).
    Returns {issues: [...], errors_count, warnings_count}.
    Idempotent — только чтение.
    """
    import re as _re
    phrases = stop_list_config.get("generic_stop_phrases", [])
    # Task 043b: generic_categorical_patterns with precompiled regex
    categorical = stop_list_config.get("generic_categorical_patterns", [])
    scoped_error = set(stop_list_config.get("scoped_chapter_ids", ["epilogue"]))
    scoped_warning = set(stop_list_config.get("extra_general_scope", []))
    severity_map = stop_list_config.get("severity_map", {})

    # Pre-compile categorical patterns scoped to epilogue
    epilogue_categories = set(stop_list_config.get("scoped_to_epilogue_only", []))

    issues = []
    chapters = book.get("chapters", [])

    all_scoped = scoped_error | scoped_warning
    for chapter in chapters:
        ch_id = chapter.get("id") or ""
        if ch_id not in all_scoped and "epilogue" not in ch_id.lower():
            continue

        content = chapter.get("content") or ""
        paragraphs = chapter.get("paragraphs", [])
        full_text = content + " " + " ".join(p.get("text", "") for p in paragraphs)
        full_text_lower = full_text.lower()

        def _add_issue(phrase_label, severity_default):
            severity = severity_map.get(ch_id, "error" if ch_id in scoped_error else severity_default)
            issues.append({"phrase": phrase_label, "chapter_id": ch_id, "severity": severity})

        # Literal phrases (with lemmatize-aware regex)
        for phrase in phrases:
            try:
                pat = _lemmatize_pattern(phrase)
                if _re.search(pat, full_text, _re.IGNORECASE):
                    _add_issue(phrase, "warning")
            except Exception:
                if phrase.lower() in full_text_lower:
                    _add_issue(phrase, "warning")

        # Categorical patterns
        is_epilogue = "epilogue" in ch_id.lower() or ch_id in scoped_error
        for cat in categorical:
            category = cat.get("category", "?")
            if category in epilogue_categories and not is_epilogue:
                continue
            pattern = cat.get("pattern") or cat.get("pattern_regex")
            if not pattern:
                continue
            try:
                if _re.search(pattern, full_text, _re.IGNORECASE):
                    _add_issue(f"[cat:{category}]", "warning" if not is_epilogue else "error")
            except Exception:
                pass

    errors = sum(1 for i in issues if i["severity"] == "error")
    warnings = sum(1 for i in issues if i["severity"] == "warning")
    print(f"[EPILOGUE-STOP] {errors} errors + {warnings} warnings по {len(phrases)} фразам + {len(categorical)} категориям.")
    return {"issues": issues, "errors_count": errors, "warnings_count": warnings}


def validate_awkward_formulation(book: dict) -> dict:
    """Task 043: Класс 11 — частный пример вместо обобщения.

    Returns {issues: [...], issues_count}.
    """
    import re
    patterns = [
        r"не\s+любил[аи]?\s+\w+\s+(по|про|о|об|насчёт)\s+\S+\s+(или|и|,)\s+\S+",
        r"не\s+нравил\w+\s+когда\s+\w+\s+(давал|просил|предлагал)\s+\w+\s+(по|про|о)\s+\S+\s+(или|и)\s+\S+",
        r"не\s+любил[аи]?,\s+когда\s+\w+\s+давали\s+советы\s+по\s+\S+\s+(или|и)\s+\S+",
    ]

    issues = []
    chapters = book.get("chapters", [])
    for chapter in chapters:
        ch_id = chapter.get("id") or ""
        texts = [chapter.get("content") or ""] + [p.get("text", "") for p in chapter.get("paragraphs", [])]
        for text in texts:
            for pat in patterns:
                for match in re.finditer(pat, text, re.IGNORECASE):
                    issues.append({
                        "type": "example_instead_of_generalization",
                        "chapter_id": ch_id,
                        "severity": "warning",
                        "matched_text": match.group(0),
                        "suggestion": "Обобщение первым, затем примеры: «не любил советов; например, по ...»",
                    })

    print(f"[AWKWARD-FORM] {len(issues)} паттернов «частный пример вместо обобщения».")
    return {"issues": issues, "issues_count": len(issues)}


_FEMALE_RELATIONS = frozenset({
    "мать", "мама", "мамочка",
    "дочь", "дочка",
    "жена", "супруга",
    "сестра",
    "бабушка", "бабуля", "баба",
    "внучка",
    "тётя",
    "племянница",
    "золовка",
    "свекровь",
    "тёща",
    "невестка",
})


def _is_female_relation(label: str) -> bool:
    label_lower = label.strip().lower()
    return any(rel in label_lower for rel in _FEMALE_RELATIONS)


def enforce_paspart_format(book: dict) -> tuple:
    """Task 043: заменить «р. YYYY» → «родился/родилась в YYYY году», «ум. YYYY» → «умер/умерла в YYYY году».

    Род определяется по label (relation). Применяется к bio_data.family и ch_01.content.
    Returns (patched_book, replacements_log).
    """
    import copy
    import re
    book = copy.deepcopy(book)
    log = []

    def _gender_birth(label: str) -> str:
        return "родилась" if _is_female_relation(label) else "родился"

    def _gender_death(label: str) -> str:
        return "умерла" if _is_female_relation(label) else "умер"

    def _replace_in_text(text: str, label: str) -> tuple:
        replacements = []

        def sub_born(m):
            year = m.group(1)
            r = f"{_gender_birth(label)} в {year} году"
            replacements.append({"old": m.group(0), "new": r, "label": label})
            return r

        def sub_died(m):
            year = m.group(1)
            r = f"{_gender_death(label)} в {year} году"
            replacements.append({"old": m.group(0), "new": r, "label": label})
            return r

        text = re.sub(r"\bр\.\s*(\d{4})\b", sub_born, text)
        text = re.sub(r"\bум\.\s*(\d{4})\b", sub_died, text)
        return text, replacements

    chapters = book.get("chapters", [])
    ch01 = next((ch for ch in chapters if ch.get("id") == "ch_01"), None)
    if ch01:
        bio_data = ch01.get("bio_data") or {}
        family = bio_data.get("family", [])
        for entry in family:
            label = entry.get("label") or entry.get("relation") or ""
            for field in ("value", "note"):
                val = entry.get(field)
                if val and isinstance(val, str):
                    new_val, reps = _replace_in_text(val, label)
                    if reps:
                        entry[field] = new_val
                        log.extend(reps)

        content = ch01.get("content") or ""
        new_content, reps = _replace_in_text(content, "")
        if reps:
            ch01["content"] = new_content
            log.extend(reps)

        ch01["bio_data"] = bio_data

    print(f"[PASPART-FORMAT] Заменено {len(log)} вхождений «р./ум.» → полная форма.")
    return book, log


# ─── Task 038: CA confabulation guards ────────────────────────────────────

def validate_description_drift(audit_data: dict) -> dict:
    """Task 038: проверить CA event descriptions на causal/date/motivation confabulation.

    audit_data — fact_map (с .timeline) или список events.
    Returns {issues: [...], events_checked, events_flagged}.
    """
    import re

    CAUSAL_RE = re.compile(
        r"\b(потому что|поскольку|так как|из-за этого|это произошло|вследствие)\b",
        re.IGNORECASE,
    )
    YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")
    MOTIVATION_RE = re.compile(
        r"\b(хотел[аи]?\b|желал[аи]?\b|мечтал[аи]?\b|стремил\w*|верил[аи]? в|решил[аи]? что|думал[аи]? что)\b",
        re.IGNORECASE,
    )

    issues = []
    checked = 0

    events = []
    if isinstance(audit_data, dict):
        events = audit_data.get("timeline", audit_data.get("events", []))
    elif isinstance(audit_data, list):
        events = audit_data

    for event in events:
        # Task 038b: bypass strict drift check for pin-list events
        if event.get("was_in_pin_list"):
            continue

        description = (event.get("description") or "").strip()
        source_quote = (event.get("source_quote") or event.get("transcript_quote") or "").strip()
        event_id = event.get("event_id") or event.get("id") or "?"

        if not description or not source_quote:
            continue
        checked += 1

        # 1. Causal drift
        if CAUSAL_RE.search(description) and not CAUSAL_RE.search(source_quote):
            issues.append({
                "event_id": event_id,
                "type": "causal_drift",
                "description_snippet": description[:120],
                "source_snippet": source_quote[:120],
            })

        # 2. Date drift
        desc_years = set(YEAR_RE.findall(description))
        src_years = set(YEAR_RE.findall(source_quote))
        extra_years = desc_years - src_years
        if extra_years:
            issues.append({
                "event_id": event_id,
                "type": "date_drift",
                "extra_years": sorted(extra_years),
                "description_snippet": description[:120],
                "source_snippet": source_quote[:120],
            })

        # 3. Motivation drift
        if MOTIVATION_RE.search(description) and not MOTIVATION_RE.search(source_quote):
            issues.append({
                "event_id": event_id,
                "type": "motivation_drift",
                "description_snippet": description[:120],
                "source_snippet": source_quote[:120],
            })

    flagged = len({i["event_id"] for i in issues})
    print(f"[CA-DRIFT] Проверено {checked} событий, flags: {len(issues)} в {flagged} событиях.")
    return {"issues": issues, "events_checked": checked, "events_flagged": flagged}


def validate_relation_consistency(fact_map: dict, transcript_text: str) -> dict:
    """Task 038: проверить relation_to_subject персон на подтверждение в транскрипте.

    Returns {issues: [...], persons_checked, unconfirmed_count}.
    """
    import re

    COMPLEX_RELATIONS = frozenset({
        "тётя", "дядя", "племянник", "племянница",
        "золовка", "свекровь", "тесть", "тёща",
        "кум", "кума", "свояк",
    })
    CONFIRMATION_RE = re.compile(
        r"(сестра|брат|мать|отец|мама|папа)\s+(моей|его|её|мужа|жены)"
        r"|сестра (мужа|жены|мамы|папы|отца|матери)"
        r"|брат (мужа|жены|мамы|папы|отца|матери)"
        r"|(тётя|дядя)\s+(со|из)\s+стороны",
        re.IGNORECASE,
    )

    issues = []
    persons = fact_map.get("persons", [])
    checked = 0

    for person in persons:
        name = (person.get("name") or "").strip()
        relation = (
            person.get("relation_to_subject") or person.get("relation") or ""
        ).strip().lower()

        if not name or not relation:
            continue
        if not any(rel in relation for rel in COMPLEX_RELATIONS):
            continue

        checked += 1
        name_lower = name.lower()
        sentences = [s.strip() for s in re.split(r"[.!?]", transcript_text) if name_lower in s.lower()]
        confirmed = any(CONFIRMATION_RE.search(s) for s in sentences)

        # Known confirmations from pin-list
        if "шура" in name_lower and any(r in relation for r in ("золовка", "сестра")):
            confirmed = True

        if not confirmed:
            issues.append({
                "person_name": name,
                "relation": relation,
                "type": "unconfirmed_relation",
                "sentences_checked": len(sentences),
                "suggested_action": f"Проверить: может быть «знакомый/соседка» вместо «{relation}»",
            })

    unconfirmed = len(issues)
    print(f"[RELATION-CONSISTENCY] Проверено {checked} персон, неподтверждённых: {unconfirmed}.")
    return {"issues": issues, "persons_checked": checked, "unconfirmed_count": unconfirmed}


def validate_historical_note_grounding(book: dict, fact_map: dict, transcripts: list) -> dict:
    """Task 038: проверить historical_notes на generalization без grounding (Класс 1c).

    Returns {issues: [...], notes_checked, errors_count, warnings_count}.
    """
    import re

    GENERALIZATION_RE = re.compile(
        r"\b(многие|обычно|в те годы|в то время|зачастую|нередко|как правило)\b"
        r"[^.]*\b(пожилые|люди|семьи|женщины|мужчины|все|часто)\b",
        re.IGNORECASE,
    )
    ANTITRIGGERS = [
        "в 1990-е многие пожилые",
        "многие пожилые люди оставались одни",
        "жизнь становилась всё дороже",
        "1990-е многие пожилые",
    ]

    issues = []
    checked = 0

    notes = book.get("historical_notes", [])
    for note in notes:
        note_id = note.get("id") or note.get("note_id") or "?"
        text = (note.get("text") or note.get("content") or "").strip()
        if not text:
            continue
        checked += 1
        text_lower = text.lower()
        for antitrigger in ANTITRIGGERS:
            if antitrigger.lower() in text_lower:
                issues.append({
                    "note_id": note_id, "type": "antitrigger_phrase",
                    "severity": "error", "matched_phrase": antitrigger, "snippet": text[:150],
                })
        if GENERALIZATION_RE.search(text):
            issues.append({
                "note_id": note_id, "type": "generalization_unverified",
                "severity": "warning", "snippet": text[:150],
            })

    chapters = book.get("chapters", [])
    for chapter in chapters:
        ch_id = chapter.get("id") or ""
        content = chapter.get("content") or ""
        inline_blocks = re.findall(r"\*\*\*(.+?)\*\*\*", content, re.DOTALL)
        for block in inline_blocks:
            checked += 1
            block_lower = block.lower()
            for antitrigger in ANTITRIGGERS:
                if antitrigger.lower() in block_lower:
                    issues.append({
                        "note_id": f"inline_{ch_id}", "type": "antitrigger_phrase",
                        "severity": "error", "chapter_id": ch_id,
                        "matched_phrase": antitrigger, "snippet": block[:150],
                    })
            if GENERALIZATION_RE.search(block):
                issues.append({
                    "note_id": f"inline_{ch_id}", "type": "generalization_unverified",
                    "severity": "warning", "chapter_id": ch_id, "snippet": block[:150],
                })

    errors = sum(1 for i in issues if i.get("severity") == "error")
    warnings = sum(1 for i in issues if i.get("severity") == "warning")
    print(f"[HN-GROUNDING] Проверено {checked} заметок, {errors} errors + {warnings} warnings.")
    return {"issues": issues, "notes_checked": checked, "errors_count": errors, "warnings_count": warnings}


def validate_motivation_attributions(book: dict, transcripts: list) -> dict:
    """Task 038: проверить атрибуции мотивации на подтверждение в транскрипте (Класс 1d).

    Returns {issues: [...], attributions_found, errors_count, warnings_count}.
    """
    import re

    MOTIVATION_RE = re.compile(
        r"\b(верила?\s+в\b|воевала?\s+за\b|хотела?\s+\S+|жила?\s+ради\b|посвятила?\s+себя\b|стремилась?\s+\S+)",
        re.IGNORECASE,
    )
    BAD_ATTRIBUTIONS = [
        "воевала за идеалы",
        "верила в идеалы",
        "идеалы за которые воевала",
        "идеалы, за которые воевала",
        "жизнь была наполнена служением",
    ]

    transcript_combined = " ".join(
        t.get("text", "") if isinstance(t, dict) else str(t)
        for t in transcripts
    ).lower()

    issues = []
    attributions_found = 0

    chapters = book.get("chapters", [])
    for chapter in chapters:
        ch_id = chapter.get("id") or ""
        texts = [chapter.get("content") or ""] + [p.get("text", "") for p in chapter.get("paragraphs", [])]
        for text in texts:
            text_lower = text.lower()
            for bad in BAD_ATTRIBUTIONS:
                if bad.lower() in text_lower:
                    attributions_found += 1
                    idx = text_lower.find(bad.lower())
                    issues.append({
                        "chapter_id": ch_id, "type": "motivation_antitrigger",
                        "severity": "error", "matched_phrase": bad,
                        "snippet": text[max(0, idx - 20): idx + len(bad) + 40],
                    })

            for match in MOTIVATION_RE.finditer(text):
                phrase = match.group(0)
                phrase_words = phrase.lower().split()[:2]
                found_in_tr = all(w in transcript_combined for w in phrase_words if len(w) > 3)
                if not found_in_tr:
                    attributions_found += 1
                    issues.append({
                        "chapter_id": ch_id, "type": "motivation_unverified",
                        "severity": "warning", "matched_phrase": phrase,
                        "context": text[max(0, match.start() - 30): match.end() + 30],
                    })

    errors = sum(1 for i in issues if i.get("severity") == "error")
    warnings = sum(1 for i in issues if i.get("severity") == "warning")
    print(f"[MOTIVATION] {attributions_found} атрибуций, {errors} errors + {warnings} warnings.")
    return {"issues": issues, "attributions_found": attributions_found, "errors_count": errors, "warnings_count": warnings}


# ─── Task 041: Pin-list coverage + episode diff ───────────────────────────

def parse_pin_list_from_markdown(md_path: str) -> dict:
    """Task 041/044b/050: парсить known_episodes_*.md → структурированный pin-list.

    Returns:
        {
          episodes: [...],          # хронологические эпизоды с min_sentences
          bytovye: [...],           # бытовые эпизоды с min_sentences
          traits: [...],
          characteristic_words: [],
          required_persons: [...],  # task 044b: обязательные персоны из раздела «Прямые родственники»
        }
    """
    import re
    from pathlib import Path

    path = Path(md_path)
    if not path.exists():
        print(f"[PIN-LIST-PARSER] Файл не найден: {md_path}")
        return {"episodes": [], "bytovye": [], "traits": [], "characteristic_words": [], "required_persons": []}

    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()

    episodes = []
    bytovye = []
    traits = []
    char_words = []
    required_persons = []
    required_episode_ids: list = []   # task 044i v7: required_in_narrative list
    descendants_info: list = []       # task 048f v7: for Class 12 extend
    characteristic_words_dicts: list = []  # task 049h v7: word + context + source

    current_table_type = None
    header_seen = False
    # Track column index for min_sentences in the current table header
    min_sentences_col_idx: dict = {}  # table_type -> col index
    in_required_list = False  # for bullet-list parsing of required episodes

    for line in lines:
        line_stripped = line.strip()

        if "## Хронологические эпизоды" in line_stripped:
            current_table_type = "episodes"; header_seen = False; min_sentences_col_idx = {}; in_required_list = False; continue
        elif "## Бытовые эпизоды" in line_stripped:
            current_table_type = "bytovye"; header_seen = False; min_sentences_col_idx = {}; in_required_list = False; continue
        elif "## Характеристики" in line_stripped:
            current_table_type = "traits"; header_seen = False; min_sentences_col_idx = {}; in_required_list = False; continue
        elif "## Голос рассказчика" in line_stripped:
            current_table_type = "char_words"; header_seen = False; min_sentences_col_idx = {}; in_required_list = False; continue
        elif ("## Прямые родственники" in line_stripped or "## Обязательные персоны" in line_stripped):
            current_table_type = "required_persons"; header_seen = False; min_sentences_col_idx = {}; in_required_list = False; continue
        elif "## Обязательные эпизоды" in line_stripped:
            current_table_type = "required_episodes"; header_seen = False; min_sentences_col_idx = {}; in_required_list = True; continue
        elif "## Племянники и племянницы" in line_stripped:
            current_table_type = "descendants"; header_seen = False; min_sentences_col_idx = {}; in_required_list = False; continue
        elif "## Characteristic words" in line_stripped:
            current_table_type = "char_words_v7"; header_seen = False; min_sentences_col_idx = {}; in_required_list = False; continue
        elif line_stripped.startswith("## "):
            current_table_type = None; header_seen = False; min_sentences_col_idx = {}; in_required_list = False; continue

        if current_table_type is None:
            continue

        # Required episodes — bullet list (task 044i)
        if current_table_type == "required_episodes":
            m = re.match(r'^[-*]\s+(ep_\w+|byt_\w+)', line_stripped)
            if m:
                required_episode_ids.append(m.group(1).strip())
            continue

        if re.match(r"^\|[-|\s]+\|$", line_stripped):
            header_seen = True
            continue

        # Parse header row to detect min_sentences column position
        if not header_seen and line_stripped.startswith("|") and current_table_type in ("episodes", "bytovye", "traits"):
            cells_h = [c.strip().lower() for c in line_stripped.split("|")[1:-1]]
            for ci, ch in enumerate(cells_h):
                if "min_sentences" in ch or "min_sent" in ch:
                    min_sentences_col_idx[current_table_type] = ci
            continue

        if not (line_stripped.startswith("|") and header_seen):
            continue

        cells = [c.strip() for c in line_stripped.split("|")[1:-1]]
        if len(cells) < 2:
            continue

        def _clean(s):
            return re.sub(r"\*+", "", s).strip()

        def _min_sent(cells_list, table_type, default):
            idx = min_sentences_col_idx.get(table_type)
            if idx is not None and idx < len(cells_list):
                val = cells_list[idx].strip()
                if val.isdigit():
                    return int(val)
            return default

        if current_table_type == "episodes":
            if len(cells) < 4:
                continue
            ep_id = cells[1]
            title = _clean(cells[2])
            markers_raw = cells[5] if len(cells) > 5 else ""
            markers = [m.strip() for m in re.split(r"[,;`]", re.sub(r"`", "", markers_raw)) if m.strip()]
            min_sent = _min_sent(cells, "episodes", 3)
            if ep_id and title and ep_id not in ("#", "episode_id", "ep_id"):
                episodes.append({
                    "episode_id": ep_id, "title": title,
                    "markers": markers, "min_sentences": min_sent,
                })

        elif current_table_type == "bytovye":
            byt_id = cells[1]
            title = _clean(cells[2]) if len(cells) > 2 else _clean(cells[1])
            markers_raw = cells[3] if len(cells) > 3 else ""
            markers = [m.strip() for m in re.split(r"[,;`]", re.sub(r"`", "", markers_raw)) if m.strip()]
            min_sent = _min_sent(cells, "bytovye", 2)
            if byt_id and title and byt_id not in ("#", "byt_id"):
                bytovye.append({
                    "byt_id": byt_id, "title": title,
                    "markers": markers, "min_sentences": min_sent,
                })

        elif current_table_type == "traits":
            trait_id = cells[1]
            title = _clean(cells[2]) if len(cells) > 2 else _clean(cells[1])
            markers_raw = cells[3] if len(cells) > 3 else ""
            markers = [m.strip() for m in re.split(r"[,;`]", re.sub(r"`", "", markers_raw)) if m.strip()]
            min_sent = _min_sent(cells, "traits", 1)
            if trait_id and title and trait_id not in ("#", "trait_id"):
                traits.append({
                    "trait_id": trait_id, "title": title,
                    "markers": markers, "min_sentences": min_sent,
                })

        elif current_table_type == "char_words":
            word = _clean(cells[0])
            if word and word not in ("#", "Слово", "слово"):
                char_words.append(word)

        elif current_table_type == "char_words_v7":
            # task 049h v7: word + context + source_quote table
            word = _clean(cells[0])
            context = _clean(cells[1]) if len(cells) > 1 else ""
            source_quote = _clean(cells[2]) if len(cells) > 2 else ""
            if word and word not in ("#", "word", "слово"):
                char_words.append(word)
                characteristic_words_dicts.append({
                    "word": word, "context": context, "source_quote": source_quote
                })

        elif current_table_type == "descendants":
            # task 048f v7: name + relation + parent + profession + notes
            name = _clean(cells[0])
            relation = _clean(cells[1]) if len(cells) > 1 else ""
            parent = _clean(cells[2]) if len(cells) > 2 else ""
            profession = _clean(cells[3]) if len(cells) > 3 else ""
            notes = _clean(cells[4]) if len(cells) > 4 else ""
            if name and name not in ("#", "name"):
                descendants_info.append({
                    "name": name, "relation_to_subject": relation,
                    "parent": parent, "profession": profession, "notes": notes,
                })

        elif current_table_type == "required_persons":
            # task 044b: раздел «Прямые родственники»
            # Ожидается: | # | name | relation | note/aliases |
            if len(cells) < 2:
                continue
            name = _clean(cells[1]) if len(cells) > 1 else _clean(cells[0])
            relation = _clean(cells[2]) if len(cells) > 2 else ""
            note = _clean(cells[3]) if len(cells) > 3 else ""
            if name and name not in ("#", "Имя", "name", "имя"):
                entry = {"name": name, "relation": relation, "is_pin_list_required": True}
                if note:
                    entry["note"] = note
                # Parse aliases from note (e.g. "тётя Маня")
                aliases = [a.strip() for a in re.split(r"[,;/]", note) if a.strip() and a.strip() != name]
                if aliases:
                    entry["aliases"] = aliases
                required_persons.append(entry)

    # task 044i v7: mark required_in_narrative for matched episodes
    if required_episode_ids:
        req_set = set(required_episode_ids)
        for ep in episodes:
            if ep.get("episode_id") in req_set:
                ep["required_in_narrative"] = True
        for byt in bytovye:
            if byt.get("byt_id") in req_set:
                byt["required_in_narrative"] = True

    print(
        f"[PIN-LIST-PARSER] Загружено: {len(episodes)} эпизодов ({sum(1 for e in episodes if e.get('required_in_narrative'))} required), "
        f"{len(bytovye)} бытовых ({sum(1 for b in bytovye if b.get('required_in_narrative'))} required), "
        f"{len(traits)} характеристик, {len(char_words)} слов, "
        f"{len(required_persons)} required_persons, {len(descendants_info)} descendants."
    )
    return {
        "episodes": episodes, "bytovye": bytovye,
        "traits": traits, "characteristic_words": char_words,
        "characteristic_words_detail": characteristic_words_dicts,
        "required_persons": required_persons,
        "descendants": descendants_info,
        "required_episode_ids": required_episode_ids,
    }


def validate_pin_list_coverage(book: dict, pin_list: dict) -> dict:
    """Task 041: проверить покрытие pin-list эпизодов в финальном тексте книги.

    coverage = "full" (≥60% markers), "partial" (≥1), "skipped" (0).
    Returns {episodes: [...], summary: {full, partial, skipped, total}}.
    """
    import re
    import math

    chapters = book.get("chapters", [])
    chapter_texts = {}
    all_text = ""
    for ch in chapters:
        ch_id = ch.get("id") or ""
        text = (ch.get("content") or "") + " ".join(p.get("text", "") for p in ch.get("paragraphs", []))
        chapter_texts[ch_id] = text.lower()
        all_text += text.lower() + " "

    results = []

    for category_key, id_field in [("episodes", "episode_id"), ("bytovye", "byt_id"), ("traits", "trait_id")]:
        for item in pin_list.get(category_key, []):
            item_id = item.get(id_field) or item.get("id") or "?"
            title = item.get("title", "")
            markers = item.get("markers", [])
            must_include = item.get("must_include", [])

            if not markers:
                continue

            found_markers = []
            found_chapter = None
            for marker in markers:
                try:
                    found = bool(re.search(marker, all_text, re.IGNORECASE))
                except re.error:
                    found = marker.lower() in all_text

                if found:
                    found_markers.append(marker)
                    if found_chapter is None:
                        for ch_id, ch_text in chapter_texts.items():
                            try:
                                if re.search(marker, ch_text, re.IGNORECASE):
                                    found_chapter = ch_id
                                    break
                            except re.error:
                                if marker.lower() in ch_text:
                                    found_chapter = ch_id
                                    break

            threshold_full = math.ceil(len(markers) * 0.6)
            count_found = len(found_markers)
            if count_found >= threshold_full:
                coverage = "full"
            elif count_found >= 1:
                coverage = "partial"
            else:
                coverage = "skipped"

            must_include_failed = [
                req for req in must_include
                if not any(w in all_text for w in req.lower().split()[:3] if len(w) > 3)
            ]

            results.append({
                "episode_id": item_id,
                "category": category_key,
                "title": title,
                "coverage": coverage,
                "markers_found": count_found,
                "markers_total": len(markers),
                "chapter_id": found_chapter,
                "must_include_failed": must_include_failed,
            })

    char_words = pin_list.get("characteristic_words", [])
    char_found = [w for w in char_words if w.lower().split()[0] in all_text]

    full_count = sum(1 for r in results if r["coverage"] == "full")
    partial_count = sum(1 for r in results if r["coverage"] == "partial")
    skipped_count = sum(1 for r in results if r["coverage"] == "skipped")

    summary = {
        "full": full_count,
        "partial": partial_count,
        "skipped": skipped_count,
        "total": len(results),
        "characteristic_words_found": len(char_found),
        "characteristic_words_total": len(char_words),
        "must_include_issues": sum(1 for r in results if r["must_include_failed"]),
    }

    print(
        f"[PIN-COVERAGE] Full={full_count}, Partial={partial_count}, Skipped={skipped_count} "
        f"из {len(results)} | char_words={len(char_found)}/{len(char_words)}"
    )
    return {"episodes": results, "summary": summary}


def diff_episodes_between_versions(
    book_new: dict,
    book_old: dict,
    pin_list: dict,
    regression_threshold: int = 3,
) -> dict:
    """Task 041: сравнить покрытие эпизодов между двумя версиями книги.

    Returns {regressions: [...], improvements: [...], regression_count, improvement_count, verdict}.
    """
    coverage_new = validate_pin_list_coverage(book_new, pin_list)
    coverage_old = validate_pin_list_coverage(book_old, pin_list)

    new_by_id = {r["episode_id"]: r for r in coverage_new["episodes"]}
    old_by_id = {r["episode_id"]: r for r in coverage_old["episodes"]}

    coverage_rank = {"full": 2, "partial": 1, "skipped": 0}
    regressions = []
    improvements = []

    for ep_id, new_r in new_by_id.items():
        old_r = old_by_id.get(ep_id)
        if old_r is None:
            continue
        new_rank = coverage_rank.get(new_r["coverage"], 0)
        old_rank = coverage_rank.get(old_r["coverage"], 0)
        if new_rank < old_rank:
            regressions.append({
                "episode_id": ep_id,
                "title": new_r.get("title", ""),
                "old_coverage": old_r["coverage"],
                "new_coverage": new_r["coverage"],
            })
        elif new_rank > old_rank:
            improvements.append({
                "episode_id": ep_id,
                "title": new_r.get("title", ""),
                "old_coverage": old_r["coverage"],
                "new_coverage": new_r["coverage"],
            })

    verdict = "regression_detected" if len(regressions) >= regression_threshold else "ok"
    print(
        f"[EPISODE-DIFF] Regressions={len(regressions)}, Improvements={len(improvements)}, "
        f"Verdict={verdict}"
    )
    return {
        "regressions": regressions,
        "improvements": improvements,
        "regression_count": len(regressions),
        "improvement_count": len(improvements),
        "verdict": verdict,
        "regression_threshold": regression_threshold,
        "summary_new": coverage_new["summary"],
        "summary_old": coverage_old["summary"],
    }
def run_proofreader_per_chapter(client, book_draft: dict, project_id: str,
                                cfg: dict | None = None) -> dict:
    """
    Запускает Корректора отдельно для каждой главы.

    Алгоритм:
    1. Первая глава → получаем паспорт стиля (style_passport)
    2. Последующие главы → передаём паспорт стиля для единообразия
    3. Каждый вызов получает контекст стыков (последний абзац пред. / первый след. главы)
    4. При падении одной главы — fallback только для неё, остальные вычитаны

    Возвращает dict с chapters (вычитанные) и style_passport (из первой главы).
    """
    if cfg is None:
        cfg = load_config()

    chapters = book_draft.get("chapters", [])
    if not chapters:
        return book_draft

    # Обогащённые главы для контекста стыков
    def _get_boundary(ch: dict, side: str) -> str:
        content = ch.get("content") or ""
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        if not paragraphs:
            return ""
        return paragraphs[-1] if side == "last" else paragraphs[0]

    style_passport: dict = {}
    corrected_chapters: list[dict] = []
    total_corrections = 0

    for idx, chapter in enumerate(chapters):
        ch_id = chapter.get("id", f"ch_{idx+1:02d}")
        ch_text = chapter.get("content") or ""

        # Пропускаем главы без текстового контента (bio_data, пустые)
        if not ch_text.strip() and not chapter.get("bio_data"):
            corrected_chapters.append(chapter)
            print(f"[PROOFREADER] {ch_id}: нет текста — пропускаем")
            continue

        prev_last = _get_boundary(chapters[idx - 1], "last") if idx > 0 else ""
        next_first = _get_boundary(chapters[idx + 1], "first") if idx < len(chapters) - 1 else ""

        single_book = {
            "chapters": [chapter],
            "callouts": book_draft.get("callouts", []),
            "historical_notes": book_draft.get("historical_notes", []),
        }

        # Первая глава с текстом — генерирует паспорт стиля
        is_first = (idx == 0 or not style_passport)

        user_message = {
            "project_id": project_id,
            "book_draft": single_book,
            "mode": "single_chapter",
            "chapter_context": {
                "is_first_chapter": is_first,
                "prev_chapter_last_paragraph": prev_last,
                "next_chapter_first_paragraph": next_first,
            },
        }
        if style_passport:
            user_message["style_passport"] = style_passport

        pr_cfg = cfg["proofreader"]
        model = pr_cfg["model"]
        max_tokens = pr_cfg["max_tokens"]
        temperature = pr_cfg.get("temperature", 0.0)
        system_prompt = load_prompt(pr_cfg["prompt_file"])

        print(f"[PROOFREADER] {ch_id}: вычитываю ({len(ch_text)} симв.)...")
        start = datetime.now()
        try:
            raw_parts = []
            input_tokens = output_tokens = 0
            with client.messages.stream(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": json.dumps(user_message, ensure_ascii=False)}]
            ) as stream:
                for text in stream.text_stream:
                    raw_parts.append(text)
                final_msg = stream.get_final_message()
                input_tokens = final_msg.usage.input_tokens
                output_tokens = final_msg.usage.output_tokens

            elapsed = (datetime.now() - start).total_seconds()
            raw = "".join(raw_parts).strip()
            print(f"[PROOFREADER] {ch_id}: {elapsed:.1f}с | in={input_tokens}, out={output_tokens}")

            if output_tokens >= max_tokens - 10:
                print(f"[PROOFREADER] {ch_id}: WARNING output_tokens близко к max_tokens")

            if raw.startswith("```"):
                lines = raw.split("\n")
                raw = "\n".join(lines[1:])
                if raw.endswith("```"):
                    raw = raw[:-3].strip()
            s = raw.find("{")
            e_idx = raw.rfind("}")
            if s != -1 and e_idx > s:
                try:
                    ch_result = json.loads(raw[s:e_idx + 1])
                except Exception:
                    ch_result = json.loads(raw)
            else:
                ch_result = json.loads(raw)

            # Извлекаем паспорт стиля из первого успешного вызова
            if is_first and ch_result.get("style_passport"):
                style_passport = ch_result["style_passport"]
                print(f"[PROOFREADER] {ch_id}: паспорт стиля получен")

            # Берём исправленную главу из ответа
            result_chapters = ch_result.get("chapters", [])
            if result_chapters:
                corrected_chapters.append(result_chapters[0])
                n_corrections = ch_result.get("summary", {}).get("total_corrections", 0)
                total_corrections += n_corrections or 0
                print(f"[PROOFREADER] {ch_id}: ✅ {n_corrections} правок")
            else:
                print(f"[PROOFREADER] {ch_id}: ⚠️ нет chapters в ответе — fallback")
                corrected_chapters.append(chapter)

        except Exception as exc:
            elapsed = (datetime.now() - start).total_seconds()
            print(f"[PROOFREADER] {ch_id}: ❌ ошибка за {elapsed:.1f}с: {exc} — fallback")
            corrected_chapters.append(chapter)

    result = dict(book_draft)
    result["chapters"] = corrected_chapters
    result["style_passport"] = style_passport
    summary = {
        "mode": "per_chapter",
        "chapters_processed": len(chapters),
        "total_corrections": total_corrections,
        "clean_text_ready": True,
    }
    result["summary"] = summary
    result["proofreader_summary"] = summary

    _auto_checkpoint(project_id, "proofreader", result)
    return result


# ═══════════════════════════════════════════════════════════════
# Batch 2-fix — новые функции (tasks 046, 043b, 038b, 049, 050, 048, 044b)
# ═══════════════════════════════════════════════════════════════


def enforce_epilogue_stop_phrases(book: dict, mapping: dict) -> tuple:
    """Task 046: auto-rewrite epilogue — удалить предложения с пластиковыми шаблонами.

    mapping — содержимое epilogue_rewrite_mapping.json (generic, universal).
    Returns (modified_book, rewrite_log).
    Idempotent.
    """
    import re
    import copy

    rules = mapping.get("rules", [])
    applies_to = set(mapping.get("applies_to_chapter_ids", ["epilogue"]))
    book_out = copy.deepcopy(book)
    rewrite_log = []

    def _split_sentences(text: str) -> list:
        parts = re.split(r'(?<=[.!?])\s+(?=[А-ЯA-Z«"])', text)
        return [p.strip() for p in parts if p.strip()]

    for chapter in book_out.get("chapters", []):
        ch_id = chapter.get("id") or ""
        if ch_id not in applies_to and "epilogue" not in ch_id.lower():
            continue
        content = chapter.get("content") or ""
        if not content:
            continue
        sentences = _split_sentences(content)
        kept = []
        for sent in sentences:
            deleted = False
            for rule in rules:
                pat = rule.get("pattern_regex")
                if not pat:
                    continue
                action = rule.get("action", "delete_sentence")
                try:
                    m = re.search(pat, sent, re.IGNORECASE)
                except re.error:
                    continue
                if not m:
                    continue
                if action == "delete_sentence":
                    rewrite_log.append({
                        "chapter_id": ch_id, "action": "deleted",
                        "category": rule.get("category", "?"),
                        "reason": rule.get("reason", ""),
                        "deleted_sentence": sent[:200],
                    })
                    deleted = True
                    break
                elif action == "delete_sentence_if_starts_with_match":
                    if m.start() < 30:
                        rewrite_log.append({
                            "chapter_id": ch_id, "action": "deleted",
                            "category": rule.get("category", "?"),
                            "reason": rule.get("reason", ""),
                            "deleted_sentence": sent[:200],
                        })
                        deleted = True
                        break
            if not deleted:
                kept.append(sent)
        chapter["content"] = " ".join(kept)
        deleted_count = len(sentences) - len(kept)
        if deleted_count:
            print(f"[EPILOGUE-REWRITE] {ch_id}: удалено {deleted_count} из {len(sentences)} предложений")
            if len(chapter["content"]) < 400:
                print("[EPILOGUE-REWRITE] ⚠️ epilogue < 400 chars после rewrite — human review")
                rewrite_log.append({"chapter_id": ch_id, "action": "warning",
                                    "reason": "epilogue < 400 chars after rewrite"})
    total_del = sum(1 for r in rewrite_log if r.get("action") == "deleted")
    print(f"[EPILOGUE-REWRITE] Итого удалено: {total_del} предложений")
    return book_out, rewrite_log


def validate_narrative_stop_phrases(book: dict, config: dict) -> dict:
    """Task 043b: проверить нарративные главы на Класс 6/11 украшения с pair-pattern support.

    Returns {issues: [...], errors_count, warnings_count}.
    Idempotent.
    """
    import re

    patterns = config.get("generic_categorical_patterns", [])
    scoped_epil_only = set(config.get("scoped_to_epilogue_only", []))
    scoped_narrative = set(config.get("scoped_to_narrative_and_epilogue", []))
    # v62a-043d: chapter-specific scope (optional, finer-grained than scoped_to_narrative_and_epilogue)
    scoped_to_chapters = config.get("scoped_to_chapters", {})
    issues = []

    for chapter in book.get("chapters", []):
        ch_id = chapter.get("id") or ""
        is_epilogue = "epilogue" in ch_id.lower()
        paras = chapter.get("paragraphs", [])
        texts = [p.get("text", "") for p in paras] if paras else [
            t.strip() for t in re.split(r"\n\n+", chapter.get("content") or "") if t.strip()
        ]
        for pat_entry in patterns:
            category = pat_entry.get("category", "?")
            if category in scoped_epil_only and not is_epilogue:
                continue
            if category not in scoped_epil_only and category not in scoped_narrative:
                continue
            # Chapter-specific scope check (overrides broader scope if defined)
            if category in scoped_to_chapters:
                allowed = scoped_to_chapters[category]
                if ch_id not in allowed:
                    continue
            pair = pat_entry.get("pattern_pair")
            if pair and len(pair) == 2:
                try:
                    re1 = re.compile(pair[0], re.IGNORECASE)
                    re2 = re.compile(pair[1], re.IGNORECASE)
                except re.error:
                    continue
                for para in texts:
                    if re1.search(para) and re2.search(para):
                        sev = "error" if is_epilogue else "warning"
                        issues.append({"chapter_id": ch_id, "category": category,
                                       "severity": sev, "match_type": "pair", "snippet": para[:150]})
                continue
            # pattern_options: any match in the list triggers a flag (043f-2)
            pattern_options = pat_entry.get("pattern_options")
            if pattern_options:
                compiled_options = []
                for p in pattern_options:
                    try:
                        compiled_options.append(re.compile(p, re.IGNORECASE))
                    except re.error:
                        pass
                sev_override = pat_entry.get("severity")
                for para in texts:
                    matched = any(rx.search(para) for rx in compiled_options)
                    if matched:
                        sev = sev_override or ("error" if is_epilogue else "warning")
                        issues.append({"chapter_id": ch_id, "category": category,
                                       "severity": sev, "match_type": "pattern_options", "snippet": para[:150]})
                continue
            pattern = pat_entry.get("pattern") or pat_entry.get("pattern_regex")
            if not pattern:
                continue
            try:
                pat_re = re.compile(pattern, re.IGNORECASE)
            except re.error:
                continue
            sev_override = pat_entry.get("severity")
            for para in texts:
                if pat_re.search(para):
                    sev = sev_override or ("error" if is_epilogue else "warning")
                    issues.append({"chapter_id": ch_id, "category": category,
                                   "severity": sev, "snippet": para[:150]})

    errors = sum(1 for i in issues if i["severity"] == "error")
    warnings = sum(1 for i in issues if i["severity"] == "warning")
    print(f"[NARRATIVE-STOP] {errors} errors + {warnings} warnings по {len(patterns)} категориям.")
    return {"issues": issues, "errors_count": errors, "warnings_count": warnings}


def validate_pin_list_in_auto_enrich(audit_data: dict, pin_list: dict) -> dict:
    """Task 038b: проверить что pin-list episodes/persons попали в CA auto_enrich.

    Returns {pin_list_event_missing, pin_list_person_missing, errors_count}.
    """
    auto_enrich = audit_data.get("auto_enrich", {})
    ae_event_texts = [
        ((ev.get("title") or "") + " " + (ev.get("description") or "") + " " + (ev.get("source_quote") or "")).lower()
        for ev in auto_enrich.get("timeline", [])
    ]
    ae_person_names = {(p.get("name") or "").lower() for p in auto_enrich.get("persons", [])}
    gap_event_ids = {g.get("id") or g.get("event_id")
                     for g in audit_data.get("log_only_gaps", {}).get("missing_events", [])}

    missing_events = []
    for ep in pin_list.get("episodes", []):
        markers = ep.get("markers", [])
        ep_id = ep.get("episode_id", "?")
        if not markers:
            continue
        found = any(any(m.lower() in ae_text for m in markers if m) for ae_text in ae_event_texts)
        if not found and ep_id not in gap_event_ids:
            missing_events.append({"episode_id": ep_id, "title": ep.get("title", ""), "severity": "error"})

    missing_persons = []
    for rp in pin_list.get("required_persons", []):
        name = (rp.get("name") or "").lower()
        aliases = [(a or "").lower() for a in rp.get("aliases", [])]
        if not any(n in ae_person_names for n in [name] + aliases if n):
            missing_persons.append({"name": rp.get("name"), "relation": rp.get("relation", ""), "severity": "error"})

    errors = len(missing_events) + len(missing_persons)
    print(f"[PIN-LIST-COMPLIANCE] missing_events={len(missing_events)}, missing_persons={len(missing_persons)}")
    return {"pin_list_event_missing": missing_events, "pin_list_person_missing": missing_persons, "errors_count": errors}


def validate_discourse_markers(book: dict, fact_map: dict, config: dict) -> dict:
    """Task 049/049c: Класс 13 — подсчёт discourse markers рассказчика в нарративе.

    config — discourse_markers_<subject>.json.
    v62a-049c: расширены generic patterns + aliases rapporteur'а включены в broad match
    (не требуется точное имя — «дочь», «она вспоминает» тоже считается).
    Returns {markers_found, thresholds, issues, errors_count, warnings_count}.
    Idempotent.
    """
    import re

    rapporteurs = config.get("rapporteurs", [])
    thresholds = config.get("thresholds", {"ch_02": 8, "ch_03": 5, "ch_04": 3})

    # Generic role-based patterns (not name-specific)
    all_patterns = [
        r"\bкак\s+вспоминает\s+(?:дочь|сын|внук\w*|племянник\w*|рассказчик\w*)\b",
        r"\bпо\s+словам\s+(?:дочери|сына|внука|внучки|племянника|племянницы|рассказчик\w*)\b",
        r"\bотмеча\w+\s+(?:дочь|сын|внук\w*)\b",
        r"\bговорит\s+(?:дочь|сын|внук\w*)\b",
        r"\bрассказывает\s+(?:дочь|сын|внук\w*)\b",
        # v62a-049c: broader alias patterns not requiring exact name
        r"\bона\s+вспомина\w+\b",
        r"\bпо\s+её\s+словам\b",
        r"\bпо\s+его\s+словам\b",
        r"\bкак\s+она\s+(?:говор\w+|вспомина\w+|рассказ\w+)\b",
        r"\bкак\s+он\s+(?:говор\w+|вспомина\w+|рассказ\w+)\b",
        r"\bпо\s+воспоминани\w+\s+(?:дочери|сына|внука|внучки)\b",
        r"\bсо\s+слов\s+(?:дочери|сына|внука|внучки|рассказчик\w*)\b",
    ]

    # Per-rapporteur patterns including their aliases
    for rap in rapporteurs:
        rap_names = [rap.get("name", "")] + rap.get("aliases", [])
        for n in rap_names:
            if not n:
                continue
            e = re.escape(n)
            all_patterns.extend([
                rf"\bкак\s+вспоминает\s+{e}\b",
                rf"\bпо\s+словам\s+{e}\b",
                rf"\b{e}\s+(?:отмеча\w+|вспомина\w+|говор\w+|рассказ\w+|пиш\w+|объясн\w+)\b",
                rf"\b{e}\s+подчёркива\w+\b",
                rf"\b{e}\s+уточня\w+\b",
            ])

    compiled = []
    for pat in all_patterns:
        try:
            compiled.append(re.compile(pat, re.IGNORECASE))
        except re.error:
            pass

    markers_found = {}
    for chapter in book.get("chapters", []):
        ch_id = chapter.get("id") or ""
        if "epilogue" in ch_id.lower():
            continue
        full_text = (chapter.get("content") or "") + " " + " ".join(
            p.get("text", "") for p in chapter.get("paragraphs", [])
        )
        markers_found[ch_id] = sum(len(p.findall(full_text)) for p in compiled)

    issues = []
    for ch_id, threshold in thresholds.items():
        found = markers_found.get(ch_id, 0)
        if found < threshold:
            issues.append({"chapter_id": ch_id, "type": "below_threshold",
                           "found": found, "expected": threshold, "severity": "warning"})

    errors = sum(1 for i in issues if i["severity"] == "error")
    warnings = sum(1 for i in issues if i["severity"] == "warning")
    print(f"[DISCOURSE-MARKERS] " + ", ".join(f"{k}={v}" for k, v in markers_found.items()))
    return {"markers_found": markers_found, "thresholds": thresholds,
            "issues": issues, "errors_count": errors, "warnings_count": warnings}


def remove_excluded_bio_data_family(book: dict, fact_map: dict) -> tuple:
    """Task 044c: удалить из bio_data.family персонажей, помеченных
    in_bio_data_family=false в fact_map.persons (после apply_relation_overrides).

    filter_bio_data_family_by_relation_whitelist не достаточен: override может явно
    исключить персону (flag в fact_map), но label родственника пройти через whitelist.

    Returns (patched_book, excluded_list).
    """
    import copy
    book = copy.deepcopy(book)
    excluded = []

    excluded_persons = [
        p for p in fact_map.get("persons", [])
        if p.get("in_bio_data_family") is False
    ]
    if not excluded_persons:
        return book, excluded

    chapters = book.get("chapters", [])
    ch01 = next((ch for ch in chapters if ch.get("id") == "ch_01"), None)
    if ch01 is None:
        return book, excluded

    bio_data = ch01.get("bio_data") or {}
    family = bio_data.get("family")
    if not family:
        return book, excluded

    def _name_matches(entry_text: str, person: dict) -> bool:
        name = (person.get("name") or "").lower().strip()
        aliases = [a.lower() for a in person.get("aliases", [])]
        text_lower = entry_text.lower()
        all_names = [name] + aliases
        return any(n and n in text_lower for n in all_names)

    kept = []
    for entry in family:
        entry_text = " ".join([
            entry.get("label") or "",
            entry.get("value") or "",
            entry.get("note") or "",
        ])
        match = next(
            (p for p in excluded_persons if _name_matches(entry_text, p)), None
        )
        if match:
            excluded.append({
                "label": entry.get("label", ""),
                "value": entry.get("value", ""),
                "matched_person": match.get("name", ""),
                "reason": "in_bio_data_family=false",
            })
            print(
                f"[v61-044c] Удалён из bio_data.family: «{entry.get('label', '')}» "
                f"({entry.get('value', '')}) — matched «{match.get('name', '')}»"
            )
        else:
            kept.append(entry)

    bio_data["family"] = kept
    ch01["bio_data"] = bio_data
    print(f"[v61-044c] bio_data.family: исключено {len(excluded)}, сохранено {len(kept)}.")
    return book, excluded


def validate_pin_list_depth(book: dict, pin_list: dict) -> dict:
    """Task 050: Класс 14 — минимальная глубина pin-list events в нарративе.

    Returns {depth_issues: [...], errors_count, warnings_count}.
    Idempotent.
    """
    import re

    SENT_RE = re.compile(r'(?<=[.!?])\s+(?=[А-ЯA-Z«"])')
    INITIAL_RE = re.compile(r'\b[А-ЯA-Z]\.')

    def _count_sentences(text: str) -> int:
        clean = INITIAL_RE.sub("X", text or "")
        return max(1, len([p for p in SENT_RE.split(clean) if p.strip()]))

    all_paragraphs = []
    for ch in book.get("chapters", []):
        ch_id = ch.get("id") or ""
        # v61-050b: только нарративные главы; ch_01 (paspart) исключён — пустые структурные
        # секции дают ложные depth errors; epilogue исключён — summary-style, не развёрнутый.
        NARRATIVE_CHAPTERS = {"ch_02", "ch_03", "ch_04"}
        if ch_id not in NARRATIVE_CHAPTERS:
            continue
        paras = ch.get("paragraphs", [])
        if paras:
            all_paragraphs.extend((p.get("text", ""), ch_id) for p in paras)
        else:
            for t in re.split(r"\n\n+", ch.get("content", "") or ""):
                if t.strip():
                    all_paragraphs.append((t.strip(), ch_id))

    depth_issues = []
    for ep in pin_list.get("episodes", []):
        ep_id = ep.get("episode_id", "?")
        markers = [m.lower() for m in ep.get("markers", []) if m]
        min_req = ep.get("min_sentences", 3)
        coverage = ep.get("coverage", "")
        if not markers or coverage == "skipped":
            continue
        best_para, best_hits, found_ch = None, 0, ""
        for para_text, ch_id in all_paragraphs:
            hits = sum(1 for m in markers if m in para_text.lower())
            if hits > best_hits:
                best_hits, best_para, found_ch = hits, para_text, ch_id
        if not best_para or best_hits == 0:
            continue
        actual = _count_sentences(best_para)
        if actual < min_req:
            sev = "error" if coverage == "full" else "warning"
            depth_issues.append({
                "episode_id": ep_id, "title": ep.get("title", ""),
                "min_required": min_req, "actual_sentences": actual,
                "chapter_id": found_ch, "paragraph_snippet": best_para[:150], "severity": sev,
            })

    errors = sum(1 for i in depth_issues if i["severity"] == "error")
    warnings = sum(1 for i in depth_issues if i["severity"] == "warning")
    print(f"[PIN-DEPTH] {errors} errors + {warnings} warnings.")
    return {"depth_issues": depth_issues, "errors_count": errors, "warnings_count": warnings}


def validate_chronological_consistency(book: dict, fact_map: dict, config: dict | None = None) -> dict:
    """Task 048 / 048e: Класс 12 — проверить хронологическую согласованность persons и событий.

    v65 (048e): ch_01 skipped (паспортичка = factual summary), epilogue child refs skipped,
    birth_declaration_self_skip — sentence declaring child's birth year not flagged.

    Returns {issues: [...], errors_count, warnings_count}.
    Idempotent.
    """
    import re

    cfg = config or {}
    SKIP_CHAPTERS = cfg.get("skip_chapters", ["ch_01"])
    EPILOGUE_SKIP_CHILD_REFS = cfg.get("epilogue_skip_child_refs", True)
    BIRTH_DECLARATION_SKIP = cfg.get("sentence_birth_self_declaration_skip", True)

    person_years = {}
    for p in fact_map.get("persons", []):
        name = (p.get("name") or "").strip().lower()
        aliases = [(a or "").strip().lower() for a in (p.get("aliases") or [])]
        birth = p.get("birth_year") or p.get("born")
        death = p.get("death_year") or p.get("died")
        for n in [name] + aliases:
            if n:
                person_years[n] = (int(birth) if birth else None, int(death) if death else None)

    def _min_birth_rel(rel_kw):
        years = [int(p["birth_year"]) for p in fact_map.get("persons", [])
                 if p.get("birth_year") and rel_kw in (p.get("relation_to_subject") or "").lower()]
        return min(years) if years else None

    collective_births = {
        "дет": min(filter(None, [_min_birth_rel("сын"), _min_birth_rel("дочь")]), default=None),
        "сын": _min_birth_rel("сын"),
        "доч": _min_birth_rel("дочь"),
        "внук": _min_birth_rel("внук"),
    }

    YEAR_RE = re.compile(r'\b((?:19|20)\d{2})\b')
    COLLECTIVE_RE = re.compile(r'\b(дет\w{0,4}|сын\w{0,2}|доч\w{0,4}|внук\w{0,4})\b', re.IGNORECASE)
    GENERIC_FAMILY_RE = re.compile(
        r'\b(семь\w{0,4}|создал\w*\s+семь\w*|семейн\w+|родственник\w*)\b', re.IGNORECASE
    )

    def _birth_declaration_sentence(sentence: str, birth_year: int) -> bool:
        """True if sentence explicitly declares birth_year — skip FP check."""
        if not BIRTH_DECLARATION_SKIP:
            return False
        years_in_sentence = [int(m) for m in YEAR_RE.findall(sentence)]
        return birth_year in years_in_sentence

    issues = []
    for chapter in book.get("chapters", []):
        ch_id = chapter.get("id") or ""
        if ch_id in SKIP_CHAPTERS:
            continue  # паспортичка содержит legitimate factual summaries
        is_epilogue = ch_id == "epilogue"
        paras = chapter.get("paragraphs", [])
        para_texts = [p.get("text", "") for p in paras] if paras else re.split(
            r"\n\n+", chapter.get("content", "") or ""
        )
        for para in para_texts:
            if not para.strip():
                continue
            para_years = [int(m) for m in YEAR_RE.findall(para)]
            if not para_years:
                continue
            min_year = min(para_years)
            para_lower = para.lower()

            for col_m in COLLECTIVE_RE.finditer(para):
                stem = col_m.group(0)[:4].lower()
                birth = collective_births.get(stem)
                if birth and min_year < birth:
                    # 048e: skip epilogue generic family refs
                    if is_epilogue and EPILOGUE_SKIP_CHILD_REFS:
                        continue
                    issues.append({
                        "chapter_id": ch_id, "type": "person_mentioned_before_birth",
                        "person_name": stem + "...", "person_birth_year_min": birth,
                        "event_year_range": str(min_year), "snippet": para[:200], "severity": "error",
                    })

            for name, (birth, death) in person_years.items():
                if len(name) < 4 or name not in para_lower:
                    continue
                if birth and min_year < birth:
                    # 048e: skip if sentence itself declares birth (factual summary)
                    if _birth_declaration_sentence(para, birth):
                        continue
                    # 048e: skip epilogue generic family refs (not named children)
                    if is_epilogue and EPILOGUE_SKIP_CHILD_REFS and GENERIC_FAMILY_RE.search(para):
                        continue
                    issues.append({
                        "chapter_id": ch_id, "type": "person_mentioned_before_birth",
                        "person_name": name, "person_birth_year_min": birth,
                        "event_year_range": str(min_year), "snippet": para[:200], "severity": "error",
                    })
                if death and min_year > death + 5:
                    issues.append({
                        "chapter_id": ch_id, "type": "person_mentioned_after_death",
                        "person_name": name, "person_death_year": death,
                        "event_year_range": str(min_year), "snippet": para[:200], "severity": "warning",
                    })

    # v62a-048c: grandchild check — inferred min birth = max(parent.marriage_year+1, parent.birth_year+16)
    grandchild_persons = [
        p for p in fact_map.get("persons", [])
        if "внук" in (p.get("relation_to_subject") or "").lower()
        and not (p.get("birth_year") or p.get("born"))
    ]
    if grandchild_persons:
        parent_persons = [
            p for p in fact_map.get("persons", [])
            if any(kw in (p.get("relation_to_subject") or "").lower() for kw in ("сын", "дочь"))
        ]
        parent_births = [int(p["birth_year"]) for p in parent_persons if p.get("birth_year")]
        parent_marriages = [int(p["marriage_year"]) for p in parent_persons
                            if p.get("marriage_year")]
        min_gc_birth = None
        if parent_births:
            min_parent_birth = min(parent_births)
            by_birth = min_parent_birth + 16
            by_marriage = min(parent_marriages) + 1 if parent_marriages else by_birth
            min_gc_birth = max(by_birth, by_marriage)

        GRANDCHILD_ACTIVITY_RE = re.compile(
            r'\b(встреча\w*|воспит\w*|играл\w*|видел\w*|школ\w*|из\s+школ\w*|сад\w*)\b',
            re.IGNORECASE,
        )
        GRANDCHILD_WORD_RE = re.compile(r'\b(внук\w*|внучк\w*)\b', re.IGNORECASE)

        for gc in grandchild_persons:
            gc_name = (gc.get("name") or "").lower().strip()
            gc_aliases = [(a or "").lower().strip() for a in gc.get("aliases", [])]
            gc_names = [gc_name] + gc_aliases
            for chapter in book.get("chapters", []):
                ch_id = chapter.get("id") or ""
                if ch_id in SKIP_CHAPTERS:
                    continue
                paras = chapter.get("paragraphs", [])
                para_texts = [p.get("text", "") for p in paras] if paras else re.split(
                    r"\n\n+", chapter.get("content", "") or ""
                )
                for para in para_texts:
                    if not para.strip():
                        continue
                    para_lower = para.lower()
                    name_in_para = any(n and n in para_lower for n in gc_names if len(n) >= 4)
                    gc_word_in_para = bool(GRANDCHILD_WORD_RE.search(para))
                    if not (name_in_para or gc_word_in_para):
                        continue
                    para_years = [int(m) for m in YEAR_RE.findall(para)]
                    if not para_years or min_gc_birth is None:
                        continue
                    activity_match = bool(GRANDCHILD_ACTIVITY_RE.search(para))
                    if min(para_years) < min_gc_birth and (name_in_para or activity_match):
                        issues.append({
                            "chapter_id": ch_id,
                            "type": "grandchild_before_inferred_birth",
                            "person_name": gc.get("name", gc_name),
                            "inferred_min_birth": min_gc_birth,
                            "parent_birth_used": min(parent_births) if parent_births else None,
                            "parent_marriage_used": min(parent_marriages) if parent_marriages else None,
                            "event_year_range": str(min(para_years)),
                            "snippet": para[:200],
                            "severity": "error",
                        })

    seen, deduped = set(), []
    for iss in issues:
        key = (iss.get("chapter_id"), iss.get("person_name"), iss.get("snippet", "")[:60])
        if key not in seen:
            seen.add(key)
            deduped.append(iss)

    errors = sum(1 for i in deduped if i["severity"] == "error")
    warnings = sum(1 for i in deduped if i["severity"] == "warning")
    print(f"[CHRONOLOGY] {errors} errors + {warnings} warnings.")
    return {"issues": deduped, "errors_count": errors, "warnings_count": warnings}


def enforce_bio_data_required_persons(book_final: dict, required_persons: list) -> dict:
    """Task 044b/044e: добавить required_persons в bio_data.family если отсутствуют.

    v62a-044e: исправлен поиск по existing entries — проверяет и name, и value поля
    (enforce_bio_data_completeness использует label/value; этот модуль раньше проверял только name).
    Добавляет entries в формате label/value (единый формат с enforce_bio_data_completeness).
    Идемпотентно. Returns modified book_final.
    """
    import copy
    book_out = copy.deepcopy(book_final)
    added = []
    for chapter in book_out.get("chapters", []):
        bio_data = chapter.get("bio_data")
        if bio_data is None:
            continue
        family = bio_data.get("family", [])
        # v62a-044e: check both name and value keys for existing entries
        existing_names: set[str] = set()
        for m in family:
            for k in ("name", "value"):
                v = (m.get(k) or "").strip().lower()
                if v and len(v) >= 3:
                    existing_names.add(v)
        for rp in required_persons:
            name = rp.get("name", "")
            if not name:
                continue
            name_lower = name.strip().lower()
            aliases = [(a or "").strip().lower() for a in rp.get("aliases", [])]
            all_names = [name_lower] + aliases
            if any(n and any(n in en or en in n for en in existing_names) for n in all_names if n):
                continue
            relation = rp.get("relation", "")
            label = relation if relation else "родственник"
            # v62a-044e: use label/value format (consistent with enforce_bio_data_completeness)
            entry = {
                "label": label,
                "value": name,
                "note": (rp.get("note", "") + " [from pin-list required_persons]").strip(),
                "confidence": "low",
                "needs_verification": True,
                "was_in_pin_list": True,
            }
            family.append(entry)
            existing_names.add(name_lower)
            added.append(name)
            print(f"[REQUIRED-PERSONS] Добавлен: {name} ({label}) — confidence bypass (pin-list)")
        bio_data["family"] = family
    print(f"[REQUIRED-PERSONS] Добавлено {len(added)} required_persons.")
    return book_out


# ─────────────────────────────────────────────────────────────────
# Task 051c: paspart-only temporal naming (v62a)
# ─────────────────────────────────────────────────────────────────


def apply_temporal_naming_to_paspart_only(book: dict, gazeteer: dict) -> dict:
    """Task 051c: применить исторические переименования топонимов ТОЛЬКО к paspart секциям.

    Области применения:
    - bio_data.family[].value / bio_data.family[].note
    - bio_data.timeline[].title / bio_data.timeline[].text
    НЕ применяется к narrative chapters (ch_02..ch_04, epilogue) — риск разрушения текста.

    gazeteer — gazeteer_<subject>.json с полем temporal_place_names[]:
        modern_name, historical_name, historical_from_year, historical_to_year

    Логика: если в строке упоминается год Y и Y попадает в [from_year, to_year] исторического
    периода, заменяем modern_name на historical_name (на всех склонениях через suffix matching).
    Idempotent: если уже historical_name — не трогаем.
    Returns modified book (deep copy).
    """
    import copy
    import re as _re

    book = copy.deepcopy(book)
    temporal_renames = gazeteer.get("temporal_place_names", [])
    if not temporal_renames:
        return book

    YEAR_RE = _re.compile(r'\b((?:18|19|20)\d{2})\b')

    def _extract_years_from_text(text: str):
        return [int(m) for m in YEAR_RE.findall(text)]

    def _apply_temporal_rename(text: str, entry_context_years: list[int]) -> str:
        """Replace modern_name with historical_name if context years fall in historical period."""
        if not text:
            return text
        inline_years = _extract_years_from_text(text)
        all_years = inline_years + entry_context_years
        for rename in temporal_renames:
            modern = rename.get("modern_name", "")
            historical = rename.get("historical_name", "")
            from_yr = rename.get("historical_from_year")
            to_yr = rename.get("historical_to_year")
            if not (modern and historical and from_yr and to_yr):
                continue
            if not any(from_yr <= y <= to_yr for y in all_years):
                continue
            if historical.lower() in text.lower():
                continue  # already has historical name
            # Match modern_name and all declined forms (Russian morphology):
            # use stem = modern minus last char (to cover е/и/ю/я/ь endings),
            # then match stem + 0-3 trailing word chars.
            # E.g. "Тверь" → stem "Твер" → matches "Тверь", "Твери", "Тверью", "Тверю".
            stem = modern[:-1] if len(modern) > 3 else modern
            try:
                text = _re.sub(
                    rf'\b{_re.escape(stem)}\w{{0,3}}\b',
                    historical,
                    text,
                    flags=_re.IGNORECASE,
                )
            except _re.error:
                pass
        return text

    chapters = book.get("chapters", [])
    ch01 = next((c for c in chapters if c.get("id") == "ch_01"), None)
    if not ch01:
        return book

    bio_data = ch01.get("bio_data") or {}
    patched = 0

    # Apply to bio_data.family
    family = bio_data.get("family", [])
    for entry in family:
        # Collect context years from the entry itself
        ctx_years = []
        for fld in ("value", "name", "note"):
            ctx_years.extend(_extract_years_from_text(entry.get(fld) or ""))
        for fld in ("value", "name", "note"):
            orig = entry.get(fld) or ""
            if not orig:
                continue
            new_val = _apply_temporal_rename(orig, ctx_years)
            if new_val != orig:
                entry[fld] = new_val
                patched += 1
                print(f"[TEMPORAL-PASPART] family.{fld}: '{orig}' -> '{new_val}'")

    # Apply to bio_data.timeline
    timeline = bio_data.get("timeline") or ch01.get("timeline") or []
    for period in timeline:
        period_yrs = []
        yr_raw = period.get("years") or period.get("period") or ""
        period_yrs.extend(_extract_years_from_text(yr_raw))
        for fld in ("title", "text", "description"):
            orig = period.get(fld) or ""
            if not orig:
                continue
            new_val = _apply_temporal_rename(orig, period_yrs)
            if new_val != orig:
                period[fld] = new_val
                patched += 1
                print(f"[TEMPORAL-PASPART] timeline.{fld}: '{orig}' -> '{new_val}'")

    print(f"[TEMPORAL-PASPART] {patched} field(s) updated in paspart (bio_data only).")
    return book


# ─────────────────────────────────────────────────────────────────
# Task 043e: anti-facts validation (v62a)
# ─────────────────────────────────────────────────────────────────


def validate_anti_facts(book: dict, anti_facts_config: dict) -> dict:
    """Task 043e: Class 1 predicate-object confabulation check.

    For each anti_fact pair (item_A, item_B): flag warning if BOTH patterns match
    within the same paragraph (≤2 sentences proximity).
    NOT enforce — flag only (risk of false positives).

    anti_facts_config — anti_facts_<subject>.json with anti_facts[]:
        anti_fact_id, item_A_patterns[], item_B_patterns[], reason, severity

    Returns {issues: [...], warnings_count, checked_paragraphs}.
    Idempotent.
    """
    import re as _re

    anti_facts = anti_facts_config.get("anti_facts", [])
    if not anti_facts:
        return {"issues": [], "warnings_count": 0, "checked_paragraphs": 0}

    # Pre-compile patterns
    compiled_af = []
    for af in anti_facts:
        af_id = af.get("anti_fact_id", "?")
        a_pats = af.get("item_A_patterns", [af.get("item_A", "")])
        b_pats = af.get("item_B_patterns", [af.get("item_B", "")])
        severity = af.get("severity", "warning")
        try:
            a_compiled = [_re.compile(p, _re.IGNORECASE) for p in a_pats if p]
            b_compiled = [_re.compile(p, _re.IGNORECASE) for p in b_pats if p]
            compiled_af.append((af_id, a_compiled, b_compiled, severity, af.get("reason", "")))
        except _re.error as e:
            print(f"[ANTI-FACTS] ⚠️ Pattern compile error for {af_id}: {e}")

    issues = []
    checked = 0

    def _split_sentences(text: str) -> list[str]:
        return [s.strip() for s in _re.split(r'(?<=[.!?])\s+', text) if s.strip()]

    for chapter in book.get("chapters", []):
        ch_id = chapter.get("id") or ""
        paras = chapter.get("paragraphs", [])
        if paras:
            para_texts = [p.get("text", "") for p in paras]
        else:
            para_texts = [s for s in _re.split(r"\n\n+", chapter.get("content", "") or "") if s.strip()]

        for para in para_texts:
            if not para.strip():
                continue
            checked += 1
            sentences = _split_sentences(para)

            for af_id, a_compiled, b_compiled, severity, reason in compiled_af:
                a_sent_idxs = [
                    i for i, s in enumerate(sentences)
                    if any(p.search(s) for p in a_compiled)
                ]
                b_sent_idxs = [
                    i for i, s in enumerate(sentences)
                    if any(p.search(s) for p in b_compiled)
                ]
                if not a_sent_idxs or not b_sent_idxs:
                    continue
                # Check if any A and B sentence are within 2 sentences of each other
                for ai in a_sent_idxs:
                    for bi in b_sent_idxs:
                        if abs(ai - bi) <= 2:
                            issues.append({
                                "anti_fact_id": af_id,
                                "chapter_id": ch_id,
                                "sentence_A_idx": ai,
                                "sentence_B_idx": bi,
                                "reason": reason,
                                "snippet": para[:250],
                                "severity": severity,
                            })
                            print(
                                f"[ANTI-FACTS] {severity.upper()}: {af_id} в {ch_id} — "
                                f"{reason[:60]}"
                            )
                            break
                    else:
                        continue
                    break

    warnings = sum(1 for i in issues if i["severity"] == "warning")
    errors = sum(1 for i in issues if i["severity"] == "error")
    print(f"[ANTI-FACTS] {len(issues)} issue(s) ({warnings} warnings, {errors} errors) "
          f"в {checked} параграфах.")
    return {"issues": issues, "warnings_count": warnings, "errors_count": errors,
            "checked_paragraphs": checked}



# ─────────────────────────────────────────────────────────────────
# Task 048d: children_before_birth chronology validator (v63)
# ─────────────────────────────────────────────────────────────────


def validate_children_before_birth(book: dict, chronology_config: dict, config: dict | None = None) -> dict:
    """Task 048d / 048e: Class 12 extension — check children not mentioned before birth.

    v65 (048e): ch_01 skipped; birth_declaration_self_skip applied;
    epilogue generic child refs skipped.
    chronology_config — chronology_periods_karakulina.json.
    Returns {issues: [...], errors_count, warnings_count}.
    Idempotent.
    """
    import re

    cfg = config or {}
    SKIP_CHAPTERS = cfg.get("skip_chapters", ["ch_01"])
    EPILOGUE_SKIP_CHILD_REFS = cfg.get("epilogue_skip_child_refs", True)

    subject_birth = None
    for p in chronology_config.get("periods", []):
        if p.get("period_id") == "birth":
            subject_birth = p.get("year")
            break

    child_birth_years = {}
    for p in chronology_config.get("periods", []):
        pid = p.get("period_id", "")
        year = p.get("year") or p.get("year_start")
        if "birth" not in pid.lower():
            continue
        if "valeriy" in pid.lower() or ("son" in pid.lower() and "birth" in pid.lower()):
            child_birth_years["валери"] = year
        elif "tatyana" in pid.lower() or ("daughter" in pid.lower() and "birth" in pid.lower()):
            child_birth_years["татьян"] = year

    YEAR_RE = re.compile(r"\b((?:19|20)\d{2})\b")
    CHILDREN_GENERAL_RE = re.compile(
        r"\b(дет\w{0,4}|ребят\w{0,2}|детишк\w{0,2})\b", re.IGNORECASE
    )
    GRANDCHILD_RE = re.compile(r"\b(внук\w*|внучк\w*)\b", re.IGNORECASE)
    GENERIC_FAMILY_RE = re.compile(
        r'\b(семь\w{0,4}|создал\w*\s+семь\w*|семейн\w+)\b', re.IGNORECASE
    )

    def _birth_declaration_sentence(sentence: str, birth_year) -> bool:
        """True if sentence itself contains the child's birth year — skip FP."""
        if not birth_year:
            return False
        years = [int(m) for m in YEAR_RE.findall(sentence)]
        return int(birth_year) in years

    issues = []
    for chapter in book.get("chapters", []):
        ch_id = chapter.get("id") or ""
        if ch_id in SKIP_CHAPTERS:
            continue
        is_epilogue = ch_id == "epilogue"
        paras = chapter.get("paragraphs", [])
        para_texts = (
            [p.get("text", "") for p in paras]
            if paras
            else re.split(r"\n\n+", chapter.get("content", "") or "")
        )
        for para in para_texts:
            if not para.strip():
                continue
            years_in_para = [int(m) for m in YEAR_RE.findall(para)]
            if not years_in_para:
                continue
            min_year = min(years_in_para)

            if subject_birth and min_year < subject_birth and CHILDREN_GENERAL_RE.search(para):
                if not (is_epilogue and EPILOGUE_SKIP_CHILD_REFS):
                    issues.append({
                        "chapter_id": ch_id, "type": "children_before_subject_birth",
                        "subject_birth_year": subject_birth, "event_year": min_year,
                        "snippet": para[:200], "severity": "error", "rule": "children_before_birth",
                    })

            para_lower = para.lower()
            for child_stem, child_birth in child_birth_years.items():
                if not child_birth:
                    continue
                if child_stem in para_lower and min_year < child_birth:
                    if _birth_declaration_sentence(para, child_birth):
                        continue  # 048e: birth declaration self-skip
                    if is_epilogue and EPILOGUE_SKIP_CHILD_REFS and GENERIC_FAMILY_RE.search(para):
                        continue  # 048e: generic family refs in epilogue
                    issues.append({
                        "chapter_id": ch_id, "type": "named_child_before_birth",
                        "child_stem": child_stem, "child_birth_year": child_birth,
                        "event_year": min_year, "snippet": para[:200], "severity": "error",
                    })

            if GRANDCHILD_RE.search(para):
                min_cb = min((y for y in child_birth_years.values() if y), default=None)
                if min_cb and min_year < min_cb + 16:
                    if not (is_epilogue and EPILOGUE_SKIP_CHILD_REFS):
                        issues.append({
                            "chapter_id": ch_id, "type": "grandchild_before_child_mature",
                            "min_child_birth_plus_16": min_cb + 16, "event_year": min_year,
                            "snippet": para[:200], "severity": "warning",
                        })

    errors = sum(1 for i in issues if i.get("severity") == "error")
    warnings = sum(1 for i in issues if i.get("severity") == "warning")
    if issues:
        print(f"[CHRONO-048d] {errors} errors, {warnings} warnings.")
    else:
        print("[CHRONO-048d] OK — no children_before_birth violations.")
    return {"issues": issues, "errors_count": errors, "warnings_count": warnings}


# ─────────────────────────────────────────────────────────────────
# Task 051d: year_confidence parser for pin-list entries (v63)
# ─────────────────────────────────────────────────────────────────


def parse_pin_list_year_field(year_cell: str) -> dict:
    """Task 051d: parse year field from pin-list table cell.

    Formats handled:
        "1946"                          -> {year: 1946, year_confidence: "high"}
        "1990-е"                        -> {year_range: ..., year_confidence: "medium"}
        "unknown"                       -> {year: None, year_confidence: "low"}
        "unknown (year_confidence=low)" -> {year: None, year_confidence: "low"}
        "~1940"                         -> {year: 1940, year_confidence: "medium"}
        "1958-62"                       -> {year_start: 1958, year_end: 1962, year_confidence: "high"}
    """
    import re

    cell = (year_cell or "").strip()
    conf_match = re.search(r"year_confidence\s*=\s*(low|medium|high)", cell, re.IGNORECASE)
    explicit_conf = conf_match.group(1).lower() if conf_match else None
    clean = re.sub(r"\([^)]*\)", "", cell).strip()

    if re.match(r"^(unknown|неизвестен|неизвестно|не\s+известен|-)$", clean, re.IGNORECASE):
        return {"year": None, "year_confidence": explicit_conf or "low"}

    range_match = re.match(r"^((?:19|20)\d{2})[–—-]((?:\d{2}|\d{4}))$", clean)
    if range_match:
        start = int(range_match.group(1))
        end_raw = range_match.group(2)
        end = int(end_raw) if len(end_raw) == 4 else int(str(start)[:2] + end_raw)
        return {"year_start": start, "year_end": end, "year_confidence": explicit_conf or "high"}

    approx = re.match(r"^~((?:19|20)\d{2})$", clean)
    if approx:
        return {"year": int(approx.group(1)), "year_confidence": explicit_conf or "medium"}

    decade = re.match(r"^((?:19|20)\d{2})[- ]?(е|х|x|s)$", clean, re.IGNORECASE)
    if decade:
        return {"year_range": clean, "year_confidence": explicit_conf or "medium"}

    exact = re.match(r"^((?:19|20)\d{2})$", clean)
    if exact:
        return {"year": int(exact.group(1)), "year_confidence": explicit_conf or "high"}

    return {"year_raw": cell, "year_confidence": explicit_conf or "low"}


# ─────────────────────────────────────────────────────────────────
# Task 043e-2: epilogue quote density validator (v63)
# ─────────────────────────────────────────────────────────────────


def validate_epilogue_quote_density(book: dict, config: dict = None) -> dict:
    """Task 043e-2: flag epilogue with zero or insufficient voice attribution.

    Defaults: min_quotes=1, max_generic_sentences_pct=0.6.
    Returns {ok: bool, quote_count: int, generic_pct: float, issues: []}.
    Idempotent.
    """
    import re

    cfg = config or {}
    min_quotes = cfg.get("min_quotes_in_epilogue", 1)
    max_generic_pct = cfg.get("max_generic_sentences_pct", 0.6)

    epilogue = None
    for ch in book.get("chapters", []):
        if "epilogue" in (ch.get("id") or ""):
            epilogue = ch
            break
    if epilogue is None:
        return {"ok": True, "skipped": True, "reason": "no epilogue chapter"}

    content = epilogue.get("content") or " ".join(
        p.get("text", "") for p in epilogue.get("paragraphs", [])
    )
    if not content.strip():
        return {"ok": True, "skipped": True, "reason": "empty epilogue"}

    sentences = [s.strip() for s in re.split(r"[.!?]+", content) if len(s.strip()) > 10]
    total = len(sentences)
    if total == 0:
        return {"ok": True, "skipped": True, "reason": "too short"}

    QUOTE_RE = re.compile(
        r"(говор\w+|сказал\w*|вспомин\w+|по\s+её\s+словам|по\s+его\s+словам|"
        r"рассказывает|«[^»]{5,}»|считал\w*|любил\w+\s+говорить|вспоминает|по\s+словам)",
        re.IGNORECASE,
    )
    quote_count = sum(1 for s in sentences if QUOTE_RE.search(s))
    generic_pct = (total - quote_count) / total if total > 0 else 0.0

    issues = []
    ok = True
    if quote_count < min_quotes:
        ok = False
        issues.append({
            "type": "epilogue_zero_quotes", "quote_count": quote_count,
            "min_required": min_quotes, "severity": "error",
        })
        print(f"[EPILOGUE-DENSITY] ERROR: {quote_count} quotes in epilogue (min={min_quotes})")
    if generic_pct > max_generic_pct:
        ok = False
        issues.append({
            "type": "epilogue_too_many_generic",
            "generic_pct": round(generic_pct, 2), "severity": "warning",
        })
        print(f"[EPILOGUE-DENSITY] WARNING: {round(generic_pct*100)}% generic sentences")
    if ok:
        print(f"[EPILOGUE-DENSITY] OK — {quote_count} quotes, {round(generic_pct*100)}% generic.")

    return {
        "ok": ok, "quote_count": quote_count, "total_sentences": total,
        "generic_pct": round(generic_pct, 3), "issues": issues,
    }


# ─────────────────────────────────────────────────────────────────
# Task 038c: entity substitution check (CA v1.5 companion) (v63)
# ─────────────────────────────────────────────────────────────────


def validate_entity_substitution(book: dict, fact_map: dict, transcripts: list) -> dict:
    """Task 038c: detect toponym/institution substitution (book vs transcripts).

    Checks: Калинин→Тверь, Молдавия→Молдова, Химинститут→РХТУ.
    Uses stem matching to handle Russian inflection (Тверь/Твери, Молдова/Молдове etc.).
    Allowed overrides via fact_map.place_canonical[].canonical_form_required=true.
    Returns {ok: bool, issues: []}.
    """
    import re

    allowed_subs = set()
    for place in fact_map.get("place_canonical", []):
        if place.get("canonical_form_required"):
            orig = (place.get("original") or "").lower()
            repl = (place.get("canonical_replacement") or "").lower()
            if orig and repl:
                allowed_subs.add((orig, repl))

    # Each tuple: (orig_stem_re, repl_stem_re, orig_key, repl_key, hint)
    substitution_pairs = [
        (r"\bкалинин\w*\b", r"\bтвер\w+\b", "калинин", "тверь",
         "TR says Калинин, book says Тверь"),
        (r"\bмолдав\w+\b", r"\bмолдов\w+\b", "молдавия", "молдова",
         "TR says Молдавия, book says Молдова"),
        (r"\bхиминститут\w*\b", r"\bрхту\b", "химинститут", "рхту",
         "TR says Химинститут, book says РХТУ"),
        (r"\bхиминститут\w*\b", r"российск\w+\s+химико.технологическ\w+", "химинститут",
         "российский химико-технологический", "institution full name sub"),
    ]

    tr_text = " ".join((t or "") for t in (transcripts or [])).lower()
    issues = []

    for orig_re, repl_re, orig_key, repl_key, hint in substitution_pairs:
        if (orig_key, repl_key) in allowed_subs:
            continue
        if not re.search(orig_re, tr_text):
            continue
        for ch in book.get("chapters", []):
            ch_id = ch.get("id") or ""
            ch_text = (ch.get("content") or "") + " ".join(
                p.get("text", "") for p in ch.get("paragraphs", [])
            )
            ch_lower = ch_text.lower()
            if re.search(repl_re, ch_lower) and not re.search(orig_re, ch_lower):
                issues.append({
                    "type": "entity_substitution", "original": orig_key,
                    "substituted": repl_key, "chapter_id": ch_id,
                    "hint": hint, "severity": "warning",
                })
                print(f"[ENTITY-SUB] WARNING: {orig_key} -> {repl_key} in {ch_id}. {hint}")

    ok = len(issues) == 0
    if ok:
        print("[ENTITY-SUB] OK — no entity substitutions.")
    return {"ok": ok, "issues": issues}


# ─────────────────────────────────────────────────────────────────
# Task 044g: bio_data.family format normalisation + locative case (v63)
# ─────────────────────────────────────────────────────────────────


def validate_bio_data_family_format(bio_data: dict, config: dict = None) -> dict:
    """Task 044g: validate bio_data.family entries for format compliance.

    Expected: "<Relation>: <ФИО>" with optional parenthetical note.
    Also checks locative case in place fields.
    Returns {ok: bool, issues: [], malformed_count: int}.
    """
    import re

    issues = []
    family = bio_data.get("family") or []
    if isinstance(family, str):
        family = [family]

    for entry in family:
        if not isinstance(entry, str) or not entry.strip():
            continue
        es = entry.strip()
        if ":" not in es:
            issues.append({
                "type": "malformed_entry", "entry": es,
                "reason": "no colon separator", "severity": "warning",
            })
            continue
        parts = es.split(":", 1)
        rel = parts[0].strip()
        name = parts[1].strip() if len(parts) > 1 else ""
        if not rel or rel in ("?", "-", ""):
            issues.append({"type": "empty_relation", "entry": es, "severity": "error"})
        if not name or name in ("?", "-", "", "(неизвестно)"):
            issues.append({
                "type": "empty_name", "entry": es,
                "relation_term": rel, "severity": "warning",
            })

    # Build nominative-city set: start from universal known cities, then extend
    # from gazeteer (Option A: config["gazeteer"]["temporal_place_names"] if present).
    # This makes the check generic — no hardcoded subject-specific city names.
    _nominative_cities = {"Москва", "Ленинград", "Санкт-Петербург", "Петроград"}
    _gazeteer = (config or {}).get("gazeteer") if config else None
    if _gazeteer and isinstance(_gazeteer, dict):
        for tpn in _gazeteer.get("temporal_place_names", []):
            for key in ("modern_name", "historical_name"):
                city = tpn.get(key, "")
                if city:
                    _nominative_cities.add(city)
        for corr in _gazeteer.get("topo_corrections", {}).values():
            # canonical replacement city names
            if corr and corr[0].isupper() and " " not in corr:
                _nominative_cities.add(corr)
    _city_alts = "|".join(re.escape(c) for c in sorted(_nominative_cities, key=len, reverse=True))
    NOMINATIVE_CITY_RE = re.compile(rf"\bв\s+({_city_alts})\b")

    for field in ("birth_place", "death_place", "lived_in"):
        val = bio_data.get(field) or ""
        if isinstance(val, list):
            val = " ".join(str(v) for v in val)
        if not val:
            continue
        m = NOMINATIVE_CITY_RE.search(val)
        if m:
            issues.append({
                "type": "locative_case_error", "field": field,
                "value": val, "match": m.group(0), "severity": "error",
                "hint": f"Use prepositional case: «в {m.group(1)}е/и» not «в {m.group(1)}»",
            })

    malformed = sum(1 for i in issues if i.get("type") == "malformed_entry")
    ok = all(i.get("severity") != "error" for i in issues)
    if issues:
        print(f"[BIO-FAMILY-FORMAT] {len(issues)} issues (malformed={malformed})")
    else:
        print("[BIO-FAMILY-FORMAT] OK — all family entries valid.")
    return {"ok": ok, "issues": issues, "malformed_count": malformed}


# ============================================================
# v64 VALIDATORS — task 043h, 046e, 049f (revision orchestrator)
# 046d (historical notes enrichment)
# ============================================================

def validate_narrative_truism(book: dict, config: dict | None = None) -> dict:
    """Detect Class 17 narrative truism patterns in narrative chapters (task 043h).

    Checks: obvious_responsibility_constatation, everything_fell_on_shoulders,
    accepted_calmly, required_strength_and_character, was_not_easy_in_those_years,
    this_required_dedication, had_to_show_X.

    Returns dict with issues list, errors_count, warnings_count.
    """
    import re, json, os

    if config is None:
        cfg_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "collab", "context", "narrative_stop_phrases.json",
        )
        if not os.path.exists(cfg_path):
            cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "narrative_stop_phrases.json")
        try:
            with open(cfg_path, encoding="utf-8") as f:
                config = json.load(f)
        except Exception:
            config = {}

    truism_cat_names = set(
        config.get("narrative_truism", {}).get("category_names", [
            "obvious_responsibility_constatation", "everything_fell_on_shoulders",
            "accepted_calmly", "required_strength_and_character",
            "was_not_easy_in_those_years", "this_required_dedication", "had_to_show_X",
        ])
    )

    all_patterns = {
        p["category"]: p
        for p in config.get("generic_categorical_patterns", [])
        if p.get("category") in truism_cat_names and "pattern" in p
    }

    def _is_quoted(sentence: str) -> bool:
        return bool(re.search(r'«[^»]*' + re.escape(sentence[:20]), sentence) or
                    sentence.strip().startswith('«'))

    issues = []
    for ch in book.get("chapters", []):
        chid = ch.get("id")
        if chid == "ch_01":
            continue
        content = ch.get("content", "") or ""
        sentences = re.split(r'(?<=[.!?])\s+', content)
        for sent in sentences:
            if _is_quoted(sent):
                continue
            for cat_name, pat_obj in all_patterns.items():
                pat = pat_obj.get("pattern", "")
                if not pat:
                    continue
                if re.search(pat, sent, re.IGNORECASE):
                    issues.append({
                        "type": "narrative_truism",
                        "category": cat_name,
                        "chapter_id": chid,
                        "snippet": sent.strip(),
                        "severity": pat_obj.get("severity", "warning"),
                        "suggestion": pat_obj.get("suggestion", "delete_sentence"),
                        "reason": pat_obj.get("reason", "narrative truism"),
                    })

    return {
        "issues": issues,
        "errors_count": sum(1 for i in issues if i["severity"] == "error"),
        "warnings_count": sum(1 for i in issues if i["severity"] == "warning"),
    }


def validate_personal_historical_voice(
    book: dict,
    config: dict | None = None,
    pin_list_anchors: list | None = None,
) -> dict:
    """Detect Class 18 personal-historical voice patterns in narrative chapters (task 046e).

    Returns dict with markers_found_per_chapter, thresholds, issues, errors_count, warnings_count.
    """
    import re

    thresholds = (config or {}).get("thresholds_per_chapter", {
        "ch_02": 3,
        "ch_03": 2,
        "ch_04": 1,
        "epilogue": 0,
    })

    patterns = [
        r'\bкак\s+(я|мы)\s+помн\w+',
        r'\bтогда\s+(в|у)\s+(нашей|нас)',
        r'\bкогда\s+(я|мы)\s+(был\w+|жил\w+|росл\w+)',
        r'\bпомн\w+,\s+(в|на)\s+\w+\s+(я|мы)',
        r'\bв\s+(советск\w+|те)\s+\w*\s*врем[еяё]\w*',
        r'\bпо\s+(тем|советск\w+|нашим)\s+\w*\s*времен\w*',
        r'\bу\s+нас\s+в\s+(семь\w+|доме|городе|посёлке|институте)',
    ]

    counts = {}
    for ch in book.get("chapters", []):
        chid = ch.get("id")
        if chid == "ch_01":
            continue
        content = ch.get("content", "") or ""
        total = 0
        for pat in patterns:
            total += len(re.findall(pat, content, re.IGNORECASE))
        counts[chid] = total

    issues = []
    for chid, expected in thresholds.items():
        if expected == 0:
            continue
        found = counts.get(chid, 0)
        if found < expected:
            issues.append({
                "type": "personal_historical_voice",
                "category": "below_threshold",
                "chapter_id": chid,
                "found": found,
                "expected": expected,
                "severity": "warning",
                "suggestion": (
                    f"Добавить \u2265{expected - found} personal-historical voice "
                    f"markers в {chid}. Examples: 'как [rapporteur] помнит, в [период]...', "
                    f"'\u0442\u043e\u0433\u0434\u0430 у нас в семье...', 'когда [rapporteur] был ребёнком, ...'. "
                    f"Использовать narrator_voice_anchors из pin-list."
                ),
                "reason": "Class 18 personal-historical voice — рассказчик помещает личную память в исторический контекст",
            })

    return {
        "markers_found_per_chapter": counts,
        "thresholds": thresholds,
        "issues": issues,
        "errors_count": sum(1 for i in issues if i["severity"] == "error"),
        "warnings_count": sum(1 for i in issues if i["severity"] == "warning"),
    }


_KNOWN_VALIDATORS = [
    "chronology_check",
    "pin_list_depth",
    "discourse_markers",
    "narrative_stop_phrases",
    "narrative_truism",
    "anti_facts",
    "epilogue_stop_phrases",
    "epilogue_quote_density",
    "personal_historical_voice",
    "timeline_anchors",
    "entity_substitution",
    "cross_paragraph_duplication",
    "historical_notes_distribution",
    "required_episodes_coverage",
    "descendants_in_early_context",
]


def collect_revision_hints(
    book_draft: dict,
    validator_outputs: dict,
    config: dict | None = None,
) -> list:
    """Collect revision_hints from validator outputs for GW revision pass (task 049f/049f-2).

    v65 fix: covers ALL validators (not subset); warning-level findings included with
    must_apply=False; missing validators logged explicitly (not silently skipped).

    validator_outputs: dict of {validator_name: output_dict}
    Each output_dict should have "issues" list.
    Returns list of hint dicts in GW ПРАВИЛО 13 format.
    """
    hints = []
    hint_counter = 0

    for validator_name in _KNOWN_VALIDATORS:
        output = validator_outputs.get(validator_name)
        if output is None:
            print(f"[collect_revision_hints] WARNING: validator '{validator_name}' not present in outputs — skipped")
            continue
        if not isinstance(output, dict):
            print(f"[collect_revision_hints] WARNING: validator '{validator_name}' output is not a dict")
            continue
        issues = output.get("issues", [])
        for issue in issues:
            hint_counter += 1
            hint = _build_revision_hint(
                hint_id=f"h_{hint_counter:03d}",
                validator=validator_name,
                issue=issue,
                book_draft=book_draft,
            )
            if hint:
                hints.append(hint)

    # Also include any additional validators passed but not in _KNOWN_VALIDATORS
    for validator_name, output in validator_outputs.items():
        if validator_name in _KNOWN_VALIDATORS:
            continue
        if not isinstance(output, dict):
            continue
        issues = output.get("issues", [])
        for issue in issues:
            hint_counter += 1
            hint = _build_revision_hint(
                hint_id=f"h_{hint_counter:03d}",
                validator=validator_name,
                issue=issue,
                book_draft=book_draft,
            )
            if hint:
                hints.append(hint)

    return hints


def _build_revision_hint(hint_id: str, validator: str, issue: dict, book_draft: dict) -> dict | None:
    """Convert single validator issue to GW revision_hint format (task 049f/049f-2).

    v65: Do NOT silently drop hints with no snippet — use a placeholder so GW can still apply.
    """
    snippet = issue.get("snippet") or _extract_snippet_from_book(book_draft, issue)
    if not snippet:
        # v65 fix: don't drop — build a generic chapter-context snippet from issue fields
        ch_id = issue.get("chapter_id", "unknown")
        ep_id = issue.get("episode_id") or issue.get("person_name") or issue.get("type") or "issue"
        snippet = f"[chapter {ch_id} — {ep_id}: see validator output]"

    hint = {
        "hint_id": hint_id,
        "validator": validator,
        "category": issue.get("category") or issue.get("type") or "unknown",
        "chapter_id": issue.get("chapter_id"),
        "severity": issue.get("severity", "warning"),
        "snippet": snippet,
        "reason": _build_revision_reason(validator, issue),
        "suggestion": issue.get("suggestion") or _build_revision_suggestion(validator, issue),
        "must_apply": issue.get("severity") == "error",
    }
    return hint


def _extract_snippet_from_book(book_draft: dict, issue: dict) -> str | None:
    """Try to find snippet in book_draft by chapter + keyword match."""
    import re
    chid = issue.get("chapter_id")
    for ch in book_draft.get("chapters", []):
        if ch.get("id") != chid:
            continue
        content = ch.get("content", "") or ""
        # Try to find sentence containing key terms from issue
        key = issue.get("pattern_matched") or issue.get("episode_id") or issue.get("person_name")
        if key:
            for sent in re.split(r'(?<=[.!?])\s+', content):
                if key.lower() in sent.lower():
                    return sent.strip()[:300]
    return None


def _build_revision_reason(validator: str, issue: dict) -> str:
    """Generate human-readable reason for hint."""
    cat = issue.get("category") or issue.get("type") or "unknown"
    severity = issue.get("severity", "warning")
    reason_detail = issue.get("reason", "")
    if reason_detail:
        return f"{validator}/{cat} ({severity}): {reason_detail}"
    return f"{validator}/{cat} ({severity})"


def _build_revision_suggestion(validator: str, issue: dict) -> str:
    """Generate concrete suggestion per validator category (task 049f/049f-2 extended)."""
    cat = issue.get("category") or issue.get("type") or ""

    if validator == "chronology_check":
        if cat in ("person_mentioned_before_birth", "children_mentioned_before_first_child_birth"):
            person = issue.get("person_name", "[ребёнок]")
            year = issue.get("event_year_range") or issue.get("first_child_birth", "")
            return (
                f"Удалить упоминание [{person}] в этом контексте. "
                f"Период предшествует рождению ({year}). "
                f"Заменить на 'занималась домом' / 'вела хозяйство'."
            )

    if validator == "narrative_truism":
        return issue.get("suggestion") or "delete_sentence"

    if validator in ("narrative_stop_phrases", "style_checks"):
        if "speciality_defined_life" in cat:
            return ("Удалить causal claim (часть про 'определила жизнь/карьеру'). "
                    "Оставить factual content (год обучения, специальность).")
        if "episode_especially_remembered" in cat:
            return "Удалить subjective claim о memorability. Оставить factual content."
        if "motivation_attribution_seemed" in cat:
            return "Удалить attribution мотивации без источника в TR."
        if "typical_for_generation" in cat:
            return "delete_sentence (целиком, без замены)"
        if "class11_not_loved" in cat:
            return (
                "Переписать обобщённо: «не любил советов» / «не любил [X]», "
                "без перечисления частных категорий. Семантическое правило — убрать перечисление, "
                "оставить только обобщение либо ОДНУ конкретную деталь из source_quote."
            )
        return issue.get("suggestion") or "Переписать без causal claim / generic listing / truism."

    if validator == "pin_list_depth":
        ep_id = issue.get("episode_id", "")
        actual = issue.get("actual_sentences", "?")
        min_req = issue.get("min_required", 3)
        return (
            f"Развернуть эпизод [{ep_id}] на \u2265{min_req} sentences per ПРАВИЛО 12. "
            f"Текущая глубина: {actual} sent. "
            f"Добавить: setup год+место+кто / детали действия / последствие."
        )

    if validator == "anti_facts":
        a = issue.get("item_A", "[A]")
        b = issue.get("item_B", "[B]")
        return (f"Не объединять [{a}] с [{b}] в одном предложении. "
                f"В источнике это отдельные позиции.")

    if validator == "discourse_markers":
        if cat == "below_threshold":
            expected = issue.get("expected", 8)
            found = issue.get("found", 0)
            chid = issue.get("chapter_id", "")
            return (
                f"Добавить \u2265{expected - found} discourse markers в {chid}. "
                f"Pattern: '[rapporteur] вспоминает' / 'по словам [rapporteur]' / "
                f"'как помнит [родственное_отношение]'."
            )

    if validator == "personal_historical_voice":
        if cat == "below_threshold":
            expected = issue.get("expected", 3)
            found = issue.get("found", 0)
            chid = issue.get("chapter_id", "")
            return (
                f"Добавить \u2265{expected - found} personal-historical voice anchors в {chid}. "
                f"'[rapporteur] помнит как в [период] ...' / 'тогда в нашей семье ...' / "
                f"'когда [rapporteur] был ребёнком, в [период], ...'. "
                f"Использовать narrator_voice_anchors из pin-list."
            )
        return issue.get("suggestion", "Добавить personal-historical voice anchors из pin-list.")

    if validator == "epilogue_stop_phrases":
        phrase = issue.get("phrase") or issue.get("snippet", "...")[:60]
        return f"Удалить epilogue stop-фразу: '{phrase}'."

    if validator == "epilogue_quote_density":
        return (
            "Снизить density cited phrases в epilogue. "
            "Распределить характерные слова по ch_02/ch_03/ch_04, в epilogue оставить spokoyno."
        )

    if validator == "timeline_anchors":
        if cat == "anchor_absorbed":
            return (
                f"Период '{issue.get('anchor_id')}' поглощён другим. "
                f"Разделить как отдельный block в ch_01 markdown."
            )

    if validator == "entity_substitution":
        return f"Replace '{issue.get('from')}' → '{issue.get('to')}' в snippet (на {issue.get('chapter_id')})."

    if validator == "cross_paragraph_duplication":
        orig_ch = issue.get("original_chapter_id", "?")
        orig_idx = issue.get("original_paragraph_index", "?")
        return (
            f"Дословный повтор paragraph из {orig_ch} (paragraph index {orig_idx}). "
            f"Удалить дубликат либо переписать со ссылкой (без повтора)."
        )

    if validator == "historical_notes_distribution":
        chid = issue.get("chapter_id", "?")
        found = issue.get("found", 0)
        expected = issue.get("expected", 1)
        return (
            f"Добавить \u2265{expected - found} historical_note inline в {chid} (***текст***). "
            f"Контекст: исторический фон эпохи, контекст характеристик или эпизодов."
        )

    if validator == "required_episodes_coverage":
        ep_id = issue.get("episode_id", "?")
        title = issue.get("title", "?")
        return (
            f"Episode [{ep_id}] «{title[:50]}» — required_in_narrative, отсутствует. "
            f"Развернуть в ch_03 или ch_04 на \u22653 sentences. "
            f"Маркеры: {issue.get('markers', [])}. Source quote из pin-list."
        )

    if validator == "descendants_in_early_context":
        name = issue.get("person_name", "?")
        year = issue.get("event_year_in_paragraph", "?")
        min_birth = issue.get("inferred_min_birth", "?")
        return (
            f"Удалить упоминание [{name}] в paragraph про {year} год — "
            f"этот родственник родился ~{min_birth}+. "
            f"Альтернатива: переписать через generic 'старшая сестра' / 'её родственники' без named descendants."
        )

    return issue.get("suggestion") or "Переписать или удалить flagged sentence."


def audit_revision_diff(
    book_draft: dict,
    book_after_revision: dict,
    revision_hints: list,
) -> dict:
    """Sanity check: revision pass changed only flagged sentences (task 049f).

    Returns dict with hints_count, applied, skipped, unauthorized_changes,
    writing_notes_proof.
    """
    import difflib, re

    def _extract_text(book: dict) -> dict:
        """Extract chapter_id -> content text."""
        return {
            ch["id"]: (ch.get("content") or "")
            for ch in book.get("chapters", [])
        }

    draft_texts = _extract_text(book_draft)
    revised_texts = _extract_text(book_after_revision)

    # Gather all flagged snippets
    flagged_snippets = {h["snippet"][:80].lower() for h in revision_hints if h.get("snippet")}

    unauthorized_changes = []
    applied = []
    skipped = []

    for chid in draft_texts:
        draft_sents = re.split(r'(?<=[.!?])\s+', draft_texts.get(chid, ""))
        revised_sents = re.split(r'(?<=[.!?])\s+', revised_texts.get(chid, ""))

        diff = list(difflib.unified_diff(draft_sents, revised_sents, lineterm=""))
        changed_lines = [l[1:].strip() for l in diff if l.startswith(("+", "-")) and not l.startswith(("+++", "---"))]

        for line in changed_lines:
            if not line:
                continue
            line_lower = line.lower()
            is_flagged = any(
                snip in line_lower or line_lower in snip
                for snip in flagged_snippets
            )
            if not is_flagged and len(line) > 15:
                unauthorized_changes.append({
                    "chapter_id": chid,
                    "diff_snippet": line[:200],
                })

    # Map writing_notes
    writing_notes = (
        book_after_revision.get("writing_notes") or
        book_after_revision.get("book_draft", {}).get("writing_notes") or {}
    )
    rule13_applied = writing_notes.get("rule13_revision_applied", [])

    for hint in revision_hints:
        hid = hint["hint_id"]
        match = next((a for a in rule13_applied if a.get("hint_id") == hid), None)
        if match:
            applied.append({"hint_id": hid, "action": match.get("action")})
        else:
            skipped.append({"hint_id": hid, "reason": "not_in_writing_notes"})

    return {
        "hints_count": len(revision_hints),
        "applied": applied,
        "skipped": skipped,
        "unauthorized_changes": unauthorized_changes,
        "unauthorized_changes_count": len(unauthorized_changes),
        "writing_notes_proof": rule13_applied,
        "revision_failed": writing_notes.get("rule13_revision_failed", False),
    }


def _count_inline_historical_notes(book: dict) -> int:
    """Count ***...*** inline historical notes across all chapters (task 046d)."""
    import re
    count = 0
    for ch in book.get("chapters", []):
        content = ch.get("content", "") or ""
        count += len(re.findall(r'\*{3}[^*]+\*{3}', content))
    return count


def enrich_historical_notes_inline(
    book: dict,
    fact_map: dict,
    pin_list_historical_anchors: list | None = None,
    config: dict | None = None,
) -> dict:
    """Post-Stage 2 enrichment: add inline historical_notes until minimum (task 046d).

    If current inline count < min_inline_notes: identify slots in ch_02/ch_03
    paragraphs with year mentions that match timeline events, then insert
    placeholder *** historical context *** notes. Actual LLM call for context
    happens in stage2 runner (historian agent reuse). This function provides
    the slot-detection + insertion scaffold.

    Returns modified book (or original if already sufficient).
    """
    import re

    cfg = config or {}
    min_inline = cfg.get("min_inline_notes", 5)
    max_inline = cfg.get("max_inline_notes", 12)
    skip_chapters = cfg.get("skip_chapters", ["ch_01"])

    current = _count_inline_historical_notes(book)
    if current >= min_inline:
        return book

    # Build year→event map from fact_map
    year_events = {}
    for ev in fact_map.get("timeline", []):
        yr = ev.get("year")
        if yr and isinstance(yr, (int, str)):
            try:
                y = int(str(yr)[:4])
                if y not in year_events:
                    year_events[y] = []
                year_events[y].append(ev.get("title", "") or ev.get("description", ""))
            except ValueError:
                pass

    # If pin-list anchors provided, also use those
    if pin_list_historical_anchors:
        for anchor in pin_list_historical_anchors:
            yr = anchor.get("year")
            if yr:
                try:
                    y = int(str(yr)[:4])
                    if y not in year_events:
                        year_events[y] = []
                    year_events[y].append(anchor.get("context", ""))
                except ValueError:
                    pass

    slots_filled = 0
    last_insert_paragraph_idx = -3  # tracking distance between notes

    for ch in book.get("chapters", []):
        chid = ch.get("id")
        if chid in skip_chapters:
            continue
        content = ch.get("content") or ""
        paragraphs = content.split("\n\n")
        new_paragraphs = []
        for pidx, para in enumerate(paragraphs):
            new_paragraphs.append(para)
            if current + slots_filled >= min_inline:
                continue
            if (pidx - last_insert_paragraph_idx) < 2:
                continue
            # Check if paragraph has a year mention
            year_mentions = re.findall(r'\b(1[89]\d{2}|20[012]\d)\b', para)
            if not year_mentions:
                continue
            # Find best year with event context
            for yr_str in year_mentions:
                yr = int(yr_str)
                events_for_year = (
                    year_events.get(yr) or
                    year_events.get(yr - 1) or
                    year_events.get(yr + 1)
                )
                if not events_for_year:
                    continue
                # Insert placeholder note (actual text filled by historian in runner)
                note_placeholder = (
                    f"***[Исторический контекст {yr}: {events_for_year[0][:80]}...]***"
                )
                new_paragraphs.append(note_placeholder)
                slots_filled += 1
                last_insert_paragraph_idx = pidx
                break

        ch["content"] = "\n\n".join(new_paragraphs)

    return book


# ─────────────────────────────────────────────────────────────────
# Task 049g: preserve_root_level_metadata — Stage 3 writing_notes fix
# ─────────────────────────────────────────────────────────────────

def preserve_root_level_metadata(book_processed: dict, book_pre_processing: dict) -> dict:
    """Restore root-level metadata fields if post-processing removed them (task 049g).

    v64 bug: writing_notes = {} in book_FINAL_stage3 though GW wrote it in book_REVISED.
    This function is called AFTER all Stage 3 post-processing steps.

    Fields preserved (only if empty/missing in processed, but present in pre-processing):
    - writing_notes (GW proof of attention + rule13_revision_applied)
    - facts_used
    - revision_log
    - metadata

    For writing_notes: also merges sub-keys from pre-processing that are missing in processed
    (e.g. rule13_revision_applied added by revision pass is not present in Stage 3 output).
    Does NOT overwrite non-empty post-LE values.
    """
    METADATA_FIELDS = ["writing_notes", "facts_used", "revision_log", "metadata"]
    restored = []
    merged = []
    for field in METADATA_FIELDS:
        pre_val = book_pre_processing.get(field)
        if not pre_val:
            continue
        post_val = book_processed.get(field)
        if not post_val or post_val == {} or post_val == [] or post_val == "":
            book_processed[field] = pre_val
            restored.append(field)
            print(f"[preserve_root_level_metadata] Restored '{field}' from pre-LE snapshot")
        elif field == "writing_notes" and isinstance(post_val, dict) and isinstance(pre_val, dict):
            # Merge sub-keys that are missing in stage3 (e.g. rule13_* from revision pass)
            missing_subkeys = [k for k in pre_val if k not in post_val or post_val[k] is None]
            for subkey in missing_subkeys:
                if pre_val[subkey] is not None:
                    book_processed[field][subkey] = pre_val[subkey]
                    merged.append(f"writing_notes.{subkey}")
            if missing_subkeys:
                print(f"[preserve_root_level_metadata] Merged writing_notes sub-keys: {missing_subkeys}")
    if not restored and not merged:
        print("[preserve_root_level_metadata] OK — no metadata fields needed restoration")
    return book_processed


# ─────────────────────────────────────────────────────────────────
# Task 048f: Class 12 extend — descendants in ancestor early context
# ─────────────────────────────────────────────────────────────────

def _find_parent_via_relation_pattern(descendant: dict, fact_map: dict) -> str | None:
    """Heuristic: try to find parent name via fact_map persons by relation matching."""
    rel = (descendant.get("relation_to_subject") or "").lower()
    persons = fact_map.get("persons", [])
    if "племянник" in rel or "племянниц" in rel:
        # Parent should be a sibling of subject
        for p in persons:
            p_rel = (p.get("relation_to_subject") or "").lower()
            if "сестра" in p_rel or "брат" in p_rel:
                return p.get("name")
    if "внук" in rel:
        # Parent should be a child of subject
        for p in persons:
            p_rel = (p.get("relation_to_subject") or "").lower()
            if "сын" in p_rel or "дочь" in p_rel:
                return p.get("name")
    return None


def validate_descendants_in_early_context(
    book: dict,
    fact_map: dict,
    config: dict | None = None,
) -> dict:
    """Task 048f: Class 12 extend — named descendants mentioned in ancestor's early-age context.

    Checks if a nephew/niece/grandchild is named in a paragraph about the subject's early years
    (years < descendant's inferred min birth). Warning level — heuristic-based.

    Generic algorithm: relation-based descendant chain, profession-based age hints,
    works for any subject.

    Returns {issues: [...], errors_count: 0, warnings_count: N}.
    Idempotent.
    """
    import re

    cfg = config or {}
    DESCENDANT_RELATIONS = cfg.get("descendant_relations", [
        "племянник", "племянница", "внук", "внучка",
        "внучатый племянник", "правнук", "правнучка",
    ])
    AGE_ADJ = cfg.get("default_age_adjustment", 18)
    SKIP_CHAPTERS = cfg.get("skip_chapters", ["ch_01", "epilogue"])

    persons = fact_map.get("persons", [])
    descendants = [
        p for p in persons
        if any(r in (p.get("relation_to_subject") or "").lower() for r in DESCENDANT_RELATIONS)
    ]
    if not descendants:
        return {"issues": [], "errors_count": 0, "warnings_count": 0}

    YEAR_RE = re.compile(r'\b(?:19|20)\d{2}\b')

    def _infer_descendant_min_birth(desc: dict) -> int | None:
        candidates = []
        parent_link = desc.get("parent") or _find_parent_via_relation_pattern(desc, fact_map)
        if parent_link:
            parent = next((p for p in persons if p.get("name") == parent_link), None)
            if parent:
                if parent.get("marriage_year"):
                    candidates.append(int(parent["marriage_year"]) + 1)
                if parent.get("birth_year"):
                    candidates.append(int(parent["birth_year"]) + AGE_ADJ)
        prof = (desc.get("profession") or "").lower()
        if any(kw in prof for kw in ["лётчик", "военный", "врач", "инженер", "учител"]):
            subject_birth = fact_map.get("subject", {}).get("birth_year")
            if subject_birth:
                candidates.append(int(subject_birth) + 30)
        return max(candidates) if candidates else None

    issues = []
    for ch in book.get("chapters", []):
        if ch.get("id") in SKIP_CHAPTERS:
            continue
        content = ch.get("content", "") or ""
        for paragraph in content.split("\n\n"):
            if not paragraph.strip():
                continue
            years = [int(m) for m in YEAR_RE.findall(paragraph)]
            if not years:
                continue
            min_year_in_para = min(years)
            para_lower = paragraph.lower()
            for desc in descendants:
                name = (desc.get("name") or "").strip()
                if len(name) < 3 or name.lower() not in para_lower:
                    continue
                inferred_min = _infer_descendant_min_birth(desc)
                if inferred_min and min_year_in_para < inferred_min:
                    issues.append({
                        "type": "descendant_in_ancestor_early_context",
                        "category": "class12_extend",
                        "chapter_id": ch["id"],
                        "person_name": name,
                        "inferred_min_birth": inferred_min,
                        "event_year_in_paragraph": min_year_in_para,
                        "snippet": paragraph[:200],
                        "severity": "warning",
                        "suggestion": (
                            f"Удалить упоминание [{name}] в paragraph про "
                            f"{min_year_in_para} год — этот родственник родился ≥{inferred_min}. "
                            f"Альтернатива: переписать через generic 'старшая сестра' / "
                            f"'её родственники' без named descendants."
                        ),
                        "reason": "Class 12 extend — потомок упомянут в context раннего возраста предка",
                    })
                    break  # one flag per paragraph per chapter per person
    return {
        "issues": issues,
        "errors_count": 0,
        "warnings_count": len(issues),
    }


# ─────────────────────────────────────────────────────────────────
# Task 048g: Class 19 NEW — cross-paragraph text duplication
# ─────────────────────────────────────────────────────────────────

def _normalize_for_dedup(text: str) -> str:
    """Normalize text for duplicate detection (task 048g)."""
    import re
    text = re.sub(r'\*+|_+|`+|#+', '', text)
    text = re.sub(r'\s+', ' ', text.lower().strip())
    return text.strip(' .,;:!?-\u2014\u2013')


def _text_similarity(a: str, b: str) -> float:
    """SequenceMatcher ratio — lightweight, no extra deps (task 048g)."""
    from difflib import SequenceMatcher
    return SequenceMatcher(None, a, b).ratio()


def validate_cross_paragraph_duplication(book: dict, config: dict | None = None) -> dict:
    """Task 048g: Class 19 NEW — detect cross-paragraph дословный повтор.

    Algorithm: extract all paragraphs >= min_chars, compare pairwise with SequenceMatcher.
    If similarity >= threshold — flag duplicate.

    Generic: text similarity — no subject knowledge required.
    Returns {issues: [...], errors_count: N, warnings_count: 0}.
    Idempotent.
    """
    cfg = config or {}
    min_chars = cfg.get("min_paragraph_chars", 100)
    threshold = cfg.get("similarity_threshold", 0.85)
    skip_chapters = cfg.get("skip_chapters", ["ch_01"])

    paragraphs = []
    for ch in book.get("chapters", []):
        if ch.get("id") in skip_chapters:
            continue
        content = ch.get("content", "") or ""
        for idx, para in enumerate(content.split("\n\n")):
            normalized = _normalize_for_dedup(para)
            if len(normalized) >= min_chars:
                paragraphs.append({
                    "chapter_id": ch["id"],
                    "paragraph_index": idx,
                    "text": para,
                    "normalized": normalized,
                })

    issues = []
    seen: list = []
    for p in paragraphs:
        duplicate_found = False
        for prev in seen:
            sim = _text_similarity(prev["normalized"], p["normalized"])
            if sim >= threshold:
                issues.append({
                    "type": "cross_paragraph_duplication",
                    "category": "duplicate_paragraph",
                    "similarity": round(sim, 3),
                    "original_chapter_id": prev["chapter_id"],
                    "original_paragraph_index": prev["paragraph_index"],
                    "duplicate_chapter_id": p["chapter_id"],
                    "duplicate_paragraph_index": p["paragraph_index"],
                    "chapter_id": p["chapter_id"],
                    "snippet": p["text"][:200],
                    "severity": "error",
                    "suggestion": (
                        f"Удалить duplicate paragraph (index {p['paragraph_index']} в "
                        f"{p['chapter_id']}). Оригинал в {prev['chapter_id']} "
                        f"(index {prev['paragraph_index']}). "
                        f"Если содержит уникальный fact — переписать без дословного повтора."
                    ),
                    "reason": "Class 19 — cross-paragraph дословное повторение текста",
                })
                duplicate_found = True
                break
        if not duplicate_found:
            seen.append(p)

    return {
        "issues": issues,
        "errors_count": len(issues),
        "warnings_count": 0,
    }


# ─────────────────────────────────────────────────────────────────
# Task 046f: historical_notes per-chapter distribution validator
# ─────────────────────────────────────────────────────────────────

def validate_historical_notes_distribution(book: dict, config: dict | None = None) -> dict:
    """Task 046f: Check per-chapter distribution of historical_notes (field + inline ***.

    Default thresholds: ch_02≥3, ch_03≥2, ch_04≥1, epilogue=0.
    Warning level — distribution hint for historian enrichment and GW revision.
    Returns {per_chapter, thresholds, issues, total_field, total_inline, errors_count, warnings_count}.
    Idempotent.
    """
    import re

    cfg = config or {}
    thresholds = cfg.get("thresholds_per_chapter", {
        "ch_02": 3,
        "ch_03": 2,
        "ch_04": 1,
        "epilogue": 0,
    })

    per_chapter: dict = {}
    # Field-level notes attribution
    for note in book.get("historical_notes", []):
        ch_id = note.get("chapter_id", "ch_02")
        per_chapter.setdefault(ch_id, {"field": 0, "inline": 0, "total": 0})
        per_chapter[ch_id]["field"] += 1

    # Inline notes: count *** patterns per chapter
    INLINE_RE = re.compile(r'\*{3}[^*]+\*{3}')
    for ch in book.get("chapters", []):
        chid = ch.get("id")
        if chid == "ch_01":
            continue
        content = ch.get("content", "") or ""
        inline_count = len(INLINE_RE.findall(content))
        per_chapter.setdefault(chid, {"field": 0, "inline": 0, "total": 0})
        per_chapter[chid]["inline"] += inline_count

    for chid, counts in per_chapter.items():
        counts["total"] = counts["field"] + counts["inline"]

    issues = []
    for chid, expected in thresholds.items():
        if chid.startswith("_"):  # skip _comment_* keys in config
            continue
        if not isinstance(expected, (int, float)) or expected == 0:
            continue
        found = per_chapter.get(chid, {"total": 0})["total"]
        if found < expected:
            issues.append({
                "type": "historical_notes_distribution",
                "category": "below_threshold_per_chapter",
                "chapter_id": chid,
                "found": found,
                "expected": expected,
                "severity": "warning",
                "suggestion": (
                    f"Добавить \u2265{expected - found} historical_note inline в {chid} (***текст***). "
                    f"Контекст: исторический фон эпохи, социальный контекст."
                ),
                "reason": "Class 9 historical_notes underutilization per chapter",
            })

    total_field = sum(c["field"] for c in per_chapter.values())
    total_inline = sum(c["inline"] for c in per_chapter.values())
    return {
        "per_chapter": per_chapter,
        "thresholds": thresholds,
        "issues": issues,
        "total_field": total_field,
        "total_inline": total_inline,
        "errors_count": sum(1 for i in issues if i["severity"] == "error"),
        "warnings_count": sum(1 for i in issues if i["severity"] == "warning"),
    }


# ─────────────────────────────────────────────────────────────────
# Task 044i: validate_required_episodes_coverage
# ─────────────────────────────────────────────────────────────────

def validate_required_episodes_coverage(
    book: dict,
    pin_list: dict | list,
    config: dict | None = None,
) -> dict:
    """Task 044i: Check that required_in_narrative episodes are present in book.

    pin_list: dict (with 'episodes' and 'bytovye' keys) or list of episode dicts.
    Each episode with required_in_narrative=True must be found in narrative chapters
    via at least one of its markers (regex search).

    Returns {required_episodes, covered_count, missing_count, total_required, issues}.
    Idempotent.
    """
    import re

    if isinstance(pin_list, list):
        episodes = pin_list
    else:
        episodes = (pin_list.get("episodes") or []) + (pin_list.get("bytovye") or [])

    required = [e for e in episodes if e.get("required_in_narrative")]
    if not required:
        return {
            "required_episodes": [], "covered_count": 0, "missing_count": 0,
            "total_required": 0, "issues": [], "errors_count": 0, "warnings_count": 0,
        }

    # Build full text per chapter (non-ch_01)
    book_text = ""
    for ch in book.get("chapters", []):
        if ch.get("id") == "ch_01":
            continue
        book_text += " " + (ch.get("content") or "")
    book_text_lower = book_text.lower()

    result_episodes = []
    issues = []
    covered = 0
    for ep in required:
        ep_id = ep.get("episode_id", "?")
        title = ep.get("title", "?")
        markers = ep.get("markers") or []
        found = False
        found_chapter = None
        mentions = 0
        for ch in book.get("chapters", []):
            if ch.get("id") == "ch_01":
                continue
            ch_content = (ch.get("content") or "").lower()
            for marker in markers:
                try:
                    if re.search(marker, ch_content, re.IGNORECASE):
                        found = True
                        found_chapter = ch.get("id")
                        mentions += len(re.findall(marker, ch_content, re.IGNORECASE))
                        break
                except re.error:
                    if marker.lower() in ch_content:
                        found = True
                        found_chapter = ch.get("id")
                        mentions += ch_content.count(marker.lower())
                        break
            if found:
                break

        ep_result = {
            "episode_id": ep_id,
            "title": title,
            "found": found,
            "mentions": mentions,
            "chapter": found_chapter,
        }
        result_episodes.append(ep_result)
        if found:
            covered += 1
        else:
            issues.append({
                "type": "required_episodes_coverage",
                "category": "missing_required_episode",
                "episode_id": ep_id,
                "title": title,
                "markers": markers,
                "severity": "error",
                "snippet": f"[episode {ep_id} not found in narrative]",
                "suggestion": (
                    f"Episode [{ep_id}] «{title[:50]}» — required_in_narrative, отсутствует. "
                    f"Развернуть в ch_03 или ch_04 на \u22653 sentences. "
                    f"Маркеры: {markers}."
                ),
                "reason": "Required episode missing from narrative",
            })

    return {
        "required_episodes": result_episodes,
        "covered_count": covered,
        "missing_count": len(required) - covered,
        "total_required": len(required),
        "optional_total": len(episodes) - len(required),
        "issues": issues,
        "errors_count": len(issues),
        "warnings_count": 0,
    }
