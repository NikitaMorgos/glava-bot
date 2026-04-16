"""
SMM Scout v2 — генерирует контент-план через Claude.
Источники: стратегия + скаут + площадки_форматы + рубрики + отзывы + идеи.
"""
import json
import logging
import os
import re
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
        get_recent_reviews, get_recent_topic_titles, set_plan_raw,
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

    existing_titles = get_recent_topic_titles(limit=800, platform_name=platform_name_filter)
    existing_block = ""
    if existing_titles:
        sample = "\n".join(f"— {t[:120]}" for t in existing_titles[:200])
        existing_block = (
            "\n\nУже использованные темы/заголовки (их повторять нельзя, даже близкие формулировки):\n"
            + sample
        )

    user_message = (
        f"Стратегия GLAVA:\n{strategy_text}"
        f"{pf_block}"
        f"{rubrics_block}"
        f"{reviews_block}"
        f"{existing_block}"
        f"{manual_block}"
        f"\n\nСгенерируй ровно {num_topics} тем для постов."
        "\nКритично: заголовки должны быть разнообразными и НЕ пересекаться по смыслу."
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
    topics = _enforce_uniqueness(topics, existing_titles)

    # Если после чистки тем стало меньше нужного количества — добираем
    if len(topics) < num_topics:
        missing = num_topics - len(topics)
        extra = _generate_extra_topics(
            client=client,
            scout_system=scout_system,
            strategy_text=strategy_text,
            pf_block=pf_block,
            rubrics_block=rubrics_block,
            reviews_block=reviews_block,
            manual_block=manual_block,
            existing_titles=existing_titles + [t.get("topic", "") for t in topics],
            num_topics=missing,
        )
        topics.extend(_enforce_uniqueness(extra, existing_titles + [t.get("topic", "") for t in topics]))

    topics = topics[:num_topics]

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


def _norm_topic(text: str) -> str:
    t = (text or "").lower().strip()
    t = re.sub(r"[^\w\s]", " ", t)
    t = re.sub(r"\s+", " ", t)
    return t


def _enforce_uniqueness(topics: list[dict], existing_titles: list[str]) -> list[dict]:
    """Удаляет дубли внутри партии и относительно истории."""
    seen = {_norm_topic(x) for x in existing_titles if x}
    out: list[dict] = []
    for item in topics:
        topic = (item.get("topic") or "").strip()
        key = _norm_topic(topic)
        if not topic or not key:
            continue
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def _generate_extra_topics(
    client,
    scout_system: str,
    strategy_text: str,
    pf_block: str,
    rubrics_block: str,
    reviews_block: str,
    manual_block: str,
    existing_titles: list[str],
    num_topics: int,
) -> list[dict]:
    """Догенерация недостающих тем, если часть была отброшена как дубли."""
    if num_topics <= 0:
        return []
    exclude = "\n".join(f"— {x[:120]}" for x in existing_titles[:300] if x)
    user_message = (
        f"Стратегия GLAVA:\n{strategy_text}"
        f"{pf_block}"
        f"{rubrics_block}"
        f"{reviews_block}"
        f"{manual_block}"
        "\n\nНиже список тем, которые уже заняты. Их нельзя повторять ни дословно, ни по смыслу:\n"
        f"{exclude}"
        f"\n\nСгенерируй {num_topics} НОВЫХ тем, без повторов."
        "\nВерни JSON-массив без пояснений:"
        '\n[{"topic": "Название", "angle": "Угол подачи", "format": "тип", '
        '"rubric": "slug рубрики", "platform_format": "slug площадки_формата"}]'
    )
    resp = client.messages.create(
        model=os.environ.get("SMM_CLAUDE_MODEL", "claude-haiku-4-5-20251001"),
        max_tokens=1200,
        messages=[{"role": "user", "content": scout_system + "\n\n---\n\n" + user_message}],
    )
    return _parse_json_list(resp.content[0].text.strip())


def _default_strategy() -> str:
    return (
        "GLAVA — сервис создания семейных книг-биографий.\n"
        "Целевая аудитория: люди 35–65 лет, хотят сохранить историю своей семьи.\n"
        "Ценности: память, тепло, семья, наследие.\n"
        "Тональность: тёплая, личная, с уважением к старшему поколению.\n"
        "Цель контента: вдохновить читателя на создание семейной книги."
    )
