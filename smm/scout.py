"""
SMM Scout v2 — генерирует контент-план через Claude.
Источники: стратегия + скаут + площадки_форматы + рубрики + отзывы + идеи.
"""
import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

SCOUT_ROLE = "smm_scout"
STRATEGY_ROLE = "smm_strategy"

_DEFAULT_SCOUT_PROMPT = """\
Ты опытный SMM-менеджер для GLAVA — сервиса создания семейных книг-биографий.
Твоя задача: генерировать разнообразные, вовлекающие темы для контент-плана.

Принципы:
— Темы должны быть близки аудитории 35–65 лет
— Тематически связаны с памятью, семьёй, историями жизни
— Разнообразие форматов: практические советы, истории, вопросы-размышления, бэкстейдж
— Используй реальные инсайты: отзывы клиентов, сезонность, инфоповоды
— Распределяй темы по рубрикам и площадкам_форматам
"""


def generate_content_plan(
    plan_id: int,
    manual_ideas: str = "",
    num_topics: int = 5,
    platform_slug: Optional[str] = None,
    platform_name_filter: Optional[str] = None,
) -> list[dict]:
    """
    Генерирует контент-план через Claude.
    Использует: стратегия + скаут + площадки_форматы + рубрики + отзывы + идеи.
    """
    import anthropic
    from admin import db_admin as dba
    from smm.db_smm import (
        create_post, get_active_platform_formats, get_active_rubrics,
        get_recent_reviews, set_plan_raw,
    )

    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY не задан")

    strategy_row = dba.get_prompt(STRATEGY_ROLE)
    scout_row = dba.get_prompt(SCOUT_ROLE)

    strategy_text = strategy_row["prompt_text"] if strategy_row else _default_strategy()
    scout_system = scout_row["prompt_text"] if scout_row else _DEFAULT_SCOUT_PROMPT

    # Площадки_Форматы (v2)
    pf_list = get_active_platform_formats(platform_name=platform_name_filter)
    pf_block = ""
    if pf_list:
        pf_lines = []
        for pf in pf_list:
            pf_prompt_row = dba.get_prompt(f"smm_pf_{pf['slug']}")
            desc = pf_prompt_row["prompt_text"] if pf_prompt_row else ""
            label = f"{pf['platform_name']} / {pf['format_name']}"
            if desc:
                pf_lines.append(f"— {label} (slug: {pf['slug']}): {desc}")
            else:
                pf_lines.append(f"— {label} (slug: {pf['slug']})")
        pf_block = "\n\nДоступные площадки и форматы:\n" + "\n".join(pf_lines)

    # Legacy: промпт площадки (если нет v2 данных, берём старый промпт)
    if not pf_block and platform_slug:
        platform_row = dba.get_prompt(f"smm_platform_{platform_slug}")
        if platform_row:
            pf_block = f"\n\nТребования площадки ({platform_slug}):\n{platform_row['prompt_text']}"

    # Рубрики
    rubrics = get_active_rubrics()
    rubrics_block = ""
    if rubrics:
        rubric_lines = []
        for r in rubrics:
            rubric_row = dba.get_prompt(f"smm_rubric_{r['slug']}")
            if rubric_row:
                rubric_lines.append(f"— {r['name']} (slug: {r['slug']}): {rubric_row['prompt_text']}")
            else:
                rubric_lines.append(f"— {r['name']} (slug: {r['slug']})")
        rubrics_block = "\n\nАктивные рубрики (распредели темы по рубрикам):\n" + "\n".join(rubric_lines)

    # Отзывы
    reviews = get_recent_reviews(10)
    reviews_block = ""
    if reviews:
        snippets = [f"— {r[:250]}" for r in reviews[:5]]
        reviews_block = "\n\nОтзывы клиентов (для вдохновения):\n" + "\n".join(snippets)

    # Идеи
    manual_block = ""
    if manual_ideas.strip():
        manual_block = f"\n\nИдеи от редактора:\n{manual_ideas.strip()}"

    user_message = (
        f"Стратегия GLAVA:\n{strategy_text}"
        f"{pf_block}"
        f"{rubrics_block}"
        f"{reviews_block}"
        f"{manual_block}"
        f"\n\nСгенерируй ровно {num_topics} тем для постов."
        "\nКаждая тема должна указывать рубрику (rubric) и площадку_формат (platform_format)."
        "\nВерни JSON-массив без пояснений:"
        '\n[{"topic": "Название", "angle": "Угол подачи", "format": "тип", '
        '"rubric": "slug рубрики", "platform_format": "slug площадки_формата"}]'
    )

    client = anthropic.Anthropic(api_key=key)
    resp = client.messages.create(
        model=os.environ.get("SMM_CLAUDE_MODEL", "claude-haiku-4-5-20251001"),
        max_tokens=2000,
        messages=[
            {"role": "user", "content": scout_system + "\n\n---\n\n" + user_message},
        ],
    )

    raw_text = resp.content[0].text.strip()
    topics = _parse_json_list(raw_text)

    set_plan_raw(plan_id, topics)

    channel = platform_name_filter or platform_slug or "dzen"
    for item in topics:
        topic_text = item.get("topic", "")
        if topic_text:
            create_post(
                plan_id,
                topic_text,
                channel=channel,
                rubric_slug=item.get("rubric", ""),
                platform_format_slug=item.get("platform_format", ""),
            )

    logger.info(
        "Scout v2: план_ид=%d filter=%s создано %d тем",
        plan_id, platform_name_filter or platform_slug or "—", len(topics),
    )
    return topics


def _parse_json_list(text: str) -> list[dict]:
    start = text.find("[")
    end = text.rfind("]") + 1
    if start == -1 or end == 0:
        raise ValueError(f"Scout не вернул корректный JSON-массив: {text[:300]}")
    return json.loads(text[start:end])


def _default_strategy() -> str:
    return (
        "GLAVA — сервис создания семейных книг-биографий.\n"
        "Целевая аудитория: люди 35–65 лет, хотят сохранить историю своей семьи.\n"
        "Ценности: память, тепло, семья, наследие.\n"
        "Тональность: тёплая, личная, с уважением к старшему поколению.\n"
        "Цель контента: вдохновить читателя на создание семейной книги."
    )
