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
        family.append({"label": label, "value": name, "source": "auto-filled"})

    print(
        f"[BIO-COMPLETENESS] auto-filled {len(missing)} персон в bio_data.family: "
        f"{missing_names}"
    )
    return book_final


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
                       cfg: dict | None = None) -> dict:
    """
    Запускает Fact Extractor.
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

    print(f"\n[FACT EXTRACTOR] Запускаю ({model}, max_tokens={max_tokens})...")
    start = datetime.now()

    user_message = {
        "context": {
            "project_id": project_id,
            "phase": "A",
            "call_type": "initial",
            "iteration": 1,
            "max_iterations": 1,
            "previous_agent": "transcript_cleaner",
            "instruction": "Извлеки все факты из протокола интервью. Построй карту фактов, хронологию, определи пробелы."
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

    # Pin-list: добавляем персон из предыдущего прогона если передан
    if pin_list_fact_map:
        prev_persons = pin_list_fact_map.get("persons", [])
        if prev_persons:
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
            user_message["pin_list"] = {
                "source": "previous_run_fact_map",
                "description": (
                    "Персоны из предыдущего прогона Stage 1. "
                    "Это контрольный список: если персона была в предыдущем прогоне, "
                    "но отсутствует в текущем fact_map — обязательно проверить транскрипт. "
                    "Если найдена → auto_enrich; если нет → log_only_gaps с пометкой 'was_in_pin_list'."
                ),
                "persons": pin_list,
            }
            print(f"[COMPLETENESS AUDITOR] Pin-list: {len(pin_list)} персон из предыдущего прогона")

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
                    force_phase: str | None = None) -> dict:
    """
    Запускает Писателя.
    call_type: "initial" (1-й проход) | "revision" (2-й проход с историком)
    force_phase: если задан ("A" или "B"), переопределяет автоматическое определение phase.
      Используй force_phase="A" для historian_integration (Phase A pass 2 по спеку v2.14):
      модель обогащает черновик, а не точечно патчит главы (Phase B семантика).
      Используй force_phase="B" когда historian-интеграция нужна на уже готовой книге.
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
    legitimate_deletion=true, суммарный размер которых компенсирует потерю.

    Возвращает (passed, details):
      passed: bool — True если объём допустим
      details: dict — chars_before, chars_after, ratio, threshold,
        legitimate_deletions (число помеченных эпизодов),
        unauthorized_drop_chars (сколько символов потеряно сверх легитимного)

    Сценарии:
      A. ratio >= min_ratio → passed=True (нормальный revision)
      B. ratio < min_ratio, legitimate_deletions > 0 → passed=True (FC разрешил)
      C. ratio < min_ratio, нет legitimate_deletion → passed=False (защита сработала)
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
                })

    details = {
        "chars_before": chars_before,
        "chars_after": chars_after,
        "ratio": round(ratio, 4),
        "threshold": min_ratio,
        "drop_chars": max(0, chars_before - chars_after),
        "legitimate_deletions_count": len(legitimate_deletions),
        "legitimate_deletions": legitimate_deletions,
    }

    if ratio >= min_ratio:
        details["verdict"] = "ok_within_threshold"
        return True, details

    if legitimate_deletions:
        details["verdict"] = "ok_with_legitimate_deletion"
        return True, details

    details["verdict"] = "blocked_unauthorized_deletion"
    details["reason"] = (
        f"Объём после revision упал на {details['drop_chars']} символов "
        f"({(1 - ratio) * 100:.1f}%), порог снижения {(1 - min_ratio) * 100:.1f}%. "
        f"FC отчёт не содержит errors с legitimate_deletion=true. "
        f"GW нарушил anti-deletion правило (v2.15)."
    )
    return False, details


# ─────────────────────────────────────────────────────────────────
# Stage 2: Фактчекер
# ─────────────────────────────────────────────────────────────────

def run_fact_checker(client, book_draft: dict, fact_map: dict,
                     transcripts: list[dict], project_id: str,
                     phase: str = "A", iteration: int = 1,
                     max_iterations: int = 3,
                     affected_chapters: list[str] | None = None,
                     cfg: dict | None = None) -> dict:
    """
    Запускает Фактчекера.
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

