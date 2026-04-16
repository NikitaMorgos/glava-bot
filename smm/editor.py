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
Ты выпускающий редактор GLAVA. Ты принимаешь финальное решение о публикации,
глядя на полностью собранный материал: заголовок, текст статьи и визуальный концепт обложки.

Оцени пакет как единое целое по трём критериям:

1. ТЕКСТ: по теме (семья, память, поколения), грамотный русский, нет оскорблений/фейков/рекламы.
2. ЕДИНСТВО: визуальный концепт соответствует теме и тональности текста.
3. ЦЕННОСТИ GLAVA: тёплый, уважительный, жизнеутверждающий тон.

Рекомендуй к публикации (approved=true) если материал проходит по всем трём критериям.
Отклоняй (approved=false) только при явных нарушениях: агрессия, депрессивный тон,
полное несоответствие теме, фактические ошибки, разрыв между текстом и визуалом.

Клише и неидеальный стиль — НЕ повод для отклонения. Оставь комментарий с рекомендациями.
В comment: одна-две конкретных правки, если нужны. Если всё хорошо — напиши «Рекомендован к публикации».

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
    Шаг 1: Иллюстратор (Claude) создаёт image_prompt → Replicate рисует обложку.
    Шаг 2: Выпускающий редактор (Claude) смотрит на полный пакет (текст + визуал)
            и выносит решение о публикации.
    Возвращает {approved, comment, image_url}.
    """
    from smm.db_smm import get_post, update_post

    post = get_post(post_id)
    if not post:
        raise ValueError(f"Пост {post_id} не найден")

    # ── Шаг 1: иллюстратор создаёт image_prompt ───────────────────────────────
    image_prompt = _illustrator_prompt(post)
    update_post(post_id, image_prompt=image_prompt)

    # ── Шаг 2: Replicate генерирует картинку ──────────────────────────────────
    image_url = _generate_image(post_id, image_prompt)
    if image_url:
        update_post(post_id, image_url=image_url)

    # ── Шаг 3: выпускающий редактор смотрит на весь пакет ─────────────────────
    approved, comment = _editorial_review(post, image_prompt)
    status = "ready" if approved else "editor_rejected"
    update_post(post_id, editor_feedback=comment, status=status)

    logger.info(
        "Editor+Illustrator: пост_ид=%d approved=%s image=%s",
        post_id, approved, (image_url or "—")[:80],
    )
    return {"approved": approved, "comment": comment, "image_url": image_url}


def _editorial_review(post: dict, image_prompt: str = "") -> tuple[bool, str]:
    """Выпускающий редактор проверяет полный пакет (текст + визуал) через Claude."""
    import anthropic
    from admin import db_admin as dba

    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY не задан")

    editor_row = dba.get_prompt(EDITOR_ROLE)
    system = editor_row["prompt_text"] if editor_row else _DEFAULT_EDITOR_PROMPT

    visual_block = (
        f"\n\nВизуальный концепт обложки (image prompt):\n{image_prompt}"
        if image_prompt else ""
    )
    user_message = (
        f"Заголовок: {post['article_title']}\n\n"
        f"Текст статьи:\n{post['article_body']}"
        f"{visual_block}\n\n"
        "Оцени полный пакет и верни только JSON без пояснений:\n"
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

    row_primary = dba.get_prompt(ILLUSTRATOR_ROLE)
    row_alias = dba.get_prompt("smm_illustrations")
    illustrator_row = row_primary or row_alias
    system = illustrator_row["prompt_text"] if illustrator_row else _DEFAULT_ILLUSTRATOR_PROMPT
    logger.info(
        "Illustrator prompt source: %s",
        ILLUSTRATOR_ROLE if row_primary else (
            "smm_illustrations" if row_alias else "default_in_code"
        ),
    )

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
