"""
SMM Scout — генерирует контент-план через Claude.
Источники тем: стратегия + промпт + отзывы из БД + идеи от Лены.
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
Твоя задача: генерировать разнообразные, вовлекающие темы для контент-плана на Яндекс Дзен.

Принципы:
— Темы должны быть близки аудитории 35–65 лет
— Тематически связаны с памятью, семьёй, историями жизни
— Разнообразие форматов: практические советы, истории, вопросы-размышления, бэкстейдж
— Используй реальные инсайты: отзывы клиентов, сезонность, инфоповоды
"""


def generate_content_plan(
    plan_id: int,
    manual_ideas: str = "",
    num_topics: int = 5,
) -> list[dict]:
    """
    Генерирует контент-план через Claude.
    Записывает темы в БД (smm_content_plans.raw_plan + создаёт smm_posts).
    Возвращает список тем: [{topic, angle, format}].
    """
    import anthropic
    from admin import db_admin as dba
    from smm.db_smm import create_post, get_recent_reviews, set_plan_raw

    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY не задан")

    strategy_row = dba.get_prompt(STRATEGY_ROLE)
    scout_row = dba.get_prompt(SCOUT_ROLE)

    strategy_text = strategy_row["prompt_text"] if strategy_row else _default_strategy()
    scout_system = scout_row["prompt_text"] if scout_row else _DEFAULT_SCOUT_PROMPT

    reviews = get_recent_reviews(10)
    reviews_block = ""
    if reviews:
        snippets = [f"— {r[:250]}" for r in reviews[:5]]
        reviews_block = "\n\nОтзывы клиентов (для вдохновения):\n" + "\n".join(snippets)

    manual_block = ""
    if manual_ideas.strip():
        manual_block = f"\n\nИдеи от редактора:\n{manual_ideas.strip()}"

    user_message = (
        f"Стратегия GLAVA:\n{strategy_text}"
        f"{reviews_block}"
        f"{manual_block}"
        f"\n\nСгенерируй ровно {num_topics} тем для постов."
        "\nВерни JSON-массив без пояснений:"
        '\n[{"topic": "Название темы", "angle": "Угол подачи", "format": "статья|список|история"}]'
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
    for item in topics:
        topic_text = item.get("topic", "")
        if topic_text:
            create_post(plan_id, topic_text)

    logger.info("Scout: план_ид=%d создано %d тем", plan_id, len(topics))
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
