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
    Шаг 1: Иллюстратор (Claude) создаёт два image_prompt — обложка + inline.
    Шаг 2: Replicate рисует обе картинки.
    Шаг 3: Выпускающий редактор (Claude) смотрит на полный пакет (текст + визуал)
            и выносит решение о публикации.
    Возвращает {approved, comment, image_url, image_url_2}.
    """
    from smm.db_smm import get_post, update_post

    post = get_post(post_id)
    if not post:
        raise ValueError(f"Пост {post_id} не найден")

    # ── Шаг 1: иллюстратор создаёт два промпта ────────────────────────────────
    cover_prompt, inline_prompt = _illustrator_prompts(post)
    update_post(post_id, image_prompt=cover_prompt)

    # ── Шаг 2: Replicate генерирует обе картинки ──────────────────────────────
    image_url = _generate_image(post_id, cover_prompt, suffix="")
    if image_url:
        update_post(post_id, image_url=image_url)

    image_url_2 = None
    if inline_prompt:
        image_url_2 = _generate_image(post_id, inline_prompt, suffix="_2")
        if image_url_2:
            update_post(post_id, image_url_2=image_url_2)

    # ── Шаг 3: выпускающий редактор смотрит на весь пакет ─────────────────────
    approved, comment = _editorial_review(post, cover_prompt)
    status = "ready" if approved else "editor_rejected"
    update_post(post_id, editor_feedback=comment, status=status)

    logger.info(
        "Editor+Illustrator: пост_ид=%d approved=%s cover=%s inline=%s",
        post_id, approved,
        (image_url or "—")[:60],
        (image_url_2 or "—")[:60],
    )
    return {"approved": approved, "comment": comment, "image_url": image_url, "image_url_2": image_url_2}


def _editorial_review(post: dict, image_prompt: str = "") -> tuple[bool, str]:
    """Выпускающий редактор проверяет полный пакет (текст + визуал) через Claude."""
    import anthropic
    from admin import db_admin as dba

    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY не задан")

    editor_row = dba.get_prompt(EDITOR_ROLE)
    system = editor_row["prompt_text"] if editor_row else _DEFAULT_EDITOR_PROMPT

    # Контекст рубрики — редактор знает, чему должна соответствовать рубрика
    rubric_slug = post.get("rubric_slug_val") or ""
    rubric_block = ""
    if rubric_slug:
        rubric_row = dba.get_prompt(f"smm_rubric_{rubric_slug}")
        if rubric_row:
            rubric_block = (
                f"\n\nКонтекст рубрики «{post.get('rubric_name', rubric_slug)}»:\n"
                f"{rubric_row['prompt_text'][:800]}"
            )
            logger.info("Editor: рубрика %s подключена", rubric_slug)

    visual_block = (
        f"\n\nВизуальный концепт обложки (image prompt):\n{image_prompt}"
        if image_prompt else ""
    )
    user_message = (
        f"Заголовок: {post['article_title']}\n\n"
        f"Текст статьи:\n{post['article_body']}"
        f"{rubric_block}"
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


def _illustrator_prompts(post: dict) -> tuple[str, str]:
    """Иллюстратор (Claude) создаёт два image_prompt: обложка и inline-иллюстрация.

    Возвращает (cover_prompt, inline_prompt).
    Если Claude недоступен — fallback на title-based промпт.
    """
    import anthropic
    from admin import db_admin as dba

    key = os.environ.get("ANTHROPIC_API_KEY", "")
    fallback = post.get("article_title") or "warm family memoir illustration"
    if not key:
        return fallback, ""

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

    # Контекст рубрики — Лена описывает нужный тип изображений в промпте рубрики
    rubric_slug = post.get("rubric_slug_val") or ""
    rubric_context = ""
    if rubric_slug:
        rubric_row = dba.get_prompt(f"smm_rubric_{rubric_slug}")
        if rubric_row:
            rubric_context = (
                f"\n\nТипы изображений для рубрики «{post.get('rubric_name', rubric_slug)}»:\n"
                f"{rubric_row['prompt_text'][:600]}"
            )
            logger.info("Illustrator: рубрика %s подключена", rubric_slug)

    # Контекст площадки/формата
    pf_slug = post.get("pf_slug") or ""
    pf_context = ""
    if pf_slug:
        pf_row = dba.get_prompt(f"smm_pf_{pf_slug}")
        if pf_row:
            pf_context = (
                f"\n\nТребования площадки {post.get('pf_platform','')} / {post.get('pf_format','')}:\n"
                f"{pf_row['prompt_text'][:400]}"
            )

    body_preview = (post.get("article_body") or "")[:800]
    user_message = (
        f"Заголовок: {post['article_title']}\n\n"
        f"Текст статьи (с маркером [ИЛЛЮСТРАЦИЯ] где нужна иллюстрация внутри):\n{body_preview}"
        f"{rubric_context}"
        f"{pf_context}\n\n"
        "Создай два промпта для генерации изображений через Replicate (flux-schnell). "
        "Верни ТОЛЬКО JSON без пояснений:\n"
        '{"cover": "prompt for cover image in English", '
        '"inline": "prompt for inline image at [ИЛЛЮСТРАЦИЯ] marker in English"}'
    )

    try:
        client = anthropic.Anthropic(api_key=key)
        resp = client.messages.create(
            model=os.environ.get("SMM_CLAUDE_MODEL", "claude-haiku-4-5-20251001"),
            max_tokens=400,
            messages=[{"role": "user", "content": system + "\n\n---\n\n" + user_message}],
        )
        raw = resp.content[0].text.strip()
        logger.info("Illustrator: raw response пост_ид=%d: %r", post["id"], raw[:120])
        data = _parse_json_obj(raw)
        cover = (data.get("cover") or "").strip() or fallback
        inline = (data.get("inline") or "").strip()
        return cover, inline
    except Exception as e:
        logger.error("Illustrator: ошибка пост_ид=%d: %s", post["id"], e)
        return fallback, ""


def _illustrator_prompt(post: dict) -> str:
    """Обёртка для обратной совместимости (используется в regen-image)."""
    cover, _ = _illustrator_prompts(post)
    return cover


def _generate_image(post_id: int, image_prompt: str, suffix: str = "") -> Optional[str]:
    """Генерирует картинку через Replicate и сохраняет в SMM_IMAGES_DIR.

    suffix="" → post_{id}.webp (обложка)
    suffix="_2" → post_{id}_2.webp (inline)
    """
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from replicate_client import generate_cover_image

    images_dir = Path(os.environ.get("SMM_IMAGES_DIR", "/tmp/smm_images"))
    images_dir.mkdir(parents=True, exist_ok=True)

    try:
        image_bytes = generate_cover_image(
            visual_style=image_prompt,
            character_name="GLAVA",
            raw=True,  # SMM: промпт иллюстратора передаётся как есть, без book-cover суффикса
        )
        if not image_bytes:
            logger.warning("Illustrator: Replicate вернул None для пост_ид=%d suffix=%r", post_id, suffix)
            return None
        filename = f"post_{post_id}{suffix}.webp"
        filepath = images_dir / filename
        filepath.write_bytes(image_bytes)
        logger.info("Illustrator: изображение сохранено %s (%d байт)", filepath, len(image_bytes))
        return f"/smm/image/{filename}"
    except Exception as e:
        logger.error("Illustrator: ошибка генерации пост_ид=%d suffix=%r: %s", post_id, suffix, e)
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
