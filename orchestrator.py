# -*- coding: utf-8 -*-
"""
Оркестратор пайплайна Phase A.

Реализует циклы возврата согласно спецификации Даши:
  - run_fact_check_loop     : Fact Checker → Ghostwriter (до 3 итераций)
  - run_literary_edit_loop  : Literary Editor → Ghostwriter (до 2 итераций)
  - run_layout_qa_loop      : Layout QA → Layout Designer (до 3 итераций)

Каждая функция:
  1. Загружает промпт из Flask Admin API
  2. Вызывает OpenAI
  3. Парсит JSON-ответ
  4. Если verdict = fail/return_to_writer → вызывает автора с правками
  5. Повторяет до max_iterations раз
  6. Возвращает финальный артефакт + метаинформацию о цикле

Использование из Flask:
  from orchestrator import run_fact_check_loop, run_literary_edit_loop, run_layout_qa_loop
"""
import json
import logging
import re
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)

# ── Конфигурация итераций ────────────────────────────────────────
MAX_ITER = {
    "fact_checker_to_ghostwriter": 3,
    "literary_editor_to_ghostwriter": 2,
    "layout_qa_to_layout_designer": 3,
}

OPENAI_MODELS = {
    "fact_checker":    "gpt-4o-mini",
    "ghostwriter":     "gpt-4o",
    "literary_editor": "gpt-4o-mini",
    "proofreader":     "gpt-4o-mini",
    "layout_designer": "gpt-4o-mini",
    "layout_qa":       "gpt-4o-mini",
}

OPENAI_TEMPS = {
    "fact_checker":    0.0,
    "ghostwriter":     0.5,
    "literary_editor": 0.4,
    "proofreader":     0.0,
    "layout_designer": 0.25,
    "layout_qa":       0.05,
}

OPENAI_MAX_TOKENS = {
    "fact_checker":    4000,
    "ghostwriter":     12000,
    "literary_editor": 8000,
    "proofreader":     8000,
    "layout_designer": 6000,
    "layout_qa":       3000,
}


# ── Вспомогательные функции ──────────────────────────────────────

def _get_prompt(role: str, admin_url: str, timeout: int = 10) -> str:
    """Загружает промпт агента из Flask Admin API."""
    try:
        r = requests.get(f"{admin_url}/api/prompts/{role}", timeout=timeout)
        r.raise_for_status()
        return r.json().get("text", "")
    except Exception as e:
        logger.warning("orchestrator: не удалось загрузить промпт %s: %s", role, e)
        return ""


def _parse_json(text: str) -> dict:
    """Извлекает первый JSON-объект из строки (LLM часто добавляет пояснения)."""
    text = text.strip()
    # Убираем markdown-блоки ```json ... ```
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    # Ищем первый {...}
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass
    # Попытка напрямую
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


def _call_openai(
    role: str,
    system_prompt: str,
    user_message: dict,
    openai_key: str,
    timeout: int = 300,
) -> dict:
    """Вызывает OpenAI и возвращает распарсенный JSON-ответ агента."""
    model = OPENAI_MODELS.get(role, "gpt-4o-mini")
    temperature = OPENAI_TEMPS.get(role, 0.3)
    max_tokens = OPENAI_MAX_TOKENS.get(role, 4000)

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt or f"Ты {role}. Верни валидный JSON."},
            {"role": "user", "content": json.dumps(user_message, ensure_ascii=False)},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    try:
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=timeout,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        result = _parse_json(content)
        logger.info("orchestrator: %s → verdict=%s", role, result.get("verdict", "n/a"))
        return result
    except Exception as e:
        logger.error("orchestrator: ошибка вызова %s: %s", role, e)
        return {}


def _build_context(
    project_id: str,
    phase: str,
    call_type: str,
    iteration: int,
    max_iterations: int,
    previous_agent: str,
    instruction: str,
) -> dict:
    """Формирует секцию context по протоколу оркестратора."""
    return {
        "project_id": project_id,
        "phase": phase,
        "call_type": call_type,
        "iteration": iteration,
        "max_iterations": max_iterations,
        "previous_agent": previous_agent,
        "instruction": instruction,
    }


# ── Цикл 1: Fact Checker → Ghostwriter ──────────────────────────

def run_fact_check_loop(
    book_draft: dict,
    fact_map: dict,
    transcripts: list,
    openai_key: str,
    admin_url: str,
    project_id: str = "proj",
    max_iterations: int | None = None,
) -> dict:
    """
    Запускает цикл: Fact Checker проверяет → при fail → Ghostwriter правит.
    Возвращает:
      {
        "book_draft": <финальный черновик>,
        "warnings": [...],
        "verdict": "pass" | "fail",
        "iterations_used": int,
        "all_pass": bool
      }
    """
    if max_iterations is None:
        max_iterations = MAX_ITER["fact_checker_to_ghostwriter"]

    fc_prompt = _get_prompt("fact_checker", admin_url)
    gw_prompt = _get_prompt("ghostwriter", admin_url)

    warnings = []
    last_verdict = "pass"

    for iteration in range(1, max_iterations + 1):
        logger.info("orchestrator: fact_check iteration %d/%d", iteration, max_iterations)

        # Вызов Fact Checker
        fc_msg = {
            "context": _build_context(
                project_id, "A",
                "initial" if iteration == 1 else "revision",
                iteration, max_iterations,
                "ghostwriter",
                "Проверь текст книги на соответствие карте фактов и транскрипту. "
                "Выдай вердикт: pass (нет критичных ошибок) или fail (найдены ошибки).",
            ),
            "data": {
                "book_draft": book_draft,
                "fact_map": fact_map,
                "transcripts": transcripts,
            },
        }
        fc_result = _call_openai("fact_checker", fc_prompt, fc_msg, openai_key)

        verdict = fc_result.get("verdict", "pass")
        warnings = fc_result.get("warnings", [])
        last_verdict = verdict

        if verdict == "pass":
            logger.info("orchestrator: fact_checker passed on iteration %d", iteration)
            break

        # verdict == "fail" и ещё есть итерации
        if iteration < max_iterations:
            errors = fc_result.get("errors", [])
            logger.info(
                "orchestrator: fact_checker fail, %d errors → revision %d",
                len(errors), iteration + 1,
            )

            # Вызов Ghostwriter для правок
            gw_msg = {
                "context": _build_context(
                    project_id, "A", "revision",
                    iteration + 1, max_iterations,
                    "fact_checker",
                    "Фактчекер нашёл ошибки в тексте. Исправь ТОЛЬКО указанные проблемы. "
                    "Не переписывай текст целиком — внеси точечные исправления.",
                ),
                "data": {
                    "book_draft": book_draft,
                    "fact_checker_report": {
                        "verdict": verdict,
                        "errors": errors,
                        "warnings": warnings,
                        "summary": fc_result.get("summary", {}),
                    },
                    "fact_map": fact_map,
                    "transcripts": transcripts,
                },
            }
            gw_result = _call_openai("ghostwriter", gw_prompt, gw_msg, openai_key)
            if gw_result.get("chapters"):
                book_draft = gw_result
            else:
                logger.warning("orchestrator: ghostwriter revision returned no chapters, keeping previous")
        else:
            logger.warning(
                "orchestrator: fact_checker exhausted %d iterations, proceeding with last draft",
                max_iterations,
            )

    return {
        "book_draft": book_draft,
        "warnings": warnings,
        "verdict": last_verdict,
        "iterations_used": iteration,
        "all_pass": last_verdict == "pass",
    }


# ── Цикл 2: Literary Editor → Ghostwriter ───────────────────────

def run_literary_edit_loop(
    book_draft: dict,
    fact_checker_warnings: list,
    openai_key: str,
    admin_url: str,
    project_id: str = "proj",
    max_iterations: int | None = None,
) -> dict:
    """
    Запускает цикл: Literary Editor редактирует → при return_to_writer → Ghostwriter правит.
    Возвращает:
      {
        "book_text": <plain text>,
        "chapters": [...],
        "iterations_used": int,
        "verdict": "pass" | "return_to_writer"
      }
    """
    if max_iterations is None:
        max_iterations = MAX_ITER["literary_editor_to_ghostwriter"]

    le_prompt = _get_prompt("literary_editor", admin_url)
    gw_prompt = _get_prompt("ghostwriter", admin_url)

    last_verdict = "pass"

    for iteration in range(1, max_iterations + 1):
        logger.info("orchestrator: literary_edit iteration %d/%d", iteration, max_iterations)

        le_msg = {
            "context": _build_context(
                project_id, "A",
                "initial" if iteration == 1 else "revision",
                iteration, max_iterations,
                "fact_checker" if iteration == 1 else "ghostwriter",
                "Отредактируй текст книги: единство голоса, переходы, ритм, тон, антиклише, читаемость. "
                "Не меняй факты. Обработай предупреждения фактчекера.",
            ),
            "data": {
                "book_draft": book_draft,
                "fact_checker_warnings": fact_checker_warnings,
            },
        }
        le_result = _call_openai("literary_editor", le_prompt, le_msg, openai_key)

        verdict = le_result.get("verdict", "pass")
        last_verdict = verdict

        if verdict == "pass":
            chapters = le_result.get("chapters") or book_draft.get("chapters", [])
            book_text = _chapters_to_text(chapters)
            logger.info("orchestrator: literary_editor passed on iteration %d", iteration)
            return {
                "book_text": book_text,
                "chapters": chapters,
                "iterations_used": iteration,
                "verdict": "pass",
            }

        # verdict == "return_to_writer"
        return_reasons = le_result.get("return_to_writer_reasons") or le_result.get("return_reasons", [])
        style_assessment = le_result.get("style_assessment", {})

        if iteration < max_iterations:
            logger.info(
                "orchestrator: literary_editor return_to_writer (%d reasons) → revision",
                len(return_reasons),
            )
            gw_msg = {
                "context": _build_context(
                    project_id, "A", "revision",
                    iteration + 1, max_iterations,
                    "literary_editor",
                    "Литредактор обнаружил структурные проблемы. Переработай указанные главы. "
                    "Факты не менять — только структуру и подачу.",
                ),
                "data": {
                    "book_draft": book_draft,
                    "return_reasons": return_reasons,
                    "style_assessment": style_assessment,
                },
            }
            gw_result = _call_openai("ghostwriter", gw_prompt, gw_msg, openai_key)
            if gw_result.get("chapters"):
                book_draft = gw_result
        else:
            logger.warning(
                "orchestrator: literary_editor exhausted iterations, using last draft",
            )

    chapters = book_draft.get("chapters", [])
    return {
        "book_text": _chapters_to_text(chapters),
        "chapters": chapters,
        "iterations_used": iteration,
        "verdict": last_verdict,
    }


# ── Цикл 3: Layout QA → Layout Designer ─────────────────────────

def run_layout_qa_loop(
    layout_spec: dict,
    bio_text: str,
    photo_layout: list,
    openai_key: str,
    admin_url: str,
    project_id: str = "proj",
    max_iterations: int | None = None,
) -> dict:
    """
    Запускает цикл: Layout QA проверяет → при fail → Layout Designer правит.
    Возвращает:
      {
        "layout_spec": <финальный spec>,
        "iterations_used": int,
        "verdict": "pass" | "fail"
      }
    """
    if max_iterations is None:
        max_iterations = MAX_ITER["layout_qa_to_layout_designer"]

    qa_prompt = _get_prompt("layout_qa", admin_url)
    ld_prompt = _get_prompt("layout_designer", admin_url)

    last_verdict = "pass"

    for iteration in range(1, max_iterations + 1):
        logger.info("orchestrator: layout_qa iteration %d/%d", iteration, max_iterations)

        qa_msg = {
            "context": _build_context(
                project_id, "A",
                "initial" if iteration == 1 else "revision",
                iteration, max_iterations,
                "layout_designer",
                "Проверь макет книги: структура, главы, оглавление, фотографии, "
                "технические параметры. Выдай вердикт: pass или fail.",
            ),
            "data": {
                "layout_spec": layout_spec,
                "bio_text_length": len(bio_text),
                "photo_count": len(photo_layout),
            },
        }
        qa_result = _call_openai("layout_qa", qa_prompt, qa_msg, openai_key)

        verdict = qa_result.get("verdict", "pass")
        last_verdict = verdict

        if verdict == "pass":
            logger.info("orchestrator: layout_qa passed on iteration %d", iteration)
            break

        issues = qa_result.get("issues", [])

        if iteration < max_iterations:
            logger.info(
                "orchestrator: layout_qa fail (%d issues) → revision",
                len(issues),
            )
            ld_msg = {
                "context": _build_context(
                    project_id, "A", "revision",
                    iteration + 1, max_iterations,
                    "layout_qa",
                    "QA вёрстки обнаружил проблемы в макете. Исправь указанные проблемы. "
                    "Стиль и содержание не менять.",
                ),
                "data": {
                    "previous_layout_spec": layout_spec,
                    "qa_report": {"verdict": verdict, "issues": issues},
                    "bio_text": bio_text,
                    "photo_layout": photo_layout,
                },
            }
            ld_result = _call_openai("layout_designer", ld_prompt, ld_msg, openai_key)
            if ld_result:
                layout_spec = ld_result
        else:
            logger.warning(
                "orchestrator: layout_qa exhausted iterations, proceeding",
            )

    return {
        "layout_spec": layout_spec,
        "iterations_used": iteration,
        "verdict": last_verdict,
    }


# ── Утилиты ──────────────────────────────────────────────────────

def _chapters_to_text(chapters: list) -> str:
    """Собирает plain text из массива глав."""
    parts = []
    for ch in chapters:
        title = ch.get("title", "")
        content = ch.get("content", "")
        if title:
            parts.append(f"\n{title}\n\n{content}")
        elif content:
            parts.append(content)
    return "\n\n".join(parts).strip()
