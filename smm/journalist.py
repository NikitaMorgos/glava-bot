"""
SMM Journalist v2 — пишет текст статьи через GPT-4o.
Маршрутизация: по рубрике + площадке_формату подбирается журналист.
Контекст: промпт журналиста (system) + тема + промпт рубрики + описание формата (user).
"""
import logging
import os

logger = logging.getLogger(__name__)

_DEFAULT_JOURNALIST_PROMPT = """\
Ты профессиональный копирайтер для GLAVA — сервиса создания семейных книг-биографий.
Пишешь тёплые, личные статьи.

Стиль: живой, искренний, с конкретными деталями. Без штампов и канцелярита.
Аудитория: 35–65 лет, ценят семью и память о близких.
Объём: 600–1000 слов.
"""


def write_article(post_id: int) -> dict:
    """
    1. Берёт пост из БД (rubric_id, platform_format_id).
    2. Ищет журналиста через find_journalist(rubric, pf).
    3. Собирает контекст: промпт журналиста + промпт рубрики + описание формата.
    4. GPT-4o пишет текст.
    5. Записывает: article_title, article_body, journalist_id, status='journalist_done'.
    """
    from openai import OpenAI
    from admin import db_admin as dba
    from smm.db_smm import find_journalist, get_post, update_post

    key = os.environ.get("OPENAI_API_KEY", "")
    if not key:
        raise RuntimeError("OPENAI_API_KEY не задан")

    post = get_post(post_id)
    if not post:
        raise ValueError(f"Пост {post_id} не найден")

    # ── Маршрутизация: подбираем журналиста ────────────────────────────────
    journalist = find_journalist(
        rubric_id=post.get("rubric_id"),
        platform_format_id=post.get("platform_format_id"),
    )

    if journalist:
        prompt_key = f"smm_journalist_{journalist['slug']}"
        j_row = dba.get_prompt(prompt_key)
        system = j_row["prompt_text"] if j_row else _DEFAULT_JOURNALIST_PROMPT
        journalist_id = journalist["id"]
        logger.info(
            "Journalist routing: пост_ид=%d → %s (id=%d)",
            post_id, journalist["name"], journalist_id,
        )
    else:
        # Fallback: legacy единый промпт smm_journalist
        legacy_row = dba.get_prompt("smm_journalist")
        system = legacy_row["prompt_text"] if legacy_row else _DEFAULT_JOURNALIST_PROMPT
        journalist_id = None
        logger.info("Journalist routing: пост_ид=%d → fallback (нет назначений)", post_id)

    # ── Контекст рубрики ──────────────────────────────────────────────────
    rubric_context = ""
    rubric_slug = post.get("rubric_slug_val") or ""
    if rubric_slug:
        rubric_row = dba.get_prompt(f"smm_rubric_{rubric_slug}")
        if rubric_row:
            rubric_context = f"\n\nТребования рубрики «{post.get('rubric_name', rubric_slug)}»:\n{rubric_row['prompt_text']}"

    # ── Контекст площадки_формата ─────────────────────────────────────────
    pf_context = ""
    pf_slug = post.get("pf_slug") or ""
    if pf_slug:
        pf_row = dba.get_prompt(f"smm_pf_{pf_slug}")
        if pf_row:
            pf_name = f"{post.get('pf_platform', '')} / {post.get('pf_format', '')}"
            pf_context = f"\n\nТребования площадки и формата «{pf_name}»:\n{pf_row['prompt_text']}"

    user_message = (
        f"Тема статьи: «{post['topic']}»"
        f"{rubric_context}"
        f"{pf_context}\n\n"
        "Первая строка — заголовок, начинается с «# ».\n"
        "Дальше — только текст в твоём стиле."
    )

    client = OpenAI(api_key=key, timeout=120)
    resp = client.chat.completions.create(
        model=os.environ.get("SMM_GPT_MODEL", "gpt-4o"),
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_message},
        ],
        max_tokens=2500,
        temperature=0.7,
    )

    full_text = (resp.choices[0].message.content or "").strip()
    title, body = _split_title_body(full_text)

    update_fields = dict(
        article_title=title,
        article_body=body,
        status="journalist_done",
    )
    if journalist_id:
        update_fields["journalist_id"] = journalist_id

    update_post(post_id, **update_fields)
    logger.info("Journalist: пост_ид=%d заголовок=%r (%d симв)", post_id, title[:60], len(body))
    return {"title": title, "body": body}


def _split_title_body(text: str) -> tuple[str, str]:
    """Извлекает заголовок (первая строка # ...) и остаток текста."""
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if line.startswith("# "):
            title = line[2:].strip()
            body = "\n".join(lines[i + 1:]).strip()
            return title, body
    for i, line in enumerate(lines):
        if line.strip():
            return line.strip(), "\n".join(lines[i + 1:]).strip()
    return "Без заголовка", text
