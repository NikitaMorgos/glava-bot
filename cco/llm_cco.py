# -*- coding: utf-8 -*-
"""LLM-модуль CCO-агента. Вызывает GPT-4o с метриками и контекстом."""
import base64
import logging
import os
import time
from pathlib import Path
from typing import Optional

from cco.cco_prompt import get_system_prompt
from cco.analytics import collect_all_metrics

logger = logging.getLogger(__name__)

CCO_MODEL = os.getenv("CCO_MODEL", "gpt-4o")
MAX_HISTORY = 30
MAX_RESPONSE_TOKENS = 2000
TEMPERATURE = 0.4
TIMEOUT = 60.0
VISION_TIMEOUT = 120.0

_histories: dict[int, list[dict[str, str]]] = {}
_last_activity: dict[int, float] = {}
_HISTORY_EXPIRY = 7200  # 2 часа


def _get_history(chat_id: int) -> list[dict[str, str]]:
    now = time.time()
    last = _last_activity.get(chat_id, 0)
    if now - last > _HISTORY_EXPIRY:
        _histories.pop(chat_id, None)
    _last_activity[chat_id] = now
    if chat_id not in _histories:
        _histories[chat_id] = []
    return _histories[chat_id]


def clear_history(chat_id: int) -> None:
    _histories.pop(chat_id, None)
    _last_activity.pop(chat_id, None)


def get_cco_response(
    user_message: str,
    chat_id: int,
    user_name: str = "",
    api_key: Optional[str] = None,
) -> Optional[str]:
    """Генерирует ответ CCO на вопрос команды."""
    key = api_key or os.getenv("OPENAI_API_KEY", "")
    if not key:
        logger.error("OPENAI_API_KEY not set")
        return "Ошибка: ключ OpenAI не настроен."

    try:
        from openai import OpenAI
        client = OpenAI(api_key=key, timeout=TIMEOUT)
    except ImportError:
        logger.error("openai package not installed")
        return None

    metrics = collect_all_metrics(days=7)
    system_prompt = get_system_prompt(metrics_text=metrics)

    history = _get_history(chat_id)
    content = f"[{user_name}]: {user_message}" if user_name else user_message
    history.append({"role": "user", "content": content})

    if len(history) > MAX_HISTORY:
        history[:] = history[-MAX_HISTORY:]

    messages = [{"role": "system", "content": system_prompt}] + history

    try:
        resp = client.chat.completions.create(
            model=CCO_MODEL,
            messages=messages,
            max_tokens=MAX_RESPONSE_TOKENS,
            temperature=TEMPERATURE,
        )
        answer = resp.choices[0].message.content or ""
        history.append({"role": "assistant", "content": answer})
        return answer.strip()
    except Exception as e:
        logger.exception("CCO LLM error: %s", e)
        return f"Ошибка при обращении к AI: {e}"


def generate_digest(chat_id: int, days: int = 7, api_key: Optional[str] = None) -> Optional[str]:
    """Генерирует еженедельный дайджест."""
    return get_cco_response(
        user_message=f"Сформируй еженедельный дайджест за последние {days} дней по формату из твоих инструкций.",
        chat_id=chat_id,
        user_name="Система",
        api_key=api_key,
    )


_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Модель для анализа скринов (Claude — лучше структурирует документы)
CCO_ANALYSIS_MODEL = os.getenv("CCO_ANALYSIS_MODEL", "claude-opus-4-5")
MAX_CONTEXT_CHARS = int(os.getenv("CCO_ANALYSIS_CONTEXT_CHARS", "60000"))

ANALYSIS_PROMPT = """Ты — продуктовый аналитик ГЛАВА. Тебе даны материалы из сервиса-конкурента {topic}
(скриншоты и/или текстовые заметки).
Имена файлов — это подписи/комментарии исследователя к материалам.

Проанализируй продукт и составь структурированный отчёт со следующими разделами:

## О продукте
Краткое описание, бизнес-модель, целевая аудитория, ценообразование.

## UX Flow
Пошаговое описание пользовательского пути: онбординг → использование → результат. Описывай конкретно, со ссылками на скрины.

## Сильные стороны
Что сделано хорошо, чему стоит поучиться. Конкретно, с примерами из скринов.

## Слабые стороны
Ограничения, недостатки, что можно сделать лучше.

## Гипотезы для ГЛАВА
Конкретные фичи и паттерны, которые стоит перенять или проверить.
Для каждой гипотезы: описание, приоритет (🔴 высокий / 🟠 средний / 🟢 низкий), обоснование.

## Открытые вопросы
Что важно выяснить дальше — конкретные вопросы для следующего раунда исследования.

{extra_context}

Пиши по-русски. Будь конкретным — ссылайся на то, что видишь в материалах. Формат: Markdown с заголовками ##.
"""

QUESTION_BANK_PROMPT = """Ты — Chief Product Officer для GLAVA.
Тебе дан сырой список вопросов конкурента {topic} и рубрикатор категорий.

Сделай отчёт ФОКУСИРОВАННО по question bank (а не по продукту в целом) со структурой:

## Что внутри question bank
- объем, типы вопросов, логика рубрикатора

## Качество банка
- сильные стороны
- слабые стороны
- заметные дубликаты / near-duplicates
- редакционные проблемы

## Карта рубрик и покрытие JTBD
- какие жизненные зоны покрыты хорошо
- где перекосы/дыры

## Что перенять в GLAVA
- 10-15 конкретных продуктовых решений по библиотеке вопросов
- приоритеты (🔴/🟠/🟢)

## План очистки и запуска в GLAVA
- шаги: dedupe, теги, глубина, чувствительность, локализация
- целевой формат данных (поля схемы)

## Открытые вопросы исследования
- что надо дополнительно проверить

Важно:
- Игнорируй общий обзор Storyworth, фокус только на системе вопросов.
- Пиши по-русски, структурированно, в Markdown с заголовками ##.
"""


def _read_input_texts(input_dir: Path) -> list[str]:
    """Читает все текстовые файлы из input-dir в виде блоков контекста."""
    blocks: list[str] = []
    if not input_dir.exists():
        return blocks
    for file_path in sorted(input_dir.iterdir()):
        if file_path.suffix.lower() not in {".md", ".txt"}:
            continue
        try:
            text = file_path.read_text(encoding="utf-8")[:MAX_CONTEXT_CHARS]
            blocks.append(f"Файл: {file_path.name}\n```\n{text}\n```")
        except Exception:
            logger.exception("Не удалось прочитать контекст %s", file_path)
    return blocks


def analyze_question_bank_from_input(
    topic: str,
    input_dir: Optional[Path] = None,
    api_key: Optional[str] = None,
) -> Optional[str]:
    """Анализирует question bank из текстовой input-папки (без скринов)."""
    key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
    if not key:
        return "Ошибка: ANTHROPIC_API_KEY не задан в .env"

    if input_dir is None:
        input_dir = _PROJECT_ROOT / "tasks" / "audience-research" / f"{topic}-input"

    text_blocks = _read_input_texts(input_dir)
    if not text_blocks:
        return f"В папке {input_dir} нет текстовых материалов (*.md/*.txt) для анализа question bank."

    content: list = [
        {"type": "text", "text": QUESTION_BANK_PROMPT.format(topic=topic.capitalize())},
        {"type": "text", "text": "\n\n".join(text_blocks)},
    ]

    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=key, timeout=VISION_TIMEOUT)
        resp = client.messages.create(
            model=CCO_ANALYSIS_MODEL,
            max_tokens=4000,
            messages=[{"role": "user", "content": content}],
        )
        return (resp.content[0].text or "").strip()
    except Exception as e:
        logger.exception("Question-bank analysis error: %s", e)
        return f"Ошибка анализа question bank: {e}"


def analyze_images_from_folder(
    topic: str,
    screens_folder: Optional[Path] = None,
    context_file: Optional[Path] = None,
    input_dir: Optional[Path] = None,
    api_key: Optional[str] = None,
) -> Optional[str]:
    """Анализирует скриншоты/текстовые материалы через Claude и возвращает Markdown-отчёт.

    Args:
        topic: Название продукта/темы (напр. "storyworth")
        screens_folder: Папка со скриншотами. По умолчанию tasks/audience-research/{topic}-screens/
        context_file: Файл с доп. контекстом (md/txt). По умолчанию tasks/audience-research/docs/{topic}-analysis.md
        input_dir: Папка с доп. материалами (*.md/*.txt). По умолчанию tasks/audience-research/{topic}-input/
        api_key: Anthropic API key. По умолчанию из env ANTHROPIC_API_KEY.
    """
    key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
    if not key:
        logger.error("ANTHROPIC_API_KEY not set")
        return "Ошибка: ANTHROPIC_API_KEY не задан в .env"

    if screens_folder is None:
        screens_folder = _PROJECT_ROOT / "tasks" / "audience-research" / f"{topic}-screens"
    if context_file is None:
        context_file = _PROJECT_ROOT / "tasks" / "audience-research" / "docs" / f"{topic}-analysis.md"
    if input_dir is None:
        input_dir = _PROJECT_ROOT / "tasks" / "audience-research" / f"{topic}-input"

    image_files: list[Path] = []
    if screens_folder.exists():
        image_files = sorted(
            [f for f in screens_folder.iterdir() if f.suffix.lower() in _IMAGE_EXTS]
        )
    elif screens_folder is not None:
        logger.warning("Папка со скринами не найдена: %s", screens_folder)

    logger.info(
        "Материалы для анализа: images=%d, screens=%s, input=%s, model=%s",
        len(image_files),
        screens_folder,
        input_dir,
        CCO_ANALYSIS_MODEL,
    )

    extra_context_parts: list[str] = []
    if context_file.exists():
        extra_context_parts.append(
            "Файл контекста (analysis.md):\n```\n"
            + context_file.read_text(encoding="utf-8")[:MAX_CONTEXT_CHARS]
            + "\n```"
        )

    # Дополнительные материалы исследователя:
    # tasks/audience-research/{topic}-input/*.md|*.txt
    if input_dir.exists():
        for file_path in sorted(input_dir.iterdir()):
            if file_path.suffix.lower() not in {".md", ".txt"}:
                continue
            try:
                text = file_path.read_text(encoding="utf-8")[:MAX_CONTEXT_CHARS]
                extra_context_parts.append(
                    f"Файл контекста ({file_path.name}):\n```\n{text}\n```"
                )
            except Exception:
                logger.exception("Не удалось прочитать контекст %s", file_path)

    extra_context = "\n\n".join(extra_context_parts)

    # Нужен хотя бы один источник: изображения или текстовый контекст
    if not image_files and not extra_context.strip():
        return (
            f"Не нашёл материалов для анализа.\n"
            f"- Скрины: {screens_folder}\n"
            f"- Текст: {input_dir}\n"
            f"Добавь изображения (*.jpg/*.png) или файлы *.md/*.txt и попробуй снова."
        )

    content: list = []
    for img_path in image_files:
        try:
            raw = img_path.read_bytes()
            b64 = base64.b64encode(raw).decode("utf-8")
            mime = "image/jpeg" if img_path.suffix.lower() in {".jpg", ".jpeg"} else "image/png"
            content.append({"type": "text", "text": f"Скриншот: «{img_path.stem}»"})
            content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": mime, "data": b64},
            })
        except Exception:
            logger.exception("Не удалось прочитать %s", img_path)

    content.append({
        "type": "text",
        "text": ANALYSIS_PROMPT.format(topic=topic.capitalize(), extra_context=extra_context),
    })

    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=key, timeout=VISION_TIMEOUT)
        resp = client.messages.create(
            model=CCO_ANALYSIS_MODEL,
            max_tokens=4000,
            messages=[{"role": "user", "content": content}],
        )
        return (resp.content[0].text or "").strip()
    except Exception as e:
        logger.exception("Claude Vision analysis error: %s", e)
        return f"Ошибка анализа: {e}"
