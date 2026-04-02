"""
SMM Editor — проверяет текст (Claude) и генерирует обложку (Replicate).
"""
import json
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

EDITOR_ROLE = "smm_editor"

_DEFAULT_EDITOR_PROMPT = """\
Ты главный редактор GLAVA. Проверяешь статьи перед публикацией.

Критерии:
— Соответствие ценностям GLAVA: семья, память, тепло, наследие
— Грамотный русский язык, живой стиль без штампов
— Подходящий объём (600–1000 слов)
— Тон: уважительный к старшему поколению, не поучительный

Для промпта обложки: опиши визуальную сцену — тёплую, семейную, соответствующую теме статьи.
Стиль: book cover illustration, warm color palette, editorial photography style.
"""


def review_and_generate_image(post_id: int) -> dict:
    """
    Редактор проверяет текст через Claude, формирует image_prompt,
    генерирует изображение через Replicate.
    Обновляет пост: editor_feedback, image_prompt, image_url, status.
    Возвращает {approved, comment, image_url}.
    """
    import anthropic
    from admin import db_admin as dba
    from smm.db_smm import get_post, update_post

    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY не задан")

    post = get_post(post_id)
    if not post:
        raise ValueError(f"Пост {post_id} не найден")

    editor_row = dba.get_prompt(EDITOR_ROLE)
    system = editor_row["prompt_text"] if editor_row else _DEFAULT_EDITOR_PROMPT

    user_message = (
        f"Статья:\n\n# {post['article_title']}\n\n{post['article_body']}\n\n"
        "Задачи:\n"
        "1. Проверь текст по критериям\n"
        "2. Сформируй промпт для генерации обложки (на английском, для Replicate flux-schnell)\n\n"
        "Верни только JSON (без пояснений):\n"
        '{"approved": true/false, "comment": "...", "image_prompt": "..."}'
    )

    client = anthropic.Anthropic(api_key=key)
    resp = client.messages.create(
        model=os.environ.get("SMM_CLAUDE_MODEL", "claude-haiku-4-5-20251001"),
        max_tokens=800,
        messages=[
            {"role": "user", "content": system + "\n\n---\n\n" + user_message},
        ],
    )

    raw = resp.content[0].text.strip()
    result = _parse_json_obj(raw)
    approved: bool = result.get("approved", True)
    comment: str = result.get("comment", "")
    image_prompt: str = result.get("image_prompt") or post["article_title"] or "family memoir illustration"

    update_post(post_id, editor_feedback=comment, image_prompt=image_prompt)

    image_url = _generate_image(post_id, image_prompt)
    status = "ready" if approved else "editor_rejected"
    update_post(post_id, status=status, image_url=image_url or "")

    logger.info(
        "Editor: пост_ид=%d approved=%s image_url=%s",
        post_id, approved, (image_url or "—")[:80],
    )
    return {"approved": approved, "comment": comment, "image_url": image_url}


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
            logger.warning("Editor: Replicate вернул None для пост_ид=%d", post_id)
            return None
        filename = f"post_{post_id}.webp"
        filepath = images_dir / filename
        filepath.write_bytes(image_bytes)
        logger.info("Editor: изображение сохранено %s (%d байт)", filepath, len(image_bytes))
        return f"/smm/image/{filename}"
    except Exception as e:
        logger.error("Editor: ошибка генерации изображения пост_ид=%d: %s", post_id, e)
        return None


def _parse_json_obj(text: str) -> dict:
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end == 0:
        logger.warning("Editor: не удалось распарсить JSON: %s", text[:200])
        return {"approved": True, "comment": "", "image_prompt": ""}
    try:
        return json.loads(text[start:end])
    except json.JSONDecodeError:
        logger.warning("Editor: ошибка парсинга JSON: %s", text[start:end][:200])
        return {"approved": True, "comment": text, "image_prompt": ""}
