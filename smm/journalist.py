"""
SMM Journalist — пишет текст статьи через GPT-4o.
"""
import logging
import os

logger = logging.getLogger(__name__)

JOURNALIST_ROLE = "smm_journalist"

_DEFAULT_JOURNALIST_PROMPT = """\
Ты профессиональный копирайтер для GLAVA — сервиса создания семейных книг-биографий.
Пишешь тёплые, личные статьи для Яндекс Дзен.

Стиль: живой, искренний, с конкретными деталями. Без штампов и канцелярита.
Аудитория: 35–65 лет, ценят семью и память о близких.
Формат Дзен: заголовок + лид + 2–4 раздела с подзаголовками + заключение с призывом.
Объём: 600–1000 слов.
"""


def write_article(post_id: int) -> dict:
    """
    Пишет статью для поста через GPT-4o.
    Обновляет smm_posts: article_title, article_body, status='journalist_done'.
    Возвращает {title, body}.
    """
    from openai import OpenAI
    from admin import db_admin as dba
    from smm.db_smm import get_post, update_post

    key = os.environ.get("OPENAI_API_KEY", "")
    if not key:
        raise RuntimeError("OPENAI_API_KEY не задан")

    post = get_post(post_id)
    if not post:
        raise ValueError(f"Пост {post_id} не найден")

    journalist_row = dba.get_prompt(JOURNALIST_ROLE)
    system = journalist_row["prompt_text"] if journalist_row else _DEFAULT_JOURNALIST_PROMPT

    user_message = (
        f"Тема статьи: «{post['topic']}»\n\n"
        "Первая строка — заголовок, начинается с «# ».\n"
        "Дальше — только текст в твоём стиле, без жёстких шаблонов структуры."
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

    update_post(post_id, article_title=title, article_body=body, status="journalist_done")
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
    # No H1 found — use first non-empty line as title
    for i, line in enumerate(lines):
        if line.strip():
            return line.strip(), "\n".join(lines[i + 1:]).strip()
    return "Без заголовка", text
