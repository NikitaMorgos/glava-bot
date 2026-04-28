#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pipeline_python.py — Полный Python-пайплайн Phase A без n8n.

Замена n8n для production: берёт транскрипт, прогоняет через все агенты
(Claude/Anthropic), сохраняет результат в book_versions.

Цепочка агентов:
  Cleaner → Fact Extractor → [Historian ‖ Ghostwriter 1st pass]
  → Ghostwriter 2nd pass (historian integration)
  → Fact Check loop (до 3 итераций)
  → Literary Editor
  → Proofreader
  → Сохранение в book_versions

Вызов из pipeline_n8n.py (fallback когда нет N8N_WEBHOOK_PHASE_A):
  from pipeline_python import run_phase_a_background
  run_phase_a_background(telegram_id, transcript, character_name, draft_id)

Прямой запуск для тестов:
  python pipeline_python.py --telegram-id 577528 --character-name "Каракулина"
"""

import hashlib
import json
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent


# ── Инициализация клиента ────────────────────────────────────────

def _make_anthropic_client():
    try:
        import anthropic
        key = os.getenv("ANTHROPIC_API_KEY", "")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY не задан")
        return anthropic.Anthropic(api_key=key)
    except ImportError:
        raise RuntimeError("pip install anthropic")


# ── Хэш транскрипта для защиты версий ───────────────────────────

def _transcript_hash(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()[:16]


# ── Сохранение в БД ──────────────────────────────────────────────

def _save_to_db(telegram_id: int, character_name: str, bio_text: str,
                transcript_hash: str, pipeline_source: str = "python") -> int:
    """
    Сохраняет результат пайплайна в book_versions.

    Защита: не перезаписывает одобренную (is_approved=True) версию.
    Возвращает version номер.
    """
    try:
        import psycopg2
        db_url = os.getenv("DATABASE_URL", "")
        if not db_url:
            logger.warning("DATABASE_URL не задан — результат не сохранён в БД")
            return 0

        conn = psycopg2.connect(db_url)
        cur = conn.cursor()

        # Проверяем есть ли одобренная версия
        cur.execute(
            "SELECT id, version FROM book_versions "
            "WHERE telegram_id = %s AND is_approved = TRUE "
            "ORDER BY version DESC LIMIT 1",
            (telegram_id,)
        )
        approved = cur.fetchone()
        if approved:
            logger.warning(
                "pipeline_python: telegram_id=%s уже имеет одобренную версию v=%s (id=%s). "
                "Новый результат сохранён как НЕ одобренный.",
                telegram_id, approved[1], approved[0]
            )

        # Получаем текущий максимальный version
        cur.execute(
            "SELECT COALESCE(MAX(version), 0) FROM book_versions WHERE telegram_id = %s",
            (telegram_id,)
        )
        max_v = cur.fetchone()[0]
        new_version = max_v + 1

        cur.execute(
            """INSERT INTO book_versions
               (telegram_id, version, bio_text, character_name,
                is_approved, transcript_hash, pipeline_source, created_at)
               VALUES (%s, %s, %s, %s, FALSE, %s, %s, NOW())
               RETURNING id""",
            (telegram_id, new_version, bio_text, character_name,
             transcript_hash, pipeline_source)
        )
        new_id = cur.fetchone()[0]
        conn.commit()
        conn.close()

        logger.info(
            "pipeline_python: сохранено book_versions id=%s v=%s tg=%s (is_approved=False)",
            new_id, new_version, telegram_id
        )
        return new_version

    except Exception as e:
        logger.exception("pipeline_python: ошибка сохранения в БД: %s", e)
        return 0


def _notify_user(telegram_id: int, message: str):
    """Отправляет сообщение пользователю через Telegram Bot API."""
    try:
        import requests
        token = os.getenv("BOT_TOKEN", "")
        if not token:
            return
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": telegram_id, "text": message},
            timeout=10,
        )
    except Exception as e:
        logger.warning("pipeline_python: не удалось отправить сообщение: %s", e)


# ── Вспомогательная: собрать plain text из chapters ──────────────

def _chapters_to_text(chapters: list) -> str:
    parts = []
    for ch in chapters:
        title = ch.get("title", "")
        content = ch.get("content", "")
        if title:
            parts.append(f"\n{title}\n\n{content}")
        elif content:
            parts.append(content)
    return "\n\n".join(parts).strip()


# ── Основной пайплайн Phase A ────────────────────────────────────

def run_phase_a(
    telegram_id: int,
    transcript: str,
    character_name: str = "",
    draft_id: int = 0,
    narrator_name: str = "",
    narrator_relation: str = "рассказчик",
) -> dict:
    """
    Запускает полный Phase A пайплайн.

    Возвращает {
        "success": bool,
        "bio_text": str,
        "book_draft": dict,
        "version": int,
        "error": str | None,
    }
    """
    from pipeline_utils import (
        load_config,
        run_cleaner,
        run_fact_extractor,
        run_historian,
        run_ghostwriter,
        run_fact_checker,
        run_literary_editor,
        run_proofreader,
    )

    project_id = f"tg_{telegram_id}"
    t_hash = _transcript_hash(transcript)
    cfg = load_config()
    result = {"success": False, "bio_text": "", "book_draft": {}, "version": 0, "error": None}

    logger.info("pipeline_python Phase A: start tg=%s len_transcript=%s", telegram_id, len(transcript))
    _notify_user(telegram_id, "Начинаю создание вашей книги... Это займёт около 10–15 минут.")

    try:
        client = _make_anthropic_client()

        # ── Шаг 1: Cleaner ─────────────────────────────────────
        logger.info("pipeline_python: [1/7] Cleaner")
        subject_name = character_name or "Герой книги"
        narr = narrator_name or subject_name
        cleaned_text, _ = run_cleaner(
            client, transcript, subject_name, narr, narrator_relation, cfg=cfg
        )

        transcripts_list = [{
            "interview_id": "int_001",
            "speaker_name": narr,
            "relation_to_subject": narrator_relation,
            "text": cleaned_text,
        }]

        # ── Шаг 2: Fact Extractor ──────────────────────────────
        logger.info("pipeline_python: [2/7] Fact Extractor")
        fact_map = run_fact_extractor(
            client, cleaned_text, subject_name,
            narr, narrator_relation, project_id, cfg=cfg
        )

        # ── Шаг 3: Historian (параллельно не блокирует) ─────────
        logger.info("pipeline_python: [3/7] Historian")
        historical_context = {}
        try:
            historical_context = run_historian(client, fact_map, cfg=cfg)
        except Exception as e:
            logger.warning("pipeline_python: Historian ошибка (пропускаем): %s", e)

        # ── Шаг 4: Ghostwriter (1-й проход) ────────────────────
        logger.info("pipeline_python: [4/7] Ghostwriter (1st pass)")
        book_draft = run_ghostwriter(
            client, fact_map, transcripts_list, project_id,
            phase="A", call_type="initial", cfg=cfg
        )

        # ── Шаг 4b: Ghostwriter (2-й проход: Historian integration) ──
        if historical_context.get("historical_context"):
            logger.info("pipeline_python: [4b] Ghostwriter (historian integration)")
            try:
                book_draft = run_ghostwriter(
                    client, fact_map, transcripts_list, project_id,
                    phase="A", call_type="revision",
                    previous_agent="historian",
                    current_book=book_draft,
                    historical_context=historical_context,
                    cfg=cfg
                )
            except Exception as e:
                logger.warning("pipeline_python: Ghostwriter 2nd pass ошибка (пропускаем): %s", e)

        # ── Шаг 5: Fact Check loop (до 3 итераций) ─────────────
        logger.info("pipeline_python: [5/7] Fact Check loop")
        fc_warnings = []
        for fc_iter in range(1, 4):
            try:
                fc_report = run_fact_checker(
                    client, book_draft, fact_map, transcripts_list,
                    project_id, phase="A",
                    iteration=fc_iter, max_iterations=3, cfg=cfg
                )
                verdict = fc_report.get("verdict", "pass")
                fc_warnings = fc_report.get("warnings", [])
                logger.info("pipeline_python: FC iter=%d verdict=%s", fc_iter, verdict)

                if verdict == "pass":
                    break

                errors = fc_report.get("errors", [])
                if errors and fc_iter < 3:
                    # Ghostwriter revision
                    book_draft = run_ghostwriter(
                        client, fact_map, transcripts_list, project_id,
                        phase="A", call_type="revision",
                        previous_agent="fact_checker",
                        current_book=book_draft,
                        revision_scope={
                            "type": "fact_correction",
                            "affected_chapters": [e.get("chapter_id", "ch_02") for e in errors],
                            "instructions": f"Исправь {len(errors)} ошибок, найденных фактчекером",
                            "new_facts": [],
                            "conflicts": [],
                        },
                        cfg=cfg
                    )
            except Exception as e:
                logger.warning("pipeline_python: Fact Check iter=%d ошибка: %s", fc_iter, e)
                break

        # ── Шаг 6: Literary Editor ──────────────────────────────
        logger.info("pipeline_python: [6/7] Literary Editor")
        try:
            le_result = run_literary_editor(
                client, book_draft, fc_warnings, project_id, phase="A", cfg=cfg
            )
            if le_result.get("chapters"):
                book_draft = le_result
        except Exception as e:
            logger.warning("pipeline_python: Literary Editor ошибка (пропускаем): %s", e)

        # ── Шаг 7: Proofreader ──────────────────────────────────
        logger.info("pipeline_python: [7/7] Proofreader")
        try:
            pr_result = run_proofreader(client, book_draft, project_id, cfg=cfg)
            if pr_result.get("chapters"):
                book_draft = pr_result
        except Exception as e:
            logger.warning("pipeline_python: Proofreader ошибка (пропускаем): %s", e)

        # ── Сохранение ─────────────────────────────────────────
        bio_text = _chapters_to_text(book_draft.get("chapters", []))
        version = _save_to_db(
            telegram_id, character_name or "Герой книги",
            bio_text, t_hash, pipeline_source="python_phase_a"
        )

        result.update({
            "success": True,
            "bio_text": bio_text,
            "book_draft": book_draft,
            "version": version,
        })

        logger.info(
            "pipeline_python Phase A: DONE tg=%s v=%s bio_len=%s",
            telegram_id, version, len(bio_text)
        )
        _notify_user(
            telegram_id,
            f"Ваша книга готова! Версия {version} сохранена. "
            "Мы свяжемся с вами, когда она будет проверена и оформлена."
        )

    except Exception as e:
        logger.exception("pipeline_python Phase A: FATAL ERROR tg=%s: %s", telegram_id, e)
        result["error"] = str(e)
        _notify_user(
            telegram_id,
            "Произошла ошибка при создании книги. Мы уже разбираемся. "
            "Попробуйте позже или напишите в поддержку."
        )

    return result


# ── Фоновый запуск ───────────────────────────────────────────────

def run_phase_a_background(
    telegram_id: int,
    transcript: str,
    character_name: str = "",
    draft_id: int = 0,
    narrator_name: str = "",
    narrator_relation: str = "рассказчик",
) -> None:
    """Запускает run_phase_a в фоновом потоке. Не блокирует бота."""
    def _run():
        try:
            run_phase_a(
                telegram_id=telegram_id,
                transcript=transcript,
                character_name=character_name,
                draft_id=draft_id,
                narrator_name=narrator_name,
                narrator_relation=narrator_relation,
            )
        except Exception as e:
            logger.exception("pipeline_python: фоновый поток упал: %s", e)

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    logger.info("pipeline_python Phase A: запущен в фоне для telegram_id=%s", telegram_id)


# ── CLI для ручного запуска / тестов ─────────────────────────────

if __name__ == "__main__":
    import argparse
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    parser = argparse.ArgumentParser(description="Python Phase A pipeline (без n8n)")
    parser.add_argument("--telegram-id", type=int, required=True)
    parser.add_argument("--character-name", default="")
    parser.add_argument("--transcript-file", default="",
                        help="Путь к файлу транскрипта (по умолчанию: берётся из БД)")
    parser.add_argument("--narrator-name", default="")
    parser.add_argument("--narrator-relation", default="рассказчик")
    args = parser.parse_args()

    if args.transcript_file:
        transcript = Path(args.transcript_file).read_text(encoding="utf-8")
    else:
        import psycopg2
        load_dotenv(ROOT / ".env")
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        cur = conn.cursor()
        cur.execute(
            "SELECT transcript FROM voice_messages "
            "WHERE user_id = (SELECT id FROM users WHERE telegram_id = %s) "
            "AND LENGTH(transcript) > 1000 "
            "ORDER BY created_at DESC LIMIT 1",
            (args.telegram_id,)
        )
        row = cur.fetchone()
        conn.close()
        if not row:
            print(f"[ERROR] Транскрипт не найден для telegram_id={args.telegram_id}")
            import sys; sys.exit(1)
        transcript = row[0]
        print(f"[INFO] Транскрипт из БД: {len(transcript)} символов")

    result = run_phase_a(
        telegram_id=args.telegram_id,
        transcript=transcript,
        character_name=args.character_name,
        narrator_name=args.narrator_name,
        narrator_relation=args.narrator_relation,
    )

    print(f"\n{'='*60}")
    print(f"SUCCESS: {result['success']}")
    print(f"Version: {result['version']}")
    print(f"Bio len: {len(result.get('bio_text', ''))}")
    if result.get('error'):
        print(f"Error:   {result['error']}")
