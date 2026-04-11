"""
SMM Editor — проверяет текст (Claude).
SMM Illustrator — генерирует визуальный концепт и обложку (Claude + Replicate).
"""
import json
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

EDITOR_ROLE      = "smm_editor"
ILLUSTRATOR_ROLE = "smm_illustrator"

_DEFAULT_EDITOR_PROMPT = """\
Ты главный редактор GLAVA. Проверяешь статьи перед публикацией.

Правило одобрения: одобряй статью (approved=true) если она:
— По теме: семья, память, поколения, история жизни
— Написана на русском языке без грубых ошибок
— Не содержит оскорблений, фейков, рекламы чужих брендов

Отклоняй (approved=false) только если статья явно нарушает ценности GLAVA
(агрессия, депрессивный тон, полностью не по теме) или содержит фактические ошибки.
Наличие клише и неидеальный стиль — НЕ повод для отклонения, оставь замечание в comment.

В comment: одна-две конкретных рекомендации по улучшению.

Верни только JSON без пояснений:
{"approved": true/false, "comment": "..."}
"""

_DEFAULT_ILLUSTRATOR_PROMPT = """\
Ты иллюстратор для GLAVA — сервиса создания семейных книг-биографий.
Твоя задача: по тексту статьи создать визуальную концепцию для обложки.

Сформируй промпт для генерации изображения через Replicate (модель flux-schnell).

Требования к промпту:
— На английском языке
— Конкретная сцена: кто изображён, что происходит, детали окружения
— Стиль: nana-banana illustration style, warm editorial, book cover aesthetic
— Палитра: тёплые тона — золотой, кремовый, терракотовый, глубокий бордо
— Без текста и надписей на изображении
— Атмосфера: уютная, ностальгическая, семейная

Верни только строку промпта, без пояснений и JSON.
"""


def review_and_generate_image(post_id: int) -> dict:
    """
    Шаг 1: Редактор (Claude) проверяет текст → approved/comment.
    Шаг 2: Иллюстратор (Claude) создаёт image_prompt → Replicate генерирует картинку.
    Возвращает {approved, comment, image_url}.
    """
    from smm.db_smm import get_post, update_post

    post = get_post(post_id)
    if not post:
        raise ValueError(f"Пост {post_id} не найден")

    # ── Шаг 1: редакторская проверка ──────────────────────────────────────────
    approved, comment = _editorial_review(post)
    update_post(post_id, editor_feedback=comment)

    # ── Шаг 2: иллюстратор создаёт image_prompt ───────────────────────────────
    image_prompt = _illustrator_prompt(post)
    update_post(post_id, image_prompt=image_prompt)

    # ── Шаг 3: Replicate генерирует картинку ──────────────────────────────────
    image_url = _generate_image(post_id, image_prompt)
    status = "ready" if approved else "editor_rejected"
    update_post(post_id, status=status, image_url=image_url or "")

    logger.info(
        "Editor+Illustrator: пост_ид=%d approved=%s image=%s",
        post_id, approved, (image_url or "—")[:80],
    )
    return {"approved": approved, "comment": comment, "image_url": image_url}


def _editorial_review(post: dict) -> tuple[bool, str]:
    """Редактор проверяет текст через Claude, возвращает (approved, comment)."""
    import anthropic
    from admin import db_admin as dba

    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY не задан")

    editor_row = dba.get_prompt(EDITOR_ROLE)
    system = editor_row["prompt_text"] if editor_row else _DEFAULT_EDITOR_PROMPT

    user_message = (
        f"Статья:\n\n# {post['article_title']}\n\n{post['article_body']}\n\n"
        "Проверь текст и верни только JSON без пояснений:\n"
        '{"approved": true/false, "comment": "..."}'
    )

    client = anthropic.Anthropic(api_key=key)
    resp = client.messages.create(
        model=os.environ.get("SMM_CLAUDE_MODEL", "claude-haiku-4-5-20251001"),
        max_tokens=400,
        messages=[{"role": "user", "content": system + "\n\n---\n\n" + user_message}],
    )

    result = _parse_json_obj(resp.content[0].text.strip())
    return result.get("approved", True), result.get("comment", "")


def _illustrator_prompt(post: dict) -> str:
    """Иллюстратор создаёт image_prompt через Claude."""
    import anthropic
    from admin import db_admin as dba

    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        return post.get("article_title") or "warm family memoir illustration"

    illustrator_row = dba.get_prompt(ILLUSTRATOR_ROLE)
    system = illustrator_row["prompt_text"] if illustrator_row else _DEFAULT_ILLUSTRATOR_PROMPT

    # Передаём заголовок + первые ~600 символов тела — достаточно для визуала
    body_preview = (post.get("article_body") or "")[:600]
    user_message = (
        f"Заголовок: {post['article_title']}\n\n"
        f"Фрагмент текста:\n{body_preview}\n\n"
        "Создай промпт для иллюстрации."
    )

    try:
        client = anthropic.Anthropic(api_key=key)
        resp = client.messages.create(
            model=os.environ.get("SMM_CLAUDE_MODEL", "claude-haiku-4-5-20251001"),
            max_tokens=300,
            messages=[{"role": "user", "content": system + "\n\n---\n\n" + user_message}],
        )
        prompt = resp.content[0].text.strip()
        logger.info("Illustrator: пост_ид=%d prompt=%r", post["id"], prompt[:80])
        return prompt or (post.get("article_title") or "family memoir illustration")
    except Exception as e:
        logger.error("Illustrator: ошибка пост_ид=%d: %s", post["id"], e)
        return post.get("article_title") or "family memoir illustration"


def _generate_image(post_id: int, image_prompt: str) -> Optional[str]:
    """Генерирует обложку через Replicate и сохраняет в SMM_IMAGES_DIR."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from replicate_client import generate_cover_image

    images_dir = Path(os.environ.get("SMM_IMAGES_DIR", "/tmp/smm_images"))
    images_dir.mkdir(parents=True, exist_ok=True)

    try:
        image_bytes = generate_cover_image(
            visual_style=image_prompt,
            character_name="GLAVA",
        )
        if not image_bytes:
            logger.warning("Illustrator: Replicate вернул None для пост_ид=%d", post_id)
            return None
        filename = f"post_{post_id}.webp"
        filepath = images_dir / filename
        filepath.write_bytes(image_bytes)
        logger.info("Illustrator: изображение сохранено %s (%d байт)", filepath, len(image_bytes))
        return f"/smm/image/{filename}"
    except Exception as e:
        logger.error("Illustrator: ошибка генерации пост_ид=%d: %s", post_id, e)
        return None


def _parse_json_obj(text: str) -> dict:
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end == 0:
        logger.warning("Editor: не удалось распарсить JSON: %s", text[:200])
        return {"approved": True, "comment": ""}
    try:
        return json.loads(text[start:end])
    except json.JSONDecodeError:
        logger.warning("Editor: ошибка парсинга JSON: %s", text[start:end][:200])
        return {"approved": True, "comment": text}
