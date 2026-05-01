#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stage 4 — Визуальный трек + Вёрстка + QA
Тестовый прогон на данных Каракулиной.

Что делает:
  - Загружает book_final из Корректора + fact_map из Историка
  - Шаг 1: Арт-директор (layout_art_director) — строит page_plan
  - Шаг 2: Верстальщик (layout_designer) — генерирует код PDF
  - Шаг 3: QA вёрстки (qa_layout) — структурная проверка
  - Цикл QA→Верстальщик до 3 итераций при fail

Режим: без фото (text-only book). Photo Editor и Cover Designer
пропускаются, если нет папки с фотографиями проекта.

Использование:
    python scripts/test_stage4_karakulina.py
    # strict mode по умолчанию: только approved checkpoints
    # legacy вручную (только при явном флаге):
    python scripts/test_stage4_karakulina.py --allow-legacy-input --proofreader-report exports/karakulina_proofreader_report_*.json --fact-map exports/test_fact_map_karakulina_v5.json
    python scripts/test_stage4_karakulina.py --photos-dir exports/karakulina_photos/  (если есть фото)
    python scripts/test_stage4_karakulina.py --skip-qa  (не запускать QA-цикл)
"""
import base64
import argparse
import asyncio
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Принудительно UTF-8 для print() в Windows-терминале
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

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

from pipeline_utils import load_config, load_prompt, save_run_manifest, prepare_book_for_layout
from checkpoint_utils import load_checkpoint
from pipeline_quality_gates import pdf_preflight, structural_layout_guard, save_gate_report

MAX_PORTRAIT_ATTEMPTS = 3

# ──────────────────────────────────────────────────────────────────
PROJECT_ID = "karakulina_stage4"
SUBJECT_NAME = "Каракулина Валентина Ивановна"
SUBJECT = {
    "name": SUBJECT_NAME,
    "surname": "Каракулина",
    "first_name": "Валентина",
    "patronymic": "Ивановна",
    "birth_year": 1920,
    "death_year": None,
    "subtitle": "История жизни, рассказанная родными",
}

# Interview architect — переопределяются через apply_subject_profile()
IA_BIRTH_PLACE = "село Мариевка, Кировоградская область"
IA_TRANSCRIPT_SPEAKERS = ["родственники (Никита и Даша, внуки; Татьяна, дочь)"]
IA_TRANSCRIPT_TOPICS = "Детство, война, замужество, переезды, работа медсестрой, пенсия"

MAX_QA_ITERATIONS = 3

DEFAULT_PROOFREADER_REPORT = ROOT / "exports" / "karakulina_proofreader_report_20260329_065332.json"
DEFAULT_FACT_MAP = ROOT / "exports" / "test_fact_map_karakulina_v5.json"  # legacy fallback
DEFAULT_PREFIX = "karakulina"
CHECKPOINT_PROJECT = "karakulina"
CHECKPOINT_STAGE_PROOFREADER = "proofreader"
CHECKPOINT_STAGE_FACT_MAP = "fact_map"
ACCEPTANCE_CHECKPOINTS = {
    "1": "text_approved.json",
    "2a": "layout_text_approved.json",
    "2b": "layout_bio_approved.json",
    "2c": "layout_full_approved.json",
    "3": "photos_approved.json",
    "4": "cover_approved.json",
}
ACCEPTANCE_PREV = {
    "2a": "1",
    "2b": "2a",
    "2c": "2b",
    "3": "2c",
    "4": "3",
}


def _acceptance_dir() -> Path:
    d = ROOT / "checkpoints" / CHECKPOINT_PROJECT
    d.mkdir(parents=True, exist_ok=True)
    return d


def _acceptance_path(gate: str) -> Path:
    return _acceptance_dir() / ACCEPTANCE_CHECKPOINTS[gate]


def ensure_previous_gate_approved(gate: str | None):
    if not gate or gate not in ACCEPTANCE_PREV:
        return
    prev_gate = ACCEPTANCE_PREV[gate]
    prev_path = _acceptance_path(prev_gate)
    if not prev_path.exists():
        raise RuntimeError(
            f"Ворота {gate} нельзя запускать: нет чекпойнта предыдущего этапа {prev_gate} ({prev_path.name})."
        )
    data = json.loads(prev_path.read_text(encoding="utf-8"))
    if not data.get("approved"):
        raise RuntimeError(
            f"Ворота {gate} нельзя запускать: чекпойнт {prev_path.name} не одобрен (approved=false)."
        )


def save_acceptance_checkpoint(gate: str | None, approved: bool, payload: dict):
    if not gate:
        return
    path = _acceptance_path(gate)
    data = {
        "gate": gate,
        "approved": bool(approved),
        "updated_at": datetime.now().isoformat(),
        **payload,
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    state = "APPROVED" if approved else "PENDING"
    print(f"[CHECKPOINT] {path.name}: {state}")


def apply_subject_profile(path: Path) -> None:
    """Подставляет героя/проект для Stage4 (обложка, арт-директор, интервьюер)."""
    global PROJECT_ID, SUBJECT_NAME, SUBJECT, IA_BIRTH_PLACE, IA_TRANSCRIPT_SPEAKERS, IA_TRANSCRIPT_TOPICS
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("project_id"):
        PROJECT_ID = data["project_id"]
    if data.get("subject_name"):
        SUBJECT_NAME = data["subject_name"]
    if data.get("subject"):
        merged = {**SUBJECT, **data["subject"]}
        SUBJECT = merged
    ia = data.get("interview_architect") or {}
    if ia.get("birth_place"):
        IA_BIRTH_PLACE = ia["birth_place"]
    if ia.get("transcript_speakers"):
        IA_TRANSCRIPT_SPEAKERS = ia["transcript_speakers"]
    if ia.get("transcript_topics"):
        IA_TRANSCRIPT_TOPICS = ia["transcript_topics"]
    print(f"[CONFIG] subject profile: {path.name} | project_id={PROJECT_ID} | hero={SUBJECT_NAME}")


# ──────────────────────────────────────────────────────────────────
# Загрузка входных данных
# ──────────────────────────────────────────────────────────────────

def load_book_final(report_path: Path) -> tuple[dict, dict]:
    """Загружает book_final и style_passport из отчёта Корректора."""
    with open(report_path, encoding="utf-8") as f:
        data = json.load(f)

    # Структура: { chapters, callouts, historical_notes, style_passport, ... }
    # или { book_final: { chapters, ... }, style_passport: ... }
    if "book_final" in data:
        book = data["book_final"]
    else:
        book = data

    book_final = {
        "chapters": book.get("chapters", []),
        "callouts": book.get("callouts", []),
        "historical_notes": book.get("historical_notes", []),
    }
    style_passport = data.get("style_passport", book.get("style_passport", {}))
    return book_final, style_passport


def load_fact_map(historian_path: Path) -> dict:
    """Загружает fact_map из файла Историка/Фактолога."""
    with open(historian_path, encoding="utf-8") as f:
        data = json.load(f)
    # Может быть { fact_map: {...} } или напрямую { persons, timeline, ... }
    if "fact_map" in data:
        return data["fact_map"]
    return data


def _extract_year(value) -> int | None:
    if isinstance(value, int):
        return value if 1000 <= value <= 2100 else None
    if isinstance(value, str):
        import re
        m = re.search(r"(19|20)\d{2}", value)
        if m:
            return int(m.group(0))
    return None


def sync_subject_years_from_fact_map(fact_map: dict, allow_clear_death: bool = True) -> None:
    """Синхронизирует birth/death годы героя из fact_map, чтобы обложка не жила на хардкоде."""
    global SUBJECT
    subj = fact_map.get("subject", {}) if isinstance(fact_map, dict) else {}
    if not isinstance(subj, dict):
        return

    birth_year = _extract_year(subj.get("birth_year")) or _extract_year(subj.get("birth_date"))
    death_year = _extract_year(subj.get("death_year")) or _extract_year(subj.get("death_date"))

    if birth_year:
        SUBJECT["birth_year"] = birth_year
    if death_year:
        SUBJECT["death_year"] = death_year
    elif allow_clear_death:
        SUBJECT["death_year"] = None


def resolve_inputs(args, ts: str) -> tuple[Path, Path, dict]:
    """Определяет входы Stage4.

    По умолчанию (строгий режим) разрешены только approved checkpoints.
    Legacy-файлы из exports разрешены только с --allow-legacy-input.
    """
    exports_dir = ROOT / "exports"
    exports_dir.mkdir(exist_ok=True)

    if args.allow_legacy_input:
        proof_path = Path(args.proofreader_report) if args.proofreader_report else DEFAULT_PROOFREADER_REPORT
        fact_path = Path(args.fact_map) if args.fact_map else DEFAULT_FACT_MAP
        if not proof_path.exists():
            raise FileNotFoundError(f"Legacy proofreader report не найден: {proof_path}")
        if not fact_path.exists():
            raise FileNotFoundError(f"Legacy fact_map не найден: {fact_path}")
        print("[INPUT] ⚠️ Legacy режим включён (--allow-legacy-input)")
        print(f"[INPUT] proofreader-report: {proof_path}")
        print(f"[INPUT] fact-map: {fact_path}")
        return proof_path, fact_path, {
            "mode": "legacy",
            "checkpoints": {},
            "sources": {"proofreader": str(proof_path), "fact_map": str(fact_path)},
        }

    # STRICT MODE: только approved checkpoints
    if args.proofreader_report or args.fact_map:
        raise RuntimeError(
            "Ручные входы (--proofreader-report/--fact-map) запрещены в strict режиме.\n"
            "Либо убери их и используй approved checkpoints,\n"
            "либо явно добавь --allow-legacy-input."
        )

    cp_proof = load_checkpoint(
        CHECKPOINT_PROJECT, CHECKPOINT_STAGE_PROOFREADER, require_approved=True
    )
    cp_fact = None
    fact_raw = None
    try:
        cp_fact = load_checkpoint(
            CHECKPOINT_PROJECT, CHECKPOINT_STAGE_FACT_MAP, require_approved=True
        )
        fact_raw = cp_fact.get("content", {})
    except Exception:
        if DEFAULT_FACT_MAP.exists():
            # Временный мост: пока fact_map checkpoint не заведён, используем legacy файл.
            print(
                f"[INPUT] ⚠️ approved checkpoint '{CHECKPOINT_STAGE_FACT_MAP}' не найден; "
                f"использую fallback: {DEFAULT_FACT_MAP}"
            )
            fact_raw = json.loads(DEFAULT_FACT_MAP.read_text(encoding="utf-8"))
        else:
            raise RuntimeError(
                f"Нет approved checkpoint '{CHECKPOINT_STAGE_FACT_MAP}' и fallback-файла {DEFAULT_FACT_MAP}.\n"
                "Создайте/одобрите fact_map чекпоинт или запустите с --allow-legacy-input --fact-map <path>."
            )

    proof_raw = cp_proof.get("content", {})
    proof_path = exports_dir / f"{args.prefix}_input_proofreader_checkpoint_{ts}.json"
    fact_path = exports_dir / f"{args.prefix}_input_fact_map_checkpoint_{ts}.json"
    proof_path.write_text(json.dumps(proof_raw, ensure_ascii=False, indent=2), encoding="utf-8")
    fact_path.write_text(json.dumps(fact_raw, ensure_ascii=False, indent=2), encoding="utf-8")

    print("[INPUT] ✅ Strict checkpoint режим")
    print(
        f"[INPUT] proofreader checkpoint: v{cp_proof.get('version')} "
        f"(approved_at={cp_proof.get('approved_at')}, source={cp_proof.get('source_file')})"
    )
    if cp_fact:
        print(
            f"[INPUT] fact_map checkpoint: v{cp_fact.get('version')} "
            f"(approved_at={cp_fact.get('approved_at')}, source={cp_fact.get('source_file')})"
        )
    print(f"[INPUT] materialized proofreader: {proof_path.name}")
    print(f"[INPUT] materialized fact_map: {fact_path.name}")

    checkpoints = {
        "proofreader": {
            "project": CHECKPOINT_PROJECT,
            "stage": CHECKPOINT_STAGE_PROOFREADER,
            "version": cp_proof.get("version"),
            "approved_at": cp_proof.get("approved_at"),
            "source_file": cp_proof.get("source_file"),
        }
    }
    if cp_fact:
        checkpoints["fact_map"] = {
            "project": CHECKPOINT_PROJECT,
            "stage": CHECKPOINT_STAGE_FACT_MAP,
            "version": cp_fact.get("version"),
            "approved_at": cp_fact.get("approved_at"),
            "source_file": cp_fact.get("source_file"),
        }

    return proof_path, fact_path, {
        "mode": "strict_checkpoint",
        "checkpoints": checkpoints,
        "sources": {"proofreader": str(proof_path), "fact_map": str(fact_path)},
    }


def count_chars(book: dict) -> int:
    return sum(len(ch.get("content") or "") for ch in book.get("chapters", []))


def build_chapters_summary(book: dict) -> list[dict]:
    """Строит краткое содержание глав для Интервьюера (первые ~400 символов контента)."""
    summaries = []
    for ch in book.get("chapters", []):
        content = ch.get("content") or ""
        brief = content[:400].strip()
        if len(content) > 400:
            brief += "..."
        summaries.append({
            "id": ch.get("id", ""),
            "title": ch.get("title", ""),
            "covers_period": ch.get("covers_period", ""),
            "brief_content": brief,
        })
    return summaries


def build_expected_content(book: dict, photos: list | None = None) -> dict:
    """Строит expected_content для QA вёрстки."""
    chapters = book.get("chapters", [])
    callouts = book.get("callouts", [])
    historical_notes = book.get("historical_notes", [])
    photo_list = photos or []
    return {
        "total_chapters": len(chapters),
        "chapter_titles": [ch.get("title", "") for ch in chapters],
        "total_photos": len(photo_list),
        "photo_ids": [p.get("id", "") for p in photo_list],
        "total_callouts": len(callouts),
        "callout_ids": [c.get("id", "") for c in callouts],
        "historical_notes_count": len(historical_notes),
    }


def image_bytes_to_base64(data: bytes) -> str:
    """Конвертирует байты изображения в base64-строку для передачи в LLM."""
    return base64.b64encode(data).decode("utf-8")


def _shrink_image_for_llm(data: bytes, max_px: int = 768, quality: int = 80) -> bytes:
    """Сжимает изображение до max_px по длинной стороне и возвращает JPEG-байты.

    Уменьшает размер base64-payload чтобы не превышать лимит токенов Claude.
    """
    try:
        from PIL import Image as PILImage
        import io
        with PILImage.open(io.BytesIO(data)) as img:
            img = img.convert("RGB")
            w, h = img.size
            if max(w, h) > max_px:
                scale = max_px / max(w, h)
                img = img.resize((int(w * scale), int(h * scale)), PILImage.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=quality, optimize=True)
            return buf.getvalue()
    except Exception as e:
        logger.warning("_shrink_image_for_llm: ошибка сжатия (%s), используем оригинал", e)
        return data


# ──────────────────────────────────────────────────────────────────
# JSON parse helper
# ──────────────────────────────────────────────────────────────────

def _strip_json_comments(text: str) -> str:
    """Удаляет // однострочные и /* блочные */ комментарии из JSON-подобного текста."""
    import re
    # Блочные комментарии /* ... */
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    # Однострочные // комментарии (только вне строк — упрощённая версия)
    lines = []
    for line in text.split('\n'):
        # Ищем // вне кавычек
        in_str = False
        escape = False
        for i, ch in enumerate(line):
            if escape:
                escape = False
                continue
            if ch == '\\':
                escape = True
                continue
            if ch == '"':
                in_str = not in_str
            if ch == '/' and not in_str and i + 1 < len(line) and line[i+1] == '/':
                line = line[:i].rstrip()
                break
        lines.append(line)
    return '\n'.join(lines)


def parse_json_response(raw: str, agent_name: str) -> dict:
    """Парсит JSON из ответа LLM, обрабатывает markdown-обёртки и комментарии."""
    text = raw.strip()
    # Убираем ```json ... ``` или ``` ... ```
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:])
        if text.endswith("```"):
            text = text[:-3].strip()
    s, e = text.find("{"), text.rfind("}")
    if s != -1 and e > s:
        candidate = text[s:e + 1]
        # Сначала пробуем как есть
        try:
            return json.loads(candidate)
        except json.JSONDecodeError as exc:
            print(f"[{agent_name}] ❌ JSON parse error (raw): {exc}")
        # Пробуем после удаления комментариев
        try:
            cleaned = _strip_json_comments(candidate)
            return json.loads(cleaned)
        except json.JSONDecodeError as exc2:
            print(f"[{agent_name}] ❌ JSON parse error (after comment strip): {exc2}")
            # Сохраняем сырой ответ для диагностики
            import time as _time
            debug_path = ROOT / "exports" / f"{agent_name.lower().replace(' ', '_')}_debug_{int(_time.time())}.txt"
            debug_path.parent.mkdir(exist_ok=True)
            debug_path.write_text(candidate[:3000], encoding="utf-8")
            print(f"[{agent_name}] Первые 3000 символов ответа сохранены: {debug_path.name}")
    raise ValueError(f"[{agent_name}] Не удалось распарсить JSON из ответа")


# ──────────────────────────────────────────────────────────────────
# Общий вызов агента
# ──────────────────────────────────────────────────────────────────

async def call_agent(
    client,
    agent_name: str,
    cfg_key: str,
    system_prompt: str,
    user_message: dict,
    cfg: dict,
) -> tuple[dict, int, int]:
    """
    Вызывает LLM-агента. Возвращает (parsed_dict, input_tokens, output_tokens).
    """
    agent_cfg = cfg[cfg_key]
    model = agent_cfg["model"]
    max_tokens = agent_cfg["max_tokens"]
    temperature = agent_cfg.get("temperature", 0.3)

    print(f"\n[{agent_name}] Запускаю ({model}, max_tokens={max_tokens}, temp={temperature})...")
    start = datetime.now()

    loop = asyncio.get_event_loop()

    def _call():
        raw_parts = []
        with client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{
                "role": "user",
                "content": json.dumps(user_message, ensure_ascii=False),
            }],
        ) as stream:
            for text in stream.text_stream:
                raw_parts.append(text)
            final = stream.get_final_message()
        return "".join(raw_parts), final.usage.input_tokens, final.usage.output_tokens

    import time as _time
    for _attempt in range(4):
        try:
            raw, in_tok, out_tok = await loop.run_in_executor(None, _call)
            break
        except anthropic.RateLimitError as e:
            wait_s = 65 * (_attempt + 1)
            print(f"[{agent_name}] Rate limit (429) — жду {wait_s}с и повторяю (попытка {_attempt+1}/4)...")
            await asyncio.sleep(wait_s)
    else:
        raise RuntimeError(f"[{agent_name}] Rate limit не снялся после 4 попыток")
    elapsed = (datetime.now() - start).total_seconds()
    print(f"[{agent_name}] Готово за {elapsed:.1f}с | {len(raw)} симв. | токены: in={in_tok}, out={out_tok}")

    if out_tok >= max_tokens - 200:
        print(f"[{agent_name}] ⚠️  output_tokens ≈ max_tokens — возможно обрезание!")

    result = parse_json_response(raw, agent_name)
    return result, in_tok, out_tok


# ──────────────────────────────────────────────────────────────────
# Валидация page_plan
# ──────────────────────────────────────────────────────────────────

def validate_page_plan(response: dict) -> dict | None:
    """Проверяет наличие page_plan с хотя бы одной cover-страницей."""
    if not isinstance(response, dict):
        return None
    plan = response.get("page_plan")
    if not plan or not isinstance(plan, list):
        print("[VALIDATE-ART] ❌ page_plan отсутствует или не список")
        return None
    if not any(p.get("page_type") == "cover" or p.get("type") == "cover" or p.get("content") == "cover_composition"
               for p in plan):
        print("[VALIDATE-ART] ⚠️  cover-страница не найдена в page_plan")
    print(f"[VALIDATE-ART] ✅ page_plan: {len(plan)} страниц")
    return response


def validate_layout_output(response: dict) -> dict | None:
    """Проверяет наличие layout_code или pages[] в ответе верстальщика.

    Поддерживает два формата:
      1. layout_code.code (Python/HTML код — старый формат v1/v2)
      2. pages[] (JSON-схема страниц — формат v3+)
    """
    if not isinstance(response, dict):
        return None

    # Формат 1: layout_code.code
    layout_code = response.get("layout_code", {})
    if layout_code and isinstance(layout_code, dict) and layout_code.get("code"):
        page_map = response.get("page_map", [])
        total_pages = response.get("technical_notes", {}).get("total_pages", 0)
        print(f"[VALIDATE-LAYOUT] ✅ layout_code (code): {len(layout_code.get('code', ''))} симв. | "
              f"page_map: {len(page_map)} стр. | total_pages: {total_pages}")
        response["_layout_format"] = "code"
        return response

    # Формат 2: pages[] (JSON-схема, Layout Designer v3+)
    pages = response.get("pages")
    if not pages:
        # Также проверяем layout_instructions.pages
        pages = response.get("layout_instructions", {}).get("pages")
    if pages and isinstance(pages, list) and len(pages) > 0:
        page_map = response.get("page_map", [])
        total_pages = response.get("technical_notes", {}).get("total_pages", len(pages))
        print(f"[VALIDATE-LAYOUT] ✅ pages[] (JSON-схема): {len(pages)} стр. | "
              f"page_map: {len(page_map)} | total_pages: {total_pages}")
        response["_layout_format"] = "pages_json"
        return response

    print("[VALIDATE-LAYOUT] ❌ Ни layout_code.code, ни pages[] не найдены")
    return None


def validate_qa_output(response: dict) -> dict | None:
    """Проверяет структуру QA-отчёта. Форсирует fail при fonts_embedded=false."""
    if not isinstance(response, dict):
        return None
    verdict = response.get("verdict")
    if verdict not in ("pass", "fail"):
        print(f"[VALIDATE-QA] ❌ Неизвестный verdict: {verdict!r}")
        return None
    # Принудительный fail если шрифты не embedded
    summary = response.get("summary", {})
    if not summary.get("fonts_embedded", True):
        response["verdict"] = "fail"
        issues = response.setdefault("issues", [])
        if not any(i.get("type") == "font_not_embedded" for i in issues):
            issues.append({
                "id": "auto_font_check",
                "severity": "critical",
                "type": "font_not_embedded",
                "description": "Шрифты не embedded в PDF",
                "fix_suggestion": "Убедиться что все шрифты embedded. Использовать локальные .ttf.",
            })
    issues = response.get("issues", [])
    critical = sum(1 for i in issues if i.get("severity") == "critical")
    major = sum(1 for i in issues if i.get("severity") == "major")
    minor = sum(1 for i in issues if i.get("severity") == "minor")
    print(f"[VALIDATE-QA] verdict={verdict} | critical={critical} major={major} minor={minor}")
    return response


# ──────────────────────────────────────────────────────────────────
# Шаг 0а: Cover Designer — Вызов 1 (арт-дирекция)
# ──────────────────────────────────────────────────────────────────

async def run_cover_designer_call1(client, photos: list, cfg: dict) -> dict:
    """
    Cover Designer первый вызов: выбирает фото, составляет промпт для Replicate,
    делает предварительный дизайн обложки.
    При пустом списке фото — составляет промпт на основе метаданных героя.
    """
    system_prompt = load_prompt(cfg["cover_designer"]["prompt_file"])

    user_message = {
        "context": {
            "call_type": "initial",
            "instruction": (
                "Выбери главное фото, составь промпт для генерации ink sketch портрета, "
                "сделай предварительный дизайн обложки. "
                "Если фотографий нет — составь промпт на основе метаданных героя."
            ),
        },
        "data": {
            "project_id": PROJECT_ID,
            "subject": SUBJECT,
            "photos": photos,
        }
    }

    result, in_tok, out_tok = await call_agent(
        client, "COVER_DESIGNER_1", "cover_designer", system_prompt, user_message, cfg
    )
    return result


async def run_cover_designer_call2(
    client,
    previous_cover_composition: dict,
    generated_portrait_base64: str,
    iteration: int,
    cfg: dict,
) -> dict:
    """
    Cover Designer второй вызов: валидирует сгенерированный портрет,
    финализирует композицию обложки.
    """
    system_prompt = load_prompt(cfg["cover_designer"]["prompt_file"])

    user_message = {
        "context": {
            "call_type": "validation",
            "iteration": iteration,
            "max_iterations": MAX_PORTRAIT_ATTEMPTS,
            "instruction": (
                "Оцени сгенерированный портрет. "
                "Если подходит — финализируй композицию. Если нет — дай уточнённый промпт."
            ),
        },
        "data": {
            "project_id": PROJECT_ID,
            "original_photo": None,
            "generated_portrait": generated_portrait_base64,
            "previous_cover_composition": previous_cover_composition,
            "subject": SUBJECT,
        }
    }

    result, in_tok, out_tok = await call_agent(
        client, "COVER_DESIGNER_2", "cover_designer", system_prompt, user_message, cfg
    )
    return result


def run_replicate_ink_sketch(
    image_gen_prompt: str,
    reference_image_bytes: bytes | None = None,
) -> bytes | None:
    """Вызывает Replicate для генерации ink sketch портрета.

    Если передан reference_image_bytes — использует google/nano-banana-2
    с реальным фото референса. Иначе fallback на FLUX Schnell text-to-image.
    """
    try:
        from replicate_client import generate_ink_sketch_portrait
        return generate_ink_sketch_portrait(
            image_gen_prompt,
            reference_image_bytes=reference_image_bytes,
            aspect_ratio="3:4",
        )
    except Exception as e:
        print(f"[REPLICATE] ❌ Ошибка: {e}")
        return None


# ──────────────────────────────────────────────────────────────────
# Шаг 1: Арт-директор
# ──────────────────────────────────────────────────────────────────

async def run_art_director(client, book_final: dict, photos: list, cover_composition: dict | None, cfg: dict) -> dict:
    """
    Арт-директор строит page_plan — постраничный план макета.
    Vision=True по конфигу, но в этом тесте фото передаются как метаданные (base64 не используется).
    """
    system_prompt = load_prompt(cfg["layout_art_director"]["prompt_file"])

    user_message = {
        "context": {
            "project_id": PROJECT_ID,
            "phase": "A",
            "call_type": "initial",
            "iteration": 1,
            "max_iterations": 1,
            "previous_agent": "proofreader + photo_editor + cover_designer",
            "instruction": (
                "Спланируй раскладку каждой страницы книги. "
                "Посмотри на каждое фото (vision). "
                "Определи каким приёмом и на какой странице размещать. "
                "Выдай page_plan. "
                "КРИТИЧНО: каждый callout обязан быть явно прописан в page_plan.elements "
                "(type='callout' + id/callout_id). page_plan — source of truth."
            ),
        },
        "data": {
            "text": book_final,
            "photos": photos,
            "cover_composition": cover_composition,
            "subject_name": SUBJECT_NAME,
        }
    }

    result, in_tok, out_tok = await call_agent(
        client, "ART_DIRECTOR", "layout_art_director", system_prompt, user_message, cfg
    )
    return result


# ──────────────────────────────────────────────────────────────────
# Шаг 2: Верстальщик
# ──────────────────────────────────────────────────────────────────

async def run_layout_designer(
    client,
    book_final: dict,
    photos: list,
    page_plan: dict,
    cover_portrait: str | None,
    cover_composition: dict | None,
    style_passport: dict,
    qa_report: dict | None,
    iteration: int,
    cfg: dict,
    book_json_path: str | None = None,
    photos_dir_path: str | None = None,
    pdf_output_path: str | None = None,
) -> dict:
    """Верстальщик генерирует код PDF по page_plan."""
    system_prompt = load_prompt(cfg["layout_designer"]["prompt_file"])

    is_revision = iteration > 1 and qa_report is not None
    user_message = {
        "context": {
            "project_id": PROJECT_ID,
            "phase": "A",
            "call_type": "initial" if not is_revision else "revision",
            "iteration": iteration,
            "max_iterations": MAX_QA_ITERATIONS,
            "previous_agent": "layout_art_director" if not is_revision else "layout_qa",
            "instruction": (
                "Реализуй page_plan в коде. Создай PDF-макет. "
                "Не меняй раскладку — следуй плану строго. "
                "page_plan=контракт, page_map=отчёт исполнения: 1:1 без расхождений. "
                "Callout-ы бери только из page_plan.elements и размещай строго по страницам page_plan; "
                "допуск ±1 только с явным обоснованием в technical_notes. "
                "Сохраняй callout IDs без потерь: set(page_map.callouts) == set(expected_content.callout_ids). "
                "Жёсткая таблица типов: "
                "cover->cover, blank->blank, toc->toc, chapter_start->chapter_start, "
                "text_only/text_with_photo/text_with_photos/text_with_callout/bio_timeline->chapter_body, "
                "photo_section/photo_section_start/full_page_photo->photo_page, final_page->final_page. "
                "Единая пагинация: cover/blank без видимого номера, TOC (physical 3) = visible 1, далее visible=physical-2. "
                "Шрифты ОБЯЗАТЕЛЬНО embedded в PDF. "
                "Используй Python ReportLab (предпочтительно) или HTML/CSS + WeasyPrint. "
                "Все шрифты должны быть embedded — использовать локальные .ttf файлы или reportlab pdfmetrics. "
                "ВАЖНО: читай текст и фото из файлов через BOOK_JSON_PATH и PHOTOS_DIR, не хардкодь текст."
            ) if not is_revision else (
                "QA обнаружил проблемы. Исправь указанные issues и пересобери PDF. "
                "Стиль и содержание не менять. "
                "Соблюди контракт page_plan↔page_map (1:1), callout pages/IDs и модель пагинации/TOC."
            ),
        },
        "data": {
            "text": book_final,
            "photos": photos,
            "page_plan": page_plan.get("page_plan", []),
            "cover_portrait": cover_portrait,
            "cover_composition": cover_composition,
            "subject_name": SUBJECT_NAME,
            "style_passport": style_passport,
            **({"book_json_path": book_json_path} if book_json_path else {}),
            **({"photos_dir": photos_dir_path} if photos_dir_path else {}),
            **({"pdf_output_path": pdf_output_path} if pdf_output_path else {}),
            **({"qa_report": qa_report} if qa_report else {}),
        }
    }

    result, in_tok, out_tok = await call_agent(
        client, "LAYOUT_DESIGNER", "layout_designer", system_prompt, user_message, cfg
    )
    return result


# ──────────────────────────────────────────────────────────────────
# Шаг 4: Интервьюер
# ──────────────────────────────────────────────────────────────────

async def run_interview_architect(
    client,
    fact_map: dict,
    book_final: dict,
    cfg: dict,
) -> dict:
    """
    Интервьюер составляет 12–18 стратегических уточняющих вопросов
    на основе gaps карты фактов и summary глав.
    """
    system_prompt = load_prompt(cfg["interview_architect"]["prompt_file"])

    chapters_summary = build_chapters_summary(book_final)
    gaps = fact_map.get("gaps", [])
    persons = fact_map.get("persons", [])
    timeline = fact_map.get("timeline", [])
    locations = fact_map.get("locations", [])
    conflicts = fact_map.get("conflicts", [])

    blitz_questions = cfg.get("blitz_questions", [])

    user_message = {
        "project_id": PROJECT_ID,
        "subject": {
            "name": SUBJECT_NAME,
            "birth_year": SUBJECT.get("birth_year"),
            "death_year": SUBJECT.get("death_year"),
            "birth_place": IA_BIRTH_PLACE,
        },
        "gaps": gaps,
        "timeline": timeline,
        "persons": persons,
        "locations": locations,
        "conflicts": conflicts,
        "book_chapters_summary": chapters_summary,
        "transcripts_summary": {
            "count": 1,
            "speakers": IA_TRANSCRIPT_SPEAKERS,
            "total_topics_covered": IA_TRANSCRIPT_TOPICS,
        },
        "blitz_questions": blitz_questions,
    }

    result, in_tok, out_tok = await call_agent(
        client, "INTERVIEW_ARCHITECT", "interview_architect", system_prompt, user_message, cfg
    )
    return result


def validate_interview_questions(response: dict) -> dict | None:
    """Проверяет структуру ответа Интервьюера."""
    if not isinstance(response, dict):
        return None
    questions = response.get("questions", [])
    if not questions:
        print("[VALIDATE-IA] ❌ Нет вопросов в ответе")
        return None
    total = response.get("summary", {}).get("total_questions", len(questions))
    if total < 8:
        print(f"[VALIDATE-IA] ⚠️  Мало вопросов: {total} (ожидается 12–18)")
    groups = response.get("question_groups", [])
    print(f"[VALIDATE-IA] ✅ Вопросов: {total} | Групп: {len(groups)}")
    return response


# ──────────────────────────────────────────────────────────────────
# Шаг 3: QA вёрстки
# ──────────────────────────────────────────────────────────────────

async def run_layout_qa(
    client,
    layout_result: dict,
    page_plan: dict,
    expected_content: dict,
    iteration: int,
    previous_qa_issues: list,
    cfg: dict,
    qa_mode: str = "structural_qa",
    pdf_path: str | None = None,
) -> dict:
    """QA вёрстки — структурная проверка page_map и style_guide."""
    system_prompt = load_prompt(cfg["qa_layout"]["prompt_file"])

    has_pdf = pdf_path is not None and Path(pdf_path).exists()
    user_message = {
        "context": {
            "project_id": PROJECT_ID,
            "phase": "A",
            "call_type": "initial",
            "iteration": iteration,
            "max_iterations": MAX_QA_ITERATIONS,
            "previous_agent": "layout_designer",
            "instruction": (
                ("Режим structural_qa: проверяй структуру page_plan/page_map/style_guide, без визуальных допущений. "
                 if qa_mode == "structural_qa" else
                 "Режим visual_qa: проверяй визуальное качество PDF, шрифты, читабельность, фото и композицию. ")
                + "Критично: page_plan=контракт, page_map=отчёт исполнения 1:1; callout-ы на страницах page_plan (±1 только с обоснованием). "
                + "Callout IDs обязаны совпадать с expected_content.callout_ids, без потерь. "
                + "Единая пагинация: cover/blank без номера, TOC physical=3 отображает visible=1, TOC использует visible номера. "
                + "ПЕРВАЯ проверка: текст читается (шрифты embedded, нет ■■■). "
                + "Затем: page_plan соблюдён, фото не обрезаны, нумерация, оглавление, поля. "
                + (
                    "PDF передаётся как путь к файлу — используй его для визуальной проверки."
                    if has_pdf else
                    "Примечание: PDF не передаётся (режим структурной проверки). "
                    "Проверяй по page_map, style_guide и expected_content."
                )
            ),
        },
        "data": {
            "pdf_file": pdf_path if has_pdf else None,
            "pdf_available": has_pdf,
            "qa_mode": qa_mode,
            "page_map": layout_result.get("page_map", []),
            "page_plan": page_plan.get("page_plan", []),
            "style_guide": layout_result.get("style_guide", {}),
            "expected_content": expected_content,
            "layout_code_format": layout_result.get("layout_code", {}).get("format", ""),
            "technical_notes": layout_result.get("technical_notes", {}),
            **({"previous_qa_issues": previous_qa_issues} if previous_qa_issues else {}),
        }
    }

    result, in_tok, out_tok = await call_agent(
        client, "LAYOUT_QA", "qa_layout", system_prompt, user_message, cfg
    )
    return result


def combine_qa_reports(structural_qa: dict | None, visual_qa: dict | None) -> dict:
    return combine_qa_reports_with_mode(
        structural_qa=structural_qa,
        visual_qa=visual_qa,
        visual_non_blocking=True,
    )


def _normalize_callout_id(value: str | None) -> str:
    return (value or "").strip().lower()


def _collect_callout_ids_from_page_plan(page_plan: dict) -> set[str]:
    out: set[str] = set()
    pages = page_plan.get("page_plan", []) if isinstance(page_plan, dict) else []
    for p in pages if isinstance(pages, list) else []:
        elems = p.get("elements", []) if isinstance(p, dict) else []
        for e in elems if isinstance(elems, list) else []:
            if not isinstance(e, dict):
                continue
            if (e.get("type") or "").strip().lower() != "callout":
                continue
            cid = _normalize_callout_id(e.get("id") or e.get("callout_id"))
            if cid:
                out.add(cid)
    return out


def _collect_callout_ids_from_page_map(layout_result: dict) -> set[str]:
    out: set[str] = set()
    page_map = layout_result.get("page_map", []) if isinstance(layout_result, dict) else []
    for p in page_map if isinstance(page_map, list) else []:
        elems = p.get("elements", []) if isinstance(p, dict) else []
        for e in elems if isinstance(elems, list) else []:
            if isinstance(e, str):
                s = _normalize_callout_id(e)
                if s.startswith("callout_"):
                    out.add(s)
                continue
            if not isinstance(e, dict):
                continue
            if (e.get("type") or "").strip().lower() != "callout":
                continue
            cid = _normalize_callout_id(e.get("id") or e.get("callout_id"))
            if cid:
                out.add(cid)
    return out


def run_callout_precheck(expected_content: dict, page_plan: dict, layout_result: dict) -> dict:
    expected_raw = expected_content.get("callout_ids", []) if isinstance(expected_content, dict) else []
    expected_ids = {_normalize_callout_id(x) for x in (expected_raw if isinstance(expected_raw, list) else []) if _normalize_callout_id(x)}
    plan_ids = _collect_callout_ids_from_page_plan(page_plan)
    map_ids = _collect_callout_ids_from_page_map(layout_result)

    missing_in_plan = sorted(expected_ids - plan_ids)
    missing_in_map = sorted(expected_ids - map_ids)
    extra_in_map = sorted(map_ids - expected_ids)

    checks = {
        "expected_ids_resolved": len(expected_ids) > 0,
        "page_plan_has_all_expected_callouts": len(missing_in_plan) == 0,
        "page_map_has_all_expected_callouts": len(missing_in_map) == 0,
        "page_map_has_no_unexpected_callouts": len(extra_in_map) == 0,
    }
    passed = all(checks.values())
    return {
        "gate": "callout_id_precheck",
        "passed": passed,
        "checks": checks,
        "expected_callout_ids": sorted(expected_ids),
        "page_plan_callout_ids": sorted(plan_ids),
        "page_map_callout_ids": sorted(map_ids),
        "missing_in_page_plan": missing_in_plan,
        "missing_in_page_map": missing_in_map,
        "extra_in_page_map": extra_in_map,
    }


def combine_qa_reports_with_mode(
    structural_qa: dict | None,
    visual_qa: dict | None,
    visual_non_blocking: bool,
) -> dict:
    structural_qa = structural_qa or {"verdict": "fail", "issues": [{"severity": "critical", "description": "structural_qa missing"}], "summary": {}}
    visual_qa = visual_qa or {"verdict": "pass", "issues": [], "summary": {}}
    structural_issues = list(structural_qa.get("issues", []))
    visual_issues = list(visual_qa.get("issues", []))

    if visual_non_blocking:
        normalized_visual = []
        for issue in visual_issues:
            if not isinstance(issue, dict):
                continue
            vis = dict(issue)
            vis["severity"] = "minor"
            vis["non_blocking"] = True
            vis["source"] = "visual_qa"
            normalized_visual.append(vis)
        issues = structural_issues + normalized_visual
        verdict = "pass" if structural_qa.get("verdict") == "pass" else "fail"
    else:
        issues = structural_issues + visual_issues
        verdict = "pass" if structural_qa.get("verdict") == "pass" and visual_qa.get("verdict") == "pass" else "fail"

    critical = sum(1 for i in issues if (i or {}).get("severity") == "critical")
    major = sum(1 for i in issues if (i or {}).get("severity") == "major")
    minor = sum(1 for i in issues if (i or {}).get("severity") == "minor")
    return {
        "verdict": verdict,
        "issues": issues,
        "summary": {
            "critical_issues": critical,
            "major_issues": major,
            "minor_issues": minor,
            "total_pages_checked": max(
                structural_qa.get("summary", {}).get("total_pages_checked", 0),
                visual_qa.get("summary", {}).get("total_pages_checked", 0),
            ),
            "overall_assessment": (
                "Combined structural_qa + visual_qa (visual non-blocking)"
                if visual_non_blocking else
                "Combined structural_qa + visual_qa"
            ),
            "fonts_embedded": structural_qa.get("summary", {}).get("fonts_embedded", True)
                              and visual_qa.get("summary", {}).get("fonts_embedded", True),
        },
        "qa_modes": {
            "structural_qa": structural_qa,
            "visual_qa": visual_qa,
        },
        "verdict_policy": {
            "visual_non_blocking": visual_non_blocking,
            "effective_blocking_source": "structural_qa" if visual_non_blocking else "structural_qa+visual_qa",
        },
    }


# ──────────────────────────────────────────────────────────────────
# Вывод результатов
# ──────────────────────────────────────────────────────────────────

def print_cover_designer_results(call_num: int, result: dict, portrait_bytes: bytes | None = None):
    print("\n" + "=" * 60)
    print(f"РЕЗУЛЬТАТ: COVER DESIGNER (Роль 13) — Вызов {call_num}")
    print("=" * 60)
    if call_num == 1:
        selected = result.get("selected_photo", {})
        pg = result.get("portrait_generation", {})
        comp = result.get("cover_composition", {})
        print(f"\n  Выбрано фото: {selected.get('photo_id', 'нет')} — {selected.get('reason', '')[:100]}")
        if pg:
            prompt = pg.get("image_gen_prompt", "")
            print(f"  Prompt для Replicate: {prompt[:150]}...")
            pp = pg.get("post_processing", {})
            print(f"  Post-processing: tint={pp.get('tint_color')}, opacity={pp.get('target_opacity')}")
        if comp:
            print(f"  Фон обложки: {comp.get('background_color')}")
            typo = comp.get("typography", {})
            if typo:
                surname = typo.get("surname", {})
                print(f"  Фамилия: '{surname.get('text', '')}' {surname.get('font', '')} {surname.get('size_pt', '')}pt")
        if portrait_bytes:
            print(f"\n  Replicate → портрет: {len(portrait_bytes)} байт ✅")
        else:
            print("\n  Replicate → портрет: не сгенерирован (нет токена или ошибка)")
    else:
        verdict = result.get("portrait_verdict", "?")
        verdict_sym = "✅" if verdict == "approved" else ("🔄" if verdict == "retry" else "⚠️")
        print(f"\n  Вердикт портрета: {verdict_sym} {verdict.upper()}")
        if verdict == "retry":
            rd = result.get("retry_details", {})
            print(f"  Проблема: {rd.get('issue', '')}")
        elif verdict == "fallback":
            fd = result.get("fallback_details", {})
            print(f"  Стратегия: {fd.get('strategy', '')} — {fd.get('reason', '')}")
        fc = result.get("final_cover_composition", {})
        if fc:
            print("  final_cover_composition: получена ✅")
    print("=" * 60)


def print_art_director_results(result: dict):
    print("\n" + "=" * 60)
    print("РЕЗУЛЬТАТ: АРТ-ДИРЕКТОР (Роль 15)")
    print("=" * 60)
    plan = result.get("page_plan", [])
    stats = result.get("layout_stats", {})
    print(f"\n  Страниц в page_plan: {len(plan)}")
    if stats:
        print(f"  Текстовых: {stats.get('text_only_pages', '?')} | "
              f"С фото: {stats.get('text_with_photo_pages', '?')} | "
              f"Full-page: {stats.get('full_page_photos', '?')}")
    notes = result.get("design_notes", "")
    if notes:
        print(f"\n  Заметки: {notes[:200]}")
    print("=" * 60)


def print_layout_designer_results(result: dict):
    print("\n" + "=" * 60)
    print("РЕЗУЛЬТАТ: ВЕРСТАЛЬЩИК (Роль 08)")
    print("=" * 60)
    lc = result.get("layout_code", {})
    page_map = result.get("page_map", [])
    tn = result.get("technical_notes", {})
    sg = result.get("style_guide", {})

    print(f"\n  Формат кода: {lc.get('format', '?')}")
    print(f"  Код: {len(lc.get('code', ''))} симв.")
    print(f"  Команда сборки: {lc.get('build_command', '?')}")
    print(f"  Зависимости: {', '.join(lc.get('dependencies', []))}")
    print(f"  Страниц (page_map): {len(page_map)}")
    print(f"  Всего страниц (technical_notes): {tn.get('total_pages', '?')}")

    page_info = sg.get("page", {})
    if page_info:
        print(f"\n  Формат страницы: {page_info.get('format', '?')} "
              f"({page_info.get('width_mm', '?')}×{page_info.get('height_mm', '?')} мм)")

    issues = tn.get("potential_issues", [])
    if issues:
        print(f"\n  Предупреждения верстальщика ({len(issues)}):")
        for iss in issues[:3]:
            print(f"    • {iss.get('issue', '')}")
    print("=" * 60)


def print_interview_results(result: dict):
    print("\n" + "=" * 60)
    print("РЕЗУЛЬТАТ: ИНТЕРВЬЮЕР (Роль 11)")
    print("=" * 60)
    questions = result.get("questions", [])
    groups = result.get("question_groups", [])
    summary = result.get("summary", {})

    total = summary.get("total_questions", len(questions))
    print(f"\n  Вопросов: {total} | Групп: {len(groups)}")

    by_cat = summary.get("by_category", {})
    if by_cat:
        print("\n  По категориям:")
        cat_names = {
            "life_turning_point": "Жизненные повороты",
            "inner_world": "Внутренний мир",
            "social_environment": "Социальная среда",
            "professional_path": "Профессиональный путь",
            "family_structure": "Семья и быт",
            "later_years": "Поздние годы",
            "conflict_resolution": "Разрешение противоречий",
        }
        for k, n in by_cat.items():
            if n:
                sym = "⚠️ " if n == 0 and k != "conflict_resolution" else "  "
                print(f"    {sym}{cat_names.get(k, k)}: {n}")

    note = summary.get("coverage_note", "")
    if note:
        print(f"\n  Покрытие: {note[:200]}")

    if questions:
        high_prio = [q for q in questions if q.get("priority") == "high"]
        print(f"\n  Вопросы высокого приоритета ({len(high_prio)}):")
        for q in high_prio[:5]:
            text = q.get("text", "")[:120]
            cat = q.get("category", "?")
            print(f"    [{cat}] {text}")

    if groups:
        print(f"\n  Группы вопросов:")
        for g in groups:
            qids = g.get("question_ids", [])
            print(f"    • {g.get('theme', '?')} ({len(qids)} вопросов)")
    print("=" * 60)


def print_qa_results(result: dict, iteration: int, mode: str = "combined"):
    print("\n" + "=" * 60)
    print(f"РЕЗУЛЬТАТ: QA ВЁРСТКИ [{mode}] (Роль 09) — итерация {iteration}")
    print("=" * 60)
    verdict = result.get("verdict", "?")
    verdict_sym = "✅ PASS" if verdict == "pass" else "❌ FAIL"
    print(f"\n  Вердикт: {verdict_sym}")

    summary = result.get("summary", {})
    print(f"  Critical: {summary.get('critical_issues', '?')} | "
          f"Major: {summary.get('major_issues', '?')} | "
          f"Minor: {summary.get('minor_issues', '?')}")
    print(f"  Страниц проверено: {summary.get('total_pages_checked', '?')}")

    assessment = summary.get("overall_assessment", "")
    if assessment:
        print(f"\n  Заключение: {assessment[:300]}")

    issues = result.get("issues", [])
    if issues:
        print(f"\n  Проблемы ({len(issues)}):")
        for iss in issues[:5]:
            sev = iss.get("severity", "?")
            page = iss.get("page", "?")
            desc = iss.get("description", "")[:120]
            print(f"    [{sev.upper()}] стр.{page}: {desc}")
        if len(issues) > 5:
            print(f"    ... ещё {len(issues) - 5}")

    checklist = result.get("checklist", {})
    if checklist:
        print("\n  Чеклист:")
        for key, val in checklist.items():
            status = val.get("status", "?") if isinstance(val, dict) else "?"
            sym = "✅" if status == "pass" else ("⚠️" if status == "warning" else "❌")
            print(f"    {sym} {key}: {status}")
    print("=" * 60)


def enforce_chapter_start_purity(
    layout_result: dict,
    strict: bool = False,
    allow_chapter_start_text: bool = False,
) -> dict:
    """Обеспечивает чистоту chapter_start страниц: только заголовок + фото/плейсхолдер.

    Находит все страницы с type == "chapter_start" и проверяет их элементы.
    Нелегальные элементы (paragraph, callout, historical_note, subheading, heading)
    переносятся на следующую страницу (auto-clean по умолчанию).

    Флаги:
    - strict=True            → hard fail при обнаружении вместо переноса
    - allow_chapter_start_text=True → enforcement отключён полностью (debug)

    Возвращает (возможно изменённый) layout_result.
    """
    if allow_chapter_start_text:
        print("[CHAPTER-START] Enforcement отключён (--allow-chapter-start-text)")
        return layout_result

    if layout_result.get("_layout_format") != "pages_json":
        return layout_result

    pages = layout_result.get("pages") or layout_result.get("layout_instructions", {}).get("pages", [])
    if not pages:
        return layout_result

    ILLEGAL_TYPES = {"paragraph", "callout", "historical_note", "subheading", "heading"}
    total_moved = 0

    for i, page in enumerate(pages):
        ptype = (page.get("type") or "").strip()
        if ptype != "chapter_start":
            continue

        elements = page.get("elements", [])
        illegal = [el for el in elements if el.get("type", "") in ILLEGAL_TYPES]
        if not illegal:
            continue

        page_num = page.get("page_number", i + 1)
        ch_id = page.get("chapter_id", "")

        if strict:
            print(
                f"[CHAPTER-START] ❌ HARD FAIL: страница {page_num} (chapter_start {ch_id}) "
                f"содержит {len(illegal)} нелегальных элементов: "
                + ", ".join(f"{el.get('type')}:{el.get('paragraph_ref','')}" for el in illegal[:5])
            )
            print("[CHAPTER-START]   Используй --allow-chapter-start-text для обхода.")
            sys.exit(1)

        # Auto-clean: переместить нелегальные элементы на следующую страницу
        # Найти или создать следующую страницу для этой главы
        if i + 1 < len(pages):
            next_page = pages[i + 1]
        else:
            next_page = None

        # Если следующей страницы нет или она принадлежит другой главе — создаём новую
        if next_page is None or next_page.get("chapter_id", "") != ch_id:
            new_page = {
                "page_number": page_num + 1,
                "type": "chapter_body",
                "chapter_id": ch_id,
                "elements": [],
            }
            pages.insert(i + 1, new_page)
            next_page = new_page
            # Перенумеровать последующие страницы
            for j in range(i + 2, len(pages)):
                pn = pages[j].get("page_number")
                if isinstance(pn, int):
                    pages[j]["page_number"] = pn + 1

        # Перемещаем: нелегальные уходят в начало следующей страницы
        next_page.setdefault("elements", [])
        next_page["elements"] = illegal + next_page["elements"]
        page["elements"] = [el for el in elements if el.get("type", "") not in ILLEGAL_TYPES]

        total_moved += len(illegal)
        print(
            f"[CHAPTER-START] ⚠️  страница {page_num} ({ch_id}): "
            f"перенесено {len(illegal)} элементов на страницу {next_page.get('page_number', '?')}"
        )

    if total_moved == 0:
        print("[CHAPTER-START] ✅ Все chapter_start страницы чисты")
    else:
        print(f"[CHAPTER-START] Итого перенесено элементов: {total_moved}")

    return layout_result


def verify_and_patch_layout_completeness(layout_result: dict, book_final: dict,
                                          allow_hybrid: bool = False) -> dict:
    """Проверяет полноту layout: все paragraph_id из книги должны быть в layout.

    Если пропущены — автоматически добавляет их на последнюю текстовую страницу
    соответствующей главы (или на chapter_start если текстовых страниц нет).

    Возвращает (возможно изменённый) layout_result.
    """
    if layout_result.get("_layout_format") != "pages_json":
        return layout_result

    pages = layout_result.get("pages") or layout_result.get("layout_instructions", {}).get("pages", [])
    if not pages:
        return layout_result

    # Собираем все paragraph_id из книги, сгруппированные по главе
    # Также сохраняем тип (paragraph / subheading) для корректного патча
    book_para_ids: dict[str, list[str]] = {}  # chapter_id -> [ordered paragraph_ids]
    book_para_types: dict[str, dict[str, str]] = {}  # chapter_id -> {pid: type}
    for ch in book_final.get("chapters", []):
        ch_id = ch.get("id", "")
        pars = ch.get("paragraphs", [])
        if ch_id and pars:
            book_para_ids[ch_id] = [p["id"] for p in pars if p.get("id")]
            book_para_types[ch_id] = {
                p["id"]: p.get("type", "paragraph")
                for p in pars if p.get("id")
            }

    # Используем (chapter_id, paragraph_id) туплы чтобы избежать коллизий:
    # prepare_book_for_layout даёт каждой главе p1, p2, ... с одинаковыми именами!
    # Плоское сравнение {p1, p2, ...} неверно — p24 из ch_02 "скроет" пропуск p24 из ch_03.
    all_book_tuples: set[tuple[str, str]] = {
        (ch_id, pid)
        for ch_id, ids in book_para_ids.items()
        for pid in ids
    }

    # Собираем все (chapter_id, paragraph_id) которые уже есть в layout
    # Поддерживаем: paragraph_ref (v3.20+), subheading_ref (v3.21+), paragraph_id (v3.19 legacy)
    layout_tuples: set[tuple[str, str]] = set()
    hybrid_elements: list[str] = []  # описания hybrid элементов для диагностики
    for page in pages:
        page_ch_id = page.get("chapter_id", "")
        for el in page.get("elements", []):
            etype = el.get("type", "")
            if etype not in ("paragraph", "subheading", "section_header"):
                continue
            # paragraph_ref / subheading_ref — новые форматы
            pid    = (
                el.get("paragraph_ref", "")
                or el.get("subheading_ref", "")
                or el.get("paragraph_id", "")
            )
            el_ch  = el.get("chapter_id", "") or page_ch_id
            if pid and el_ch:
                layout_tuples.add((el_ch, pid))
            elif el.get("text") and not pid:
                # Hybrid-элемент: есть inline text, но нет paragraph_ref/paragraph_id.
                # Это означает регрессию LD — модель не перешла на v3.20 ссылочную архитектуру.
                # Auto-patch не добавит ref для такого элемента, но может добавить дубль.
                hybrid_elements.append(
                    f"{el_ch or '(no chapter_id)'}: text='{el.get('text','')[:60]}...'"
                )

    if hybrid_elements:
        msg = (
            f"[LAYOUT-VERIFY] ❌ Обнаружены hybrid элементы (inline text без paragraph_ref): "
            f"{len(hybrid_elements)} шт.\n"
            + "\n".join(f"  {d}" for d in hybrid_elements[:5])
        )
        if allow_hybrid:
            print(msg.replace("❌", "⚠️ "))
            print("[LAYOUT-VERIFY]   --allow-hybrid задан — продолжаем (дубли возможны)")
        else:
            print(msg)
            print("[LAYOUT-VERIFY]   LD выдал hybrid элементы — Layout Designer регрессировал "
                  "и не следует ссылочной архитектуре v3.20.")
            print("[LAYOUT-VERIFY]   Используй --allow-hybrid для обхода (debug режим).")
            sys.exit(1)

    missing_tuples = all_book_tuples - layout_tuples
    if not missing_tuples:
        print(f"[LAYOUT-VERIFY] ✅ Полнота OK: все {len(all_book_tuples)} абзацев присутствуют в layout")
        return layout_result

    # Группируем пропущенные по главе для читаемого вывода
    from collections import defaultdict
    missing_by_ch: dict[str, list[str]] = defaultdict(list)
    for ch_id, pid in missing_tuples:
        missing_by_ch[ch_id].append(pid)
    missing_summary = {ch: sorted(pids, key=lambda x: int(x.lstrip("p") or 0))
                       for ch, pids in missing_by_ch.items()}
    total_missing = sum(len(v) for v in missing_by_ch.values())
    print(f"[LAYOUT-VERIFY] ⚠️  Пропущено {total_missing} из {len(all_book_tuples)} абзацев: {missing_summary}")

    # Для каждой главы — найти последнюю текстовую страницу (тип text/text_with_photo/text_only)
    TEXT_PAGE_TYPES = {"text", "text_with_photo", "text_with_photos", "text_only", "chapter_body"}
    last_text_page_by_chapter: dict[str, dict] = {}
    chapter_start_page_by_chapter: dict[str, dict] = {}
    for page in pages:
        ch_id = page.get("chapter_id", "")
        ptype = (page.get("type") or "").strip()
        if not ch_id:
            continue
        if ptype in TEXT_PAGE_TYPES:
            last_text_page_by_chapter[ch_id] = page
        if ptype == "chapter_start":
            chapter_start_page_by_chapter[ch_id] = page

    # Распределяем пропущенные абзацы в правильном порядке
    for ch_id, ordered_ids in book_para_ids.items():
        missing_for_chapter = [pid for pid in ordered_ids if (ch_id, pid) in missing_tuples]
        if not missing_for_chapter:
            continue

        target_page = last_text_page_by_chapter.get(ch_id) or chapter_start_page_by_chapter.get(ch_id)
        if target_page is None:
            # Создаём новую текстовую страницу для этой главы
            new_page: dict = {
                "page_number": max((p.get("page_number", 0) for p in pages), default=0) + 1,
                "type": "text",
                "chapter_id": ch_id,
                "elements": [],
            }
            pages.append(new_page)
            target_page = new_page
            print(f"[LAYOUT-VERIFY]   Создана новая стр. для {ch_id}: добавлено {len(missing_for_chapter)} абзацев")
        else:
            print(f"[LAYOUT-VERIFY]   {ch_id}: добавляю {len(missing_for_chapter)} абзацев → стр.{target_page.get('page_number','?')} ({target_page.get('type')})")

        for pid in missing_for_chapter:
            elem_type = book_para_types.get(ch_id, {}).get(pid, "paragraph")
            if elem_type == "subheading":
                target_page.setdefault("elements", []).append({
                    "type": "subheading",
                    "chapter_id": ch_id,
                    "subheading_ref": pid,
                })
            else:
                target_page.setdefault("elements", []).append({
                    "type": "paragraph",
                    "chapter_id": ch_id,
                    "paragraph_ref": pid,
                })

    # Обновляем pages в layout_result
    if "pages" in layout_result:
        layout_result["pages"] = pages
    elif "layout_instructions" in layout_result:
        layout_result["layout_instructions"]["pages"] = pages

    total_after = len({
        (page.get("chapter_id", "") or el.get("chapter_id", ""), el.get("paragraph_ref") or el.get("paragraph_id"))
        for page in pages
        for el in page.get("elements", [])
        if el.get("paragraph_ref") or el.get("paragraph_id")
    })
    print(f"[LAYOUT-VERIFY] ✅ После патча: {total_after}/{len(all_book_tuples)} абзацев в layout")
    return layout_result


def save_code_file(layout_result: dict, prefix: str, ts: str) -> Path | None:
    """Сохраняет сгенерированный код вёрстки или pages-схему в отдельный файл."""
    layout_format = layout_result.get("_layout_format", "code")

    if layout_format == "pages_json":
        # pages[] формат — сохраняем JSON-схему
        pages = layout_result.get("pages") or layout_result.get("layout_instructions", {}).get("pages", [])
        if not pages:
            return None
        code_path = ROOT / "exports" / f"{prefix}_layout_pages_{ts}.json"
        with open(code_path, "w", encoding="utf-8") as f:
            json.dump({"pages": pages, "style_guide": layout_result.get("style_guide", {})}, f,
                      ensure_ascii=False, indent=2)
        return code_path

    # layout_code.code формат
    lc = layout_result.get("layout_code", {})
    code = lc.get("code", "")
    if not code:
        return None
    fmt = lc.get("format", "unknown")
    ext = "py" if "python" in fmt.lower() or "reportlab" in fmt.lower() else (
          "html" if "html" in fmt.lower() else "txt")
    code_path = ROOT / "exports" / f"{prefix}_layout_code_{ts}.{ext}"
    with open(code_path, "w", encoding="utf-8") as f:
        f.write(code)
    return code_path


# ──────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--proofreader-report", default=None,
                        help="Legacy: JSON-отчёт Корректора (только с --allow-legacy-input)")
    parser.add_argument("--fact-map", default=None,
                        help="Legacy: JSON с fact_map (только с --allow-legacy-input)")
    parser.add_argument("--photos-dir", default=None,
                        help="Директория с фото проекта (необязательно)")
    parser.add_argument("--prefix", default=DEFAULT_PREFIX,
                        help="Префикс для имён выходных файлов")
    parser.add_argument("--skip-qa", action="store_true",
                        help="Не запускать QA-цикл")
    parser.add_argument("--skip-layout", action="store_true",
                        help="Запустить только Арт-директора")
    parser.add_argument("--use-existing-cover", default=None,
                        help="Путь к JSON Call2 (final_cover_composition) от предыдущего прогона Cover Designer")
    parser.add_argument("--existing-portrait", default=None,
                        help="Путь к .webp/.png портрету от предыдущего прогона (используется с --use-existing-cover)")
    parser.add_argument("--existing-page-plan", default=None,
                        help="Путь к JSON page_plan от предыдущего прогона Арт-директора (пропускает Шаг 1)")
    parser.add_argument("--existing-layout", default=None,
                        help="Путь к готовому layout JSON (переиспользование без повторных LLM вызовов)")
    parser.add_argument("--allow-legacy-input", action="store_true",
                        help="Разрешить legacy-входы из exports вместо approved checkpoints")
    parser.add_argument("--allow-mismatch", action="store_true",
                        help="Fidelity ошибки — предупреждение вместо hard fail (debug режим)")
    parser.add_argument("--allow-hybrid", action="store_true",
                        help="Hybrid элементы (без ref/id, с inline text) — warn вместо hard fail (debug режим)")
    parser.add_argument("--strict-chapter-start", action="store_true",
                        help="Hard fail если найден текст на chapter_start странице (prod режим)")
    parser.add_argument("--allow-chapter-start-text", action="store_true",
                        help="Отключить chapter_start enforcement полностью (debug режим)")
    parser.add_argument(
        "--subject-profile",
        default=None,
        help="JSON с полями project_id, subject_name, subject{...}, interview_architect{...} (другой герой)",
    )
    parser.add_argument("--text-only", action="store_true",
                        help="Ворота 2a/2b: рендерить только текстовый слой")
    parser.add_argument("--with-bio-block", action="store_true",
                        help="Ворота 2b: в режиме --text-only добавить bio_data блок ch_01")
    parser.add_argument("--no-photos", action="store_true",
                        help="Ворота 2c: рендерить без реальных фото (с плейсхолдерами chapter_start)")
    parser.add_argument("--with-cover", action="store_true",
                        help="Ворота 4: включить обложку")
    parser.add_argument("--acceptance-gate", choices=["1", "2a", "2b", "2c", "3", "4"], default=None,
                        help="Номер ворот приёмки (для enforced checkpoint flow)")
    parser.add_argument("--approve-gate", action="store_true",
                        help="Сразу отметить чекпойнт текущих ворот как approved=true")
    args = parser.parse_args()

    if args.acceptance_gate == "1":
        # Gate 1 = text-only story mode, без bio_data и фото
        args.text_only = True
        args.with_bio_block = False
        args.no_photos = False
        args.with_cover = False
        args.skip_qa = True   # QA ложно срабатывает на отсутствие фото в text-only
    elif args.acceptance_gate == "2a":
        args.text_only = True
        args.with_bio_block = False
        args.no_photos = False
        args.with_cover = False
        args.skip_qa = True
    elif args.acceptance_gate == "2b":
        args.text_only = True
        args.with_bio_block = True
        args.no_photos = False
        args.with_cover = False
        args.skip_qa = True
    elif args.acceptance_gate == "2c":
        args.text_only = False
        args.with_bio_block = True   # 2c = 2b + callouts/справки/плейсхолдеры
        args.no_photos = True
        args.with_cover = False
    elif args.acceptance_gate == "3":
        args.text_only = False
        args.with_bio_block = False
        args.no_photos = False
        args.with_cover = False
    elif args.acceptance_gate == "4":
        args.with_cover = True

    ensure_previous_gate_approved(args.acceptance_gate)
    if args.acceptance_gate in {"2b", "2c", "3", "4"} and not args.existing_layout:
        raise RuntimeError(
            f"Ворота {args.acceptance_gate} должны переиспользовать layout из 2a: укажи --existing-layout <file>."
        )

    if args.subject_profile:
        apply_subject_profile(Path(args.subject_profile))

    cfg = load_config()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    proofreader_input_path, fact_map_input_path, input_meta = resolve_inputs(args, ts)

    # ─── Загрузка данных ───
    print(f"\n[INPUT] Загружаю book_final из: {proofreader_input_path.name}")
    book_final, style_passport = load_book_final(proofreader_input_path)
    book_final = prepare_book_for_layout(book_final)
    total_paras = sum(len(ch.get("paragraphs", [])) for ch in book_final.get("chapters", []))
    chars = count_chars(book_final)
    print(f"[INPUT] Глав: {len(book_final['chapters'])} | "
          f"Символов: {chars} | "
          f"Абзацев (indexed): {total_paras} | "
          f"Callouts: {len(book_final.get('callouts', []))} | "
          f"Историч.блоков: {len(book_final.get('historical_notes', []))}")
    if style_passport:
        print(f"[INPUT] style_passport: имён={len(style_passport.get('person_names', []))}")

    print(f"\n[INPUT] Загружаю fact_map из: {fact_map_input_path.name}")
    fact_map = load_fact_map(fact_map_input_path)
    sync_subject_years_from_fact_map(fact_map, allow_clear_death=not bool(args.subject_profile))
    gaps = fact_map.get("gaps", [])
    print(f"[INPUT] fact_map: persons={len(fact_map.get('persons', []))} | "
          f"timeline={len(fact_map.get('timeline', []))} | gaps={len(gaps)}")
    print(f"[INPUT] subject years for cover: birth={SUBJECT.get('birth_year')} death={SUBJECT.get('death_year')}")

    # Режим без фото
    photos = []
    if args.photos_dir:
        photos_dir = Path(args.photos_dir)
        if photos_dir.exists():
            manifest_path = photos_dir / "manifest.json"
            if manifest_path.exists():
                # Загружаем с подписями из манифеста
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                photos = []
                for e in sorted(manifest, key=lambda x: x["index"]):
                    if e.get("exclude"):
                        continue
                    # local_path может быть Windows-путём (если манифест создан на Windows)
                    # Приоритет: photos_dir / filename (кроссплатформенно)
                    actual_path = photos_dir / e["filename"]
                    if not actual_path.exists():
                        # Fallback: попробуем local_path как есть
                        actual_path = Path(e["local_path"])
                    if not actual_path.exists():
                        continue
                    photos.append({
                        "id": f"photo_{e['index']:03d}",
                        "photo_id": e["photo_id"],
                        "filename": e["filename"],
                        "local_path": str(actual_path),
                        "caption": e.get("caption") or "",
                        "created_at": e.get("created_at", ""),
                    })
                excluded = sum(1 for e in manifest if e.get("exclude"))
                with_cap = sum(1 for p in photos if p["caption"])
                excl_note = f", исключено: {excluded}" if excluded else ""
                print(f"[INPUT] Загружено из манифеста: {len(photos)} фото ({with_cap} с подписями{excl_note})")
            else:
                if input_meta.get("mode") == "strict_checkpoint":
                    raise RuntimeError(
                        f"В strict режиме требуется фиксированный photos/manifest.json, но не найден: {manifest_path}"
                    )
                # Fallback: просто сканируем директорию
                photo_files = sorted(
                    list(photos_dir.glob("*.jpg")) + list(photos_dir.glob("*.png"))
                )
                photos = [
                    {"id": f"photo_{i+1:03d}", "filename": p.name, "local_path": str(p), "caption": ""}
                    for i, p in enumerate(photo_files)
                ]
                print(f"[INPUT] Найдено фото (без манифеста): {len(photos)}")
        else:
            print(f"[INPUT] Директория фото не найдена: {photos_dir}")
    else:
        print("[INPUT] Фото не переданы — text-only режим")

    if args.acceptance_gate == "3" and not photos:
        raise RuntimeError("Ворота 3 требуют реальные фото (--photos-dir с валидным manifest.json).")
    if args.acceptance_gate == "4" and not photos:
        print("[WARN] Ворота 4 запущены без фото — обложка будет построена без референса.")

    print(f"[MODE] acceptance_gate={args.acceptance_gate or 'none'} | "
          f"text_only={args.text_only} with_bio_block={args.with_bio_block} "
          f"no_photos={args.no_photos} with_cover={args.with_cover}")

    expected_content = build_expected_content(book_final, photos)
    cover_composition = None
    cover_portrait = None

    if args.existing_layout:
        existing_layout_path = Path(args.existing_layout)
        if not existing_layout_path.exists():
            raise FileNotFoundError(f"--existing-layout не найден: {existing_layout_path}")
        print(f"[REUSE] Использую готовый layout: {existing_layout_path}")
        layout_raw = json.loads(existing_layout_path.read_text(encoding="utf-8"))
        layout_result = validate_layout_output(layout_raw)
        if layout_result is None:
            raise RuntimeError(f"Файл --existing-layout невалиден: {existing_layout_path}")

        # Проверяем полноту layout и патчим пропущенные абзацы (с учётом chapter_id)
        layout_result = verify_and_patch_layout_completeness(layout_result, book_final,
                                                               allow_hybrid=args.allow_hybrid)

        # chapter_start enforcement: нелегальные элементы переносятся на следующую страницу
        layout_result = enforce_chapter_start_purity(
            layout_result,
            strict=getattr(args, "strict_chapter_start", False),
            allow_chapter_start_text=getattr(args, "allow_chapter_start_text", False),
        )

        # Валидация соответствия layout ↔ book_FINAL (задача 017)
        try:
            from validate_layout_fidelity import validate_fidelity as _vf
            _allow_mm = getattr(args, "allow_fc_fail", False)
            _passed, _ferrors = _vf(layout_result, book_final, allow_mismatch=True)
            if _ferrors:
                print(f"[FIDELITY] ⚠️  {len(_ferrors)} нарушений (существующий layout — fidelity-предупреждения)")
        except ImportError:
            pass

        code_path = save_code_file(layout_result, f"{args.prefix}_reuse", ts)
        if not code_path:
            raise RuntimeError("Не удалось извлечь pages/layout_code из --existing-layout")

        pdf_output_path = ROOT / "exports" / f"{args.prefix}_stage4_gate_{args.acceptance_gate or 'reuse'}_{ts}.pdf"
        render_script = ROOT / "scripts" / "pdf_renderer.py"
        render_cmd = [sys.executable, str(render_script), "--layout", str(code_path), "--book", str(proofreader_input_path.resolve())]
        if args.text_only:
            render_cmd.append("--text-only")
        if args.with_bio_block:
            render_cmd.append("--with-bio-block")
        if args.no_photos:
            render_cmd.append("--no-photos")
        if args.with_cover:
            render_cmd.append("--with-cover")
        # Auto-detect photos_dir если не передан явно (для gate 3/4 с реальными фото).
        # gate 2a/2b/2c — text-only, авто-детект не применяется.
        photos_dir_effective = args.photos_dir
        if not photos_dir_effective and args.acceptance_gate in {"3", "4"}:
            # Пробуем strip _stageN suffix из PROJECT_ID: "karakulina_stage4" → "karakulina"
            _proj_base = PROJECT_ID.split("_stage")[0]
            for _candidate in [
                ROOT / "exports" / f"{_proj_base}_photos",
                ROOT / "exports" / f"{PROJECT_ID}_photos",
                ROOT / "photos",
            ]:
                if _candidate.exists() and any(_candidate.iterdir()):
                    photos_dir_effective = str(_candidate)
                    print(f"[REUSE] Auto photos_dir: {_candidate}")
                    break
        # Явный guard: на gate 2a/2b/2c игнорируем photos_dir (даже если передан явно)
        if args.acceptance_gate in {"2a", "2b", "2c"} and photos_dir_effective:
            print(
                f"[WARN] gate {args.acceptance_gate}: photos_dir проигнорирован "
                f"(text-only режим). Фото: {photos_dir_effective}"
            )
            photos_dir_effective = None
        if photos_dir_effective:
            render_cmd += ["--photos-dir", str(Path(photos_dir_effective).resolve())]
        if args.existing_portrait and Path(args.existing_portrait).exists():
            render_cmd += ["--portrait", str(Path(args.existing_portrait).resolve())]
        render_cmd += ["--output", str(pdf_output_path)]

        print(f"[REUSE] Рендер PDF из существующего layout ({render_script.name})")
        build_result = subprocess.run(
            render_cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
            cwd=str(ROOT),
        )
        if build_result.returncode != 0 or not pdf_output_path.exists():
            raise RuntimeError(
                f"Сборка PDF из existing-layout не удалась (exit={build_result.returncode}). "
                f"stderr: {(build_result.stderr or '')[-400:]}"
            )

        print(f"[REUSE] ✅ PDF: {pdf_output_path.name}")
        save_acceptance_checkpoint(
            gate=args.acceptance_gate,
            approved=args.approve_gate,
            payload={
                "project_id": PROJECT_ID,
                "ts": ts,
                "final_verdict": "pass",
                "page_plan_path": None,
                "layout_result_path": str(existing_layout_path),
                "qa_report_path": None,
                "pdf_path": str(pdf_output_path),
                "mode": {
                    "text_only": args.text_only,
                    "with_bio_block": args.with_bio_block,
                    "no_photos": args.no_photos,
                    "with_cover": args.with_cover,
                },
                "reused_layout": True,
            },
        )
        save_run_manifest(
            output_dir=ROOT / "exports",
            prefix=args.prefix,
            stage="stage4",
            project_id=PROJECT_ID,
            cfg=cfg,
            ts=ts,
            inputs={
                "proofreader_input_path": str(proofreader_input_path),
                "fact_map_input_path": str(fact_map_input_path),
                "input_mode": input_meta.get("mode"),
                "photos_dir": args.photos_dir,
                "acceptance_gate": args.acceptance_gate,
                "text_only": args.text_only,
                "with_bio_block": args.with_bio_block,
                "no_photos": args.no_photos,
                "with_cover": args.with_cover,
                "existing_layout": str(existing_layout_path),
                "photos_mode": (
                    "none" if args.acceptance_gate in {"2a", "2b", "2c"}
                    else ("real" if photos_dir_effective else "placeholders")
                ),
            },
            outputs={
                "page_plan_path": None,
                "layout_result_path": str(existing_layout_path),
                "qa_report_path": None,
                "final_verdict": "pass",
                "generated_artifacts": [code_path.name, pdf_output_path.name],
            },
            checkpoints=input_meta.get("checkpoints", {}),
        )
        return

    # ─── API клиент ───
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("[ERROR] ANTHROPIC_API_KEY не задан")
        sys.exit(1)
    client = anthropic.Anthropic(api_key=api_key)

    # ══════════════════════════════════════════════════════════════
    # ШАГ 0: COVER DESIGNER (cover_designer, Роль 13) — только для --with-cover
    # ══════════════════════════════════════════════════════════════
    if args.with_cover:
        print("\n" + "─" * 60)
        print("ШАГ 0: COVER DESIGNER (cover_designer, Роль 13)")
        print(f"        Фото: {len(photos)} | Replicate: {'включён' if os.environ.get('REPLICATE_API_TOKEN') else 'НЕ ЗАДАН'}")
        print("─" * 60)
    else:
        print("\n[SKIP] Cover Designer: --with-cover не задан (ворота 2a/2b/2c/3)")

    cover_portrait_path = None
    cover_portrait_bytes = None
    final_cover_composition = None

    # --- Использование существующей обложки (--use-existing-cover) ---
    if args.with_cover and args.use_existing_cover:
        existing_cover_path = Path(args.use_existing_cover)
        if existing_cover_path.exists():
            with open(existing_cover_path, encoding="utf-8") as f:
                existing_cover_data = json.load(f)
            final_cover_composition = existing_cover_data.get("final_cover_composition", existing_cover_data)
            print(f"[COVER_DESIGNER] ♻️  Используем существующую обложку: {existing_cover_path.name}")
            if args.existing_portrait:
                portrait_path = Path(args.existing_portrait)
                if portrait_path.exists():
                    cover_portrait_path = portrait_path
                    cover_portrait_bytes = portrait_path.read_bytes()
                    print(f"[COVER_DESIGNER] ♻️  Существующий портрет: {portrait_path.name} ({len(cover_portrait_bytes)} байт)")
                else:
                    print(f"[COVER_DESIGNER] ⚠️  Портрет не найден: {portrait_path}")
        else:
            print(f"[COVER_DESIGNER] ⚠️  Файл обложки не найден: {existing_cover_path} — запускаем Cover Designer")
            args.use_existing_cover = None

    if args.with_cover and not args.use_existing_cover:
        # --- Вызов 1: арт-дирекция ---
        cd1_raw = await run_cover_designer_call1(client, photos, cfg)

        if not isinstance(cd1_raw, dict) or "portrait_generation" not in cd1_raw:
            print("[COVER_DESIGNER] ⚠️  Неожиданный ответ Call 1 — пропускаем обложку")
            cover_composition = None
        else:
            cd1_path = ROOT / "exports" / f"{args.prefix}_stage4_cover_designer_call1_{ts}.json"
            with open(cd1_path, "w", encoding="utf-8") as f:
                json.dump(cd1_raw, f, ensure_ascii=False, indent=2)
            print(f"[SAVED] cover_designer_call1: {cd1_path.name}")

        prev_composition = cd1_raw.get("cover_composition", {})
        pg = cd1_raw.get("portrait_generation", {})
        image_gen_prompt = pg.get("image_gen_prompt", "")

        # --- Replicate: генерация ink sketch ---
        portrait_bytes = None
        if image_gen_prompt and os.environ.get("REPLICATE_API_TOKEN"):
            # Загружаем референс-фото (выбранное Cover Designer)
            ref_photo_id = pg.get("reference_photo_id") or cd1_raw.get("selected_photo", {}).get("photo_id")
            ref_image_bytes: bytes | None = None
            if ref_photo_id and photos:
                ref_photo = next((p for p in photos if p.get("id") == ref_photo_id or p.get("photo_id") == ref_photo_id), None)
                if ref_photo and Path(ref_photo["local_path"]).exists():
                    ref_image_bytes = Path(ref_photo["local_path"]).read_bytes()
                    print(f"\n[REPLICATE] Референс-фото: {ref_photo_id} ({len(ref_image_bytes)} байт)")
                else:
                    print(f"\n[REPLICATE] ⚠️  Референс-фото {ref_photo_id!r} не найдено — генерим без референса")
            else:
                print(f"\n[REPLICATE] ⚠️  reference_photo_id не задан — генерим без референса")

            print(f"[REPLICATE] Генерируем ink sketch портрет{'  (flux-dev img2img + референс)' if ref_image_bytes else ' (FLUX text-only, без референса)'}...")
            print(f"[REPLICATE] Prompt: {image_gen_prompt[:100]}...")
            start_r = datetime.now()
            portrait_bytes = run_replicate_ink_sketch(image_gen_prompt, ref_image_bytes)
            elapsed_r = (datetime.now() - start_r).total_seconds()
            if portrait_bytes:
                cover_portrait_path = ROOT / "exports" / f"{args.prefix}_stage4_cover_portrait_{ts}.webp"
                with open(cover_portrait_path, "wb") as f:
                    f.write(portrait_bytes)
                print(f"[REPLICATE] ✅ Портрет готов за {elapsed_r:.1f}с | {len(portrait_bytes)} байт")
                print(f"[SAVED] cover_portrait: {cover_portrait_path.name}")
                cover_portrait_bytes = portrait_bytes
            else:
                print(f"[REPLICATE] ❌ Генерация не удалась — продолжаем без портрета")
        else:
            if not image_gen_prompt:
                print("[REPLICATE] Пропуск: нет image_gen_prompt от Cover Designer")
            else:
                print("[REPLICATE] Пропуск: REPLICATE_API_TOKEN не задан")

        print_cover_designer_results(1, cd1_raw, portrait_bytes)

        # --- Вызов 2: валидация портрета ---
        if portrait_bytes:
            print(f"\n[COVER_DESIGNER] Вызов 2: валидация портрета...")
            # Сжимаем до 768px чтобы не превышать 200K токенов Anthropic
            portrait_small = _shrink_image_for_llm(portrait_bytes, max_px=768)
            print(f"[COVER_DESIGNER] Портрет сжат: {len(portrait_bytes)//1024}KB → {len(portrait_small)//1024}KB для LLM")
            portrait_b64 = image_bytes_to_base64(portrait_small)

            for attempt in range(1, MAX_PORTRAIT_ATTEMPTS + 1):
                cd2_raw = await run_cover_designer_call2(
                    client, prev_composition, portrait_b64, attempt, cfg
                )
                cd2_path = ROOT / "exports" / f"{args.prefix}_stage4_cover_designer_call2_a{attempt}_{ts}.json"
                with open(cd2_path, "w", encoding="utf-8") as f:
                    json.dump(cd2_raw, f, ensure_ascii=False, indent=2)
                print(f"[SAVED] cover_designer_call2: {cd2_path.name}")
                print_cover_designer_results(2, cd2_raw)

                portrait_verdict = cd2_raw.get("portrait_verdict", "")
                if portrait_verdict == "approved":
                    final_cover_composition = cd2_raw.get("final_cover_composition", prev_composition)
                    print(f"[COVER_DESIGNER] ✅ Портрет принят на попытке {attempt}")
                    break
                elif portrait_verdict == "retry" and attempt < MAX_PORTRAIT_ATTEMPTS:
                    retry_details = cd2_raw.get("retry_details", {})
                    new_prompt = retry_details.get("updated_prompt", image_gen_prompt)
                    print(f"[COVER_DESIGNER] 🔄 Retry {attempt}/{MAX_PORTRAIT_ATTEMPTS}: перегенерируем")
                    print(f"[REPLICATE] Новый prompt: {new_prompt[:100]}...")
                    portrait_bytes = run_replicate_ink_sketch(new_prompt, ref_image_bytes)
                    if portrait_bytes:
                        cover_portrait_path = ROOT / "exports" / f"{args.prefix}_stage4_cover_portrait_r{attempt}_{ts}.webp"
                        with open(cover_portrait_path, "wb") as f:
                            f.write(portrait_bytes)
                        portrait_small = _shrink_image_for_llm(portrait_bytes, max_px=768)
                        portrait_b64 = image_bytes_to_base64(portrait_small)
                        print(f"[SAVED] cover_portrait (retry {attempt}): {cover_portrait_path.name}")
                    else:
                        print("[REPLICATE] Retry не удался — принимаем как есть")
                        final_cover_composition = prev_composition
                        break
                else:
                    # fallback или исчерпаны попытки
                    fallback = cd2_raw.get("fallback_details", {})
                    strategy = fallback.get("strategy", "typography_only")
                    print(f"[COVER_DESIGNER] ⚠️  Fallback: {strategy} — обложка без портрета")
                    final_cover_composition = cd2_raw.get("final_cover_composition", prev_composition)
                    cover_portrait_path = None
                    cover_portrait_bytes = None
                    break
        else:
            # Портрет не сгенерирован — используем предварительную композицию
            final_cover_composition = prev_composition
            print("[COVER_DESIGNER] Используем предварительную композицию (без портрета)")

        cover_composition = final_cover_composition

    # cover_composition выставляется в обоих ветках (existing или новый)
    cover_composition = final_cover_composition

    # ══════════════════════════════════════════════════════════════
    # ШАГ 1: АРТ-ДИРЕКТОР (layout_art_director, Роль 15)
    # Планирует page_plan — постраничный план макета
    # ══════════════════════════════════════════════════════════════
    print("\n" + "─" * 60)
    print("ШАГ 1: АРТ-ДИРЕКТОР (layout_art_director, Роль 15)")
    print("─" * 60)

    if args.existing_page_plan:
        existing_pp_path = Path(args.existing_page_plan)
        if existing_pp_path.exists():
            with open(existing_pp_path, encoding="utf-8") as f:
                existing_pp_data = json.load(f)
            page_plan = validate_page_plan(existing_pp_data)
            if page_plan:
                art_path = existing_pp_path
                print(f"[ART_DIRECTOR] ♻️  Используем существующий page_plan: {existing_pp_path.name}")
                print_art_director_results(page_plan)
            else:
                print(f"[ART_DIRECTOR] ⚠️  Невалидный page_plan в файле — запускаем заново")
                args.existing_page_plan = None
        else:
            print(f"[ART_DIRECTOR] ⚠️  Файл не найден: {existing_pp_path} — запускаем заново")
            args.existing_page_plan = None

    if not args.existing_page_plan:
        art_result_raw = await run_art_director(client, book_final, photos, cover_composition, cfg)

        page_plan = validate_page_plan(art_result_raw)
        if page_plan is None:
            raw_path = ROOT / "exports" / f"{args.prefix}_art_director_raw_{ts}.json"
            with open(raw_path, "w", encoding="utf-8") as f:
                json.dump(art_result_raw, f, ensure_ascii=False, indent=2)
            print(f"[SAVED] Сырой ответ: {raw_path.name}")
            print("[ERROR] Арт-директор вернул невалидный page_plan — завершаем")
            sys.exit(1)

        art_path = ROOT / "exports" / f"{args.prefix}_stage4_page_plan_{ts}.json"
        with open(art_path, "w", encoding="utf-8") as f:
            json.dump(page_plan, f, ensure_ascii=False, indent=2)
        print(f"[SAVED] page_plan: {art_path.name}")
        print_art_director_results(page_plan)

    if args.skip_layout:
        print("\n✅ Запущен только Арт-директор. --skip-layout задан.")
        return

    # ══════════════════════════════════════════════════════════════
    # ШАГ 2+3: ВЕРСТАЛЬЩИК + QA (цикл до max_qa_iterations)
    # ══════════════════════════════════════════════════════════════
    layout_result = None
    qa_result = None
    previous_qa_issues = []
    final_verdict = None
    layout_path = None
    qa_path = None
    structural_qa_path = None
    visual_qa_path = None
    preflight_path = None
    callout_precheck_path = None

    for qa_iteration in range(1, MAX_QA_ITERATIONS + 1):
        print(f"\n{'─' * 60}")
        print(f"ШАГ 2: ВЕРСТАЛЬЩИК (layout_designer, Роль 08) — итерация {qa_iteration}")
        print("─" * 60)

        pdf_output_path = ROOT / "exports" / f"{args.prefix}_stage4_pdf_iter{qa_iteration}_{ts}.pdf"

        layout_raw = await run_layout_designer(
            client,
            book_final=book_final,
            photos=photos,
            page_plan=page_plan,
            cover_portrait=cover_portrait,
            cover_composition=cover_composition,
            style_passport=style_passport,
            qa_report=qa_result,
            iteration=qa_iteration,
            cfg=cfg,
            book_json_path=str(proofreader_input_path.resolve()),
            photos_dir_path=str(Path(args.photos_dir).resolve()) if args.photos_dir and args.acceptance_gate not in {"2a", "2b", "2c"} else None,
            pdf_output_path=str(pdf_output_path),
        )

        layout_result = validate_layout_output(layout_raw)
        if layout_result is None:
            raw_path = ROOT / "exports" / f"{args.prefix}_layout_raw_iter{qa_iteration}_{ts}.json"
            with open(raw_path, "w", encoding="utf-8") as f:
                json.dump(layout_raw, f, ensure_ascii=False, indent=2)
            print(f"[SAVED] Сырой ответ: {raw_path.name}")
            print(f"[WARN] Итерация {qa_iteration}: невалидный layout — пробуем следующую")
            continue

        # Сохраняем результат верстальщика
        layout_path = ROOT / "exports" / f"{args.prefix}_stage4_layout_iter{qa_iteration}_{ts}.json"
        with open(layout_path, "w", encoding="utf-8") as f:
            json.dump(layout_result, f, ensure_ascii=False, indent=2)
        print(f"[SAVED] layout_result: {layout_path.name}")

        print_layout_designer_results(layout_result)

        # ─── Верификация полноты layout (все paragraph_refs должны быть в layout) ───
        layout_result = verify_and_patch_layout_completeness(layout_result, book_final,
                                                               allow_hybrid=args.allow_hybrid)

        # chapter_start enforcement: нелегальные элементы переносятся на следующую страницу
        layout_result = enforce_chapter_start_purity(
            layout_result,
            strict=getattr(args, "strict_chapter_start", False),
            allow_chapter_start_text=getattr(args, "allow_chapter_start_text", False),
        )

        # Валидация соответствия layout ↔ book_FINAL: completeness, order, uniqueness (задача 017)
        try:
            from validate_layout_fidelity import validate_fidelity as _vf
            _passed_fid, _ferrors = _vf(layout_result, book_final, allow_mismatch=False)
            if not _passed_fid:
                if args.allow_mismatch:
                    print(f"[FIDELITY] ⚠️  Нарушения fidelity (--allow-mismatch задан, продолжаем):")
                    for _fe in _ferrors:
                        print(f"           {_fe}")
                else:
                    print(f"[FIDELITY] ❌ Нарушения fidelity — прогон остановлен:")
                    for _fe in _ferrors:
                        print(f"           {_fe}")
                    print("[FIDELITY] ℹ️  Используй --allow-mismatch для обхода (debug режим)")
                    sys.exit(1)
            else:
                print(f"[FIDELITY] ✅ Все проверки прошли")
        except ImportError:
            print("[FIDELITY] ⚠️  validate_layout_fidelity.py не найден — валидация пропущена")

        # Перезаписываем layout_path с патчем (если были пропуски)
        with open(layout_path, "w", encoding="utf-8") as f:
            json.dump(layout_result, f, ensure_ascii=False, indent=2)

        # Сохраняем код вёрстки отдельно (после патча — чтобы code_path содержал полный layout)
        code_path = save_code_file(layout_result, f"{args.prefix}_iter{qa_iteration}", ts)
        if code_path:
            print(f"[SAVED] layout_code: {code_path.name}")
            print(f"        Запуск: {layout_result.get('layout_code', {}).get('build_command', '?')}")
        built_pdf_path = None
        layout_format = layout_result.get("_layout_format", "code")

        if layout_format == "pages_json":
            # Верстальщик v3+: pages[] формат — строим PDF через pdf_renderer.py
            print(f"\n{'─' * 60}")
            print(f"ШАГ 2.5: СБОРКА PDF (pdf_renderer.py) — итерация {qa_iteration}")
            print("─" * 60)
            try:
                render_script = ROOT / "scripts" / "pdf_renderer.py"
                render_cmd = [sys.executable, str(render_script), "--layout", str(code_path)]
                # Передаём book для lookup paragraph_id → текст (архитектура v3.19)
                render_cmd += ["--book", str(proofreader_input_path.resolve())]
                if args.text_only:
                    render_cmd.append("--text-only")
                if args.with_bio_block:
                    render_cmd.append("--with-bio-block")
                if args.no_photos:
                    render_cmd.append("--no-photos")
                if args.with_cover:
                    render_cmd.append("--with-cover")
                # Guard: gate 2a/2b/2c — не передаём photos_dir в рендерер (симметрично 1644-1649)
                if args.photos_dir:
                    if args.acceptance_gate in {"2a", "2b", "2c"}:
                        print(f"[WARN] gate {args.acceptance_gate}: --photos-dir игнорируется для pdf_renderer (text-only mode)")
                    else:
                        render_cmd += ["--photos-dir", str(Path(args.photos_dir).resolve())]
                # Используем cover_portrait_path (сгенерированный или переданный)
                effective_portrait = cover_portrait_path or (Path(args.existing_portrait) if args.existing_portrait else None)
                if effective_portrait and Path(effective_portrait).exists():
                    render_cmd += ["--portrait", str(Path(effective_portrait).resolve())]
                render_cmd += ["--output", str(pdf_output_path)]
                print(f"[BUILD] Запускаю: python {render_script.name}")
                build_result = subprocess.run(
                    render_cmd,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=180,
                    cwd=str(ROOT),
                )
                if build_result.returncode == 0 and Path(pdf_output_path).exists():
                    built_pdf_path = str(pdf_output_path)
                    size_kb = Path(pdf_output_path).stat().st_size // 1024
                    print(f"[BUILD] ✅ PDF собран: {Path(pdf_output_path).name} ({size_kb} KB)")
                else:
                    print(f"[BUILD] ❌ Ошибка сборки (exit {build_result.returncode})")
                    out_tail = (build_result.stdout or "")[-300:]
                    err_tail = (build_result.stderr or "")[-500:]
                    if out_tail:
                        print(f"[BUILD] stdout:\n{out_tail}")
                    if err_tail:
                        print(f"[BUILD] stderr:\n{err_tail}")
            except subprocess.TimeoutExpired:
                print("[BUILD] ❌ Таймаут сборки (180с)")
            except Exception as e:
                print(f"[BUILD] ❌ Ошибка запуска: {e}")

        elif code_path and code_path.suffix == ".py":
            print(f"\n{'─' * 60}")
            print(f"ШАГ 2.5: СБОРКА PDF — итерация {qa_iteration}")
            print("─" * 60)
            try:
                build_env = {
                    **os.environ,
                    "PDF_OUTPUT_PATH": str(pdf_output_path),
                    "BOOK_JSON_PATH": str(proofreader_input_path.resolve()),
                    "PHOTOS_DIR": str(Path(args.photos_dir).resolve()) if args.photos_dir else "",
                }
                print(f"[BUILD] Запускаю: python {code_path.name}")
                build_result = subprocess.run(
                    [sys.executable, str(code_path)],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=180,
                    cwd=str(ROOT),
                    env=build_env,
                )
                if build_result.returncode == 0 and pdf_output_path.exists():
                    built_pdf_path = str(pdf_output_path)
                    size_kb = pdf_output_path.stat().st_size // 1024
                    print(f"[BUILD] ✅ PDF собран: {pdf_output_path.name} ({size_kb} KB)")
                else:
                    if build_result.returncode != 0:
                        print(f"[BUILD] ❌ Ошибка сборки (exit {build_result.returncode})")
                        stderr_tail = (build_result.stderr or "")[-500:]
                        if stderr_tail:
                            print(f"[BUILD] stderr:\n{stderr_tail}")
                    else:
                        print("[BUILD] ⚠️  Скрипт выполнен, но PDF не найден по ожидаемому пути")
                        print(f"[BUILD]   Ожидалось: {pdf_output_path}")
            except subprocess.TimeoutExpired:
                print("[BUILD] ❌ Таймаут сборки (180с)")
            except Exception as e:
                print(f"[BUILD] ❌ Ошибка запуска: {e}")
        elif code_path:
            print(f"[BUILD] Пропуск автосборки (формат: {layout_result.get('layout_code', {}).get('format', '?')} — не python)")

        # ─── QA ───
        if args.skip_qa:
            print("\n[SKIP] QA пропущен (--skip-qa)")
            final_verdict = "skipped"
            break

        print(f"\n{'─' * 60}")
        print(f"ШАГ 3: QA ВЁРСТКИ (qa_layout, Роль 09) — итерация {qa_iteration}")
        if built_pdf_path:
            print(f"        PDF: {Path(built_pdf_path).name} ✅")
        else:
            print("        PDF: не доступен (структурная проверка)")
        print("─" * 60)
        # Preflight + structural guard (блокирующие)
        structural_guard = structural_layout_guard(layout_result, page_plan)
        structural_guard_path = ROOT / "exports" / f"{args.prefix}_stage4_structural_guard_iter{qa_iteration}_{ts}.json"
        save_gate_report(structural_guard_path, structural_guard)
        print(f"[SAVED] structural_guard: {structural_guard_path.name}")

        if built_pdf_path:
            preflight = pdf_preflight(built_pdf_path, layout_result.get("page_map", []))
        else:
            preflight = {
                "gate": "pdf_preflight",
                "passed": False,
                "checks": {
                    "exists": False,
                    "readable_header_pdf": False,
                    "size_ok": False,
                    "size_bytes": 0,
                    "min_size_bytes": 12000,
                    "page_map_pages": len(layout_result.get("page_map", [])),
                    "pdf_pages": None,
                    "page_count_match": False,
                },
            }
        preflight_path = ROOT / "exports" / f"{args.prefix}_stage4_pdf_preflight_iter{qa_iteration}_{ts}.json"
        save_gate_report(preflight_path, preflight)
        print(f"[SAVED] pdf_preflight: {preflight_path.name}")

        callout_precheck = run_callout_precheck(expected_content, page_plan, layout_result)
        callout_precheck_path = ROOT / "exports" / f"{args.prefix}_stage4_callout_precheck_iter{qa_iteration}_{ts}.json"
        save_gate_report(callout_precheck_path, callout_precheck)
        print(f"[SAVED] callout_precheck: {callout_precheck_path.name}")

        if not callout_precheck.get("passed"):
            qa_result = {
                "verdict": "fail",
                "issues": [
                    {
                        "severity": "critical",
                        "type": "callout_precheck_failed",
                        "description": "Детерминированный precheck callout IDs не пройден",
                        "details": {
                            "missing_in_page_plan": callout_precheck.get("missing_in_page_plan", []),
                            "missing_in_page_map": callout_precheck.get("missing_in_page_map", []),
                            "extra_in_page_map": callout_precheck.get("extra_in_page_map", []),
                        },
                    }
                ],
                "summary": {
                    "critical_issues": 1,
                    "major_issues": 0,
                    "minor_issues": 0,
                    "total_pages_checked": len(layout_result.get("page_map", []) or []),
                    "overall_assessment": "callout_precheck failed before QA",
                    "fonts_embedded": True,
                },
                "qa_modes": {
                    "structural_qa": {"verdict": "skipped", "reason": "blocked by callout_precheck"},
                    "visual_qa": {"verdict": "skipped", "reason": "blocked by callout_precheck"},
                },
            }
            qa_path = ROOT / "exports" / f"{args.prefix}_stage4_qa_iter{qa_iteration}_{ts}.json"
            with open(qa_path, "w", encoding="utf-8") as f:
                json.dump(qa_result, f, ensure_ascii=False, indent=2)
            print(f"[SAVED] qa_report: {qa_path.name}")
            print("[QA] ⛔ Пропуск LLM-QA: callout_precheck не пройден")
            final_verdict = qa_result.get("verdict")
            if qa_iteration >= MAX_QA_ITERATIONS:
                print(f"\n⚠️  QA FAIL после {MAX_QA_ITERATIONS} итераций — эскалация к Продюсеру (не реализована в тесте)")
                break
            previous_qa_issues = qa_result.get("issues", [])
            print(f"\n🔄 QA FAIL — передаём Верстальщику на доработку (итерация {qa_iteration + 1})")
            continue

        structural_raw = await run_layout_qa(
            client,
            layout_result=layout_result,
            page_plan=page_plan,
            expected_content=expected_content,
            iteration=qa_iteration,
            previous_qa_issues=previous_qa_issues,
            cfg=cfg,
            qa_mode="structural_qa",
            pdf_path=None,
        )
        structural_qa = validate_qa_output(structural_raw)
        if structural_qa is None:
            structural_qa = {
                "verdict": "fail",
                "issues": [{"severity": "critical", "description": "Invalid structural_qa output"}],
                "summary": {"critical_issues": 1, "major_issues": 0, "minor_issues": 0, "total_pages_checked": 0, "overall_assessment": "invalid structural_qa", "fonts_embedded": True},
            }
        structural_qa_path = ROOT / "exports" / f"{args.prefix}_stage4_structural_qa_iter{qa_iteration}_{ts}.json"
        with open(structural_qa_path, "w", encoding="utf-8") as f:
            json.dump(structural_qa, f, ensure_ascii=False, indent=2)
        print(f"[SAVED] structural_qa: {structural_qa_path.name}")
        print_qa_results(structural_qa, qa_iteration, mode="structural_qa")

        visual_qa = {
            "verdict": "pass",
            "issues": [],
            "summary": {"critical_issues": 0, "major_issues": 0, "minor_issues": 0, "total_pages_checked": 0, "overall_assessment": "visual_qa skipped (pdf unavailable or preflight failed)", "fonts_embedded": True},
        }
        if built_pdf_path and preflight.get("passed"):
            visual_raw = await run_layout_qa(
                client,
                layout_result=layout_result,
                page_plan=page_plan,
                expected_content=expected_content,
                iteration=qa_iteration,
                previous_qa_issues=previous_qa_issues,
                cfg=cfg,
                qa_mode="visual_qa",
                pdf_path=built_pdf_path,
            )
            visual_validated = validate_qa_output(visual_raw)
            if visual_validated is None:
                visual_qa = {
                    "verdict": "fail",
                    "issues": [{"severity": "critical", "description": "Invalid visual_qa output"}],
                    "summary": {"critical_issues": 1, "major_issues": 0, "minor_issues": 0, "total_pages_checked": 0, "overall_assessment": "invalid visual_qa", "fonts_embedded": False},
                }
            else:
                visual_qa = visual_validated
            visual_qa_path = ROOT / "exports" / f"{args.prefix}_stage4_visual_qa_iter{qa_iteration}_{ts}.json"
            with open(visual_qa_path, "w", encoding="utf-8") as f:
                json.dump(visual_qa, f, ensure_ascii=False, indent=2)
            print(f"[SAVED] visual_qa: {visual_qa_path.name}")
            print_qa_results(visual_qa, qa_iteration, mode="visual_qa")

        qa_result = combine_qa_reports_with_mode(
            structural_qa=structural_qa,
            visual_qa=visual_qa,
            visual_non_blocking=bool(preflight.get("passed")),
        )
        if not structural_guard.get("passed"):
            qa_result["verdict"] = "fail"
            qa_result.setdefault("issues", []).append(
                {"severity": "critical", "type": "structural_guard_failed", "description": "structural_layout_guard не пройден"}
            )
        if built_pdf_path and not preflight.get("passed"):
            qa_result["verdict"] = "fail"
            qa_result.setdefault("issues", []).append(
                {"severity": "critical", "type": "pdf_preflight_failed", "description": "PDF preflight не пройден"}
            )

        qa_path = ROOT / "exports" / f"{args.prefix}_stage4_qa_iter{qa_iteration}_{ts}.json"
        with open(qa_path, "w", encoding="utf-8") as f:
            json.dump(qa_result, f, ensure_ascii=False, indent=2)
        print(f"[SAVED] qa_report: {qa_path.name}")
        print_qa_results(qa_result, qa_iteration, mode="combined")

        final_verdict = qa_result.get("verdict")

        if final_verdict == "pass":
            print(f"\n✅ QA PASS на итерации {qa_iteration} — вёрстка принята!")
            break

        if qa_iteration >= MAX_QA_ITERATIONS:
            print(f"\n⚠️  QA FAIL после {MAX_QA_ITERATIONS} итераций — эскалация к Продюсеру (не реализована в тесте)")
            break

        # Готовим issues для следующей итерации
        previous_qa_issues = qa_result.get("issues", [])
        print(f"\n🔄 QA FAIL — передаём Верстальщику на доработку (итерация {qa_iteration + 1})")

    # ══════════════════════════════════════════════════════════════
    # ШАГ 4: ИНТЕРВЬЮЕР (interview_architect, Роль 11)
    # Параллельно с вёрсткой — здесь запускаем после QA
    # ══════════════════════════════════════════════════════════════
    interview_result = None
    gaps = fact_map.get("gaps", [])

    if gaps:
        print(f"\n{'─' * 60}")
        print(f"ШАГ 4: ИНТЕРВЬЮЕР (interview_architect, Роль 11)")
        print(f"        gaps: {len(gaps)}")
        print("─" * 60)

        ia_raw = await run_interview_architect(client, fact_map, book_final, cfg)
        interview_result = validate_interview_questions(ia_raw)

        if interview_result is None:
            ia_raw_path = ROOT / "exports" / f"{args.prefix}_ia_raw_{ts}.json"
            with open(ia_raw_path, "w", encoding="utf-8") as f:
                json.dump(ia_raw, f, ensure_ascii=False, indent=2)
            print(f"[SAVED] Сырой ответ Интервьюера: {ia_raw_path.name}")
        else:
            ia_path = ROOT / "exports" / f"{args.prefix}_stage4_interview_questions_{ts}.json"
            with open(ia_path, "w", encoding="utf-8") as f:
                json.dump(interview_result, f, ensure_ascii=False, indent=2)
            print(f"[SAVED] interview_questions: {ia_path.name}")
            print_interview_results(interview_result)

            # Стык 10: сборка ai_questions = clarifying + blitz
            ai_questions = {
                "clarifying": interview_result.get("questions", []),
                "blitz": cfg.get("blitz_questions", []),
            }
            aq_path = ROOT / "exports" / f"{args.prefix}_stage4_ai_questions_{ts}.json"
            with open(aq_path, "w", encoding="utf-8") as f:
                json.dump(ai_questions, f, ensure_ascii=False, indent=2)
            print(f"[SAVED] ai_questions (clarifying={len(ai_questions['clarifying'])}, "
                  f"blitz={len(ai_questions['blitz'])}): {aq_path.name}")
    else:
        print("\n[SKIP] Интервьюер: gaps пустой — вопросы не нужны")

    # ══════════════════════════════════════════════════════════════
    # ИТОГ
    # ══════════════════════════════════════════════════════════════
    print(f"\n{'=' * 60}")
    print("  ИТОГ ЭТАПА 4")
    print("=" * 60)
    print(f"  Проект: {PROJECT_ID}")
    print(f"  page_plan: {art_path.name}")
    if layout_result:
        lc = layout_result.get("layout_code", {})
        print(f"  Формат кода: {lc.get('format', '?')}")
        print(f"  Страниц: {layout_result.get('technical_notes', {}).get('total_pages', '?')}")
    if cover_portrait_path:
        print(f"  Портрет обложки: {cover_portrait_path.name} ✅")
    elif final_cover_composition:
        print(f"  Обложка: текстовая композиция (без портрета)")
    else:
        print(f"  Обложка: не сгенерирована")
    if final_verdict:
        verdict_sym = "✅" if final_verdict == "pass" else ("⏭️" if final_verdict == "skipped" else "❌")
        print(f"  QA вердикт: {verdict_sym} {final_verdict.upper()}")
    if interview_result:
        total_q = interview_result.get("summary", {}).get("total_questions", len(interview_result.get("questions", [])))
        print(f"  Вопросов для клиента: {total_q}")
    elif not gaps:
        print("  Вопросов: 0 (gaps пустой)")
    print(f"\n  {'⚠️  СЛЕДУЮЩИЙ ШАГ:' if not photos else '✅ СЛЕДУЮЩИЙ ШАГ:'}")
    if not photos:
        print("  Нужны фото Каракулиной для запуска Photo Editor (07) и Cover Designer (13).")
        print("  Передайте: --photos-dir <директория_с_фото>")
    print("=" * 60)

    generated = sorted((ROOT / "exports").glob(f"{args.prefix}*{ts}*"))
    save_acceptance_checkpoint(
        gate=args.acceptance_gate,
        approved=args.approve_gate,
        payload={
            "project_id": PROJECT_ID,
            "ts": ts,
            "final_verdict": final_verdict,
            "page_plan_path": str(art_path) if "art_path" in locals() else None,
            "layout_result_path": str(layout_path) if layout_path else None,
            "qa_report_path": str(qa_path) if qa_path else None,
            "pdf_path": str(pdf_output_path) if "pdf_output_path" in locals() and Path(pdf_output_path).exists() else None,
            "mode": {
                "text_only": args.text_only,
                "with_bio_block": args.with_bio_block,
                "no_photos": args.no_photos,
                "with_cover": args.with_cover,
            },
        },
    )

    save_run_manifest(
        output_dir=ROOT / "exports",
        prefix=args.prefix,
        stage="stage4",
        project_id=PROJECT_ID,
        cfg=cfg,
        ts=ts,
        inputs={
            "proofreader_input_path": str(proofreader_input_path),
            "fact_map_input_path": str(fact_map_input_path),
            "input_mode": input_meta.get("mode"),
            "photos_dir": args.photos_dir,
            "skip_qa": args.skip_qa,
            "skip_layout": args.skip_layout,
            "acceptance_gate": args.acceptance_gate,
            "text_only": args.text_only,
            "with_bio_block": args.with_bio_block,
            "no_photos": args.no_photos,
            "with_cover": args.with_cover,
            "photos_mode": (
                "none" if args.acceptance_gate in {"2a", "2b", "2c"}
                else ("real" if args.photos_dir and args.acceptance_gate not in {"2a", "2b", "2c"} else "placeholders")
            ),
        },
        outputs={
            "page_plan_path": str(art_path) if "art_path" in locals() else None,
            "layout_result_path": str(layout_path) if layout_path else None,
            "callout_precheck_path": str(callout_precheck_path) if callout_precheck_path else None,
            "structural_qa_path": str(structural_qa_path) if structural_qa_path else None,
            "visual_qa_path": str(visual_qa_path) if visual_qa_path else None,
            "pdf_preflight_path": str(preflight_path) if preflight_path else None,
            "qa_report_path": str(qa_path) if qa_path else None,
            "cover_portrait_path": str(cover_portrait_path) if cover_portrait_path else None,
            "final_verdict": final_verdict,
            "generated_artifacts": [p.name for p in generated],
        },
        checkpoints=input_meta.get("checkpoints", {}),
    )


if __name__ == "__main__":
    asyncio.run(main())
