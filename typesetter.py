# -*- coding: utf-8 -*-
"""
Верстальщик PDF: текст (биография от OpenAI) + фото пользователя → PDF по образцу.
Использует Claude (Anthropic) для выбора структуры и подписей к фото, reportlab — для сборки PDF.
"""

import base64
import json
import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Описание образца по умолчанию (семейная книга)
DEFAULT_TEMPLATE_DESCRIPTION = """
Образец: семейная книга в тёплом, аккуратном стиле.
- Обложка/титул не нужен в JSON — первый блок текста может быть заголовком (имя человека).
- Чередуй блоки текста и фото: после 1–2 абзацев можно вставить фото с подписью.
- Подписи к фото — короткие (1 строка), от первого лица или нейтрально.
- Шрифт и отступы задаются при вёрстке; тебе нужно вернуть только структуру и подписи.
"""


def _load_images_for_claude(image_paths: list[str], max_size_mpx: float = 1.0) -> list[dict]:
    """Читает изображения, при необходимости уменьшает и возвращает блоки content для API."""
    import io
    try:
        from PIL import Image
    except ImportError:
        logger.warning("PIL/Pillow не установлен, фото не передаём в Claude")
        return []

    blocks = []
    for i, path in enumerate(image_paths[:10]):  # не более 10 фото
        p = Path(path)
        if not p.exists():
            continue
        try:
            with Image.open(path) as img:
                img = img.convert("RGB")
                w, h = img.size
                # Ограничение ~1.15 Mpx для экономии токенов
                if w * h > max_size_mpx * 1_150_000:
                    ratio = (max_size_mpx * 1_150_000 / (w * h)) ** 0.5
                    new_w, new_h = int(w * ratio), int(h * ratio)
                    img = img.resize((max(1, new_w), max(1, new_h)), Image.Resampling.LANCZOS)
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=85)
                b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
                blocks.append({
                    "type": "image",
                    "source": {"type": "base64", "media_type": "image/jpeg", "data": b64},
                })
        except Exception as e:
            logger.warning("Пропуск изображения %s: %s", path, e)
    return blocks


def get_layout_from_claude(
    api_key: str,
    bio_text: str,
    image_paths: list[str],
    template_description: str | None = None,
    model: str = "claude-sonnet-4-20250514",
) -> dict[str, Any] | None:
    """
    Отправляет Claude биографический текст и фото, получает JSON-описание структуры страниц.
    Возвращает dict с ключом "sections": список блоков {"type": "heading"|"paragraph"|"image", ...}.
    """
    if not api_key or not bio_text.strip():
        return None
    try:
        from anthropic import Anthropic
    except ImportError:
        logger.warning("anthropic не установлен: pip install anthropic")
        return None

    template = (template_description or "").strip() or DEFAULT_TEMPLATE_DESCRIPTION
    user_content: list[dict] = [
        {"type": "text", "text": f"Текст биографии для книги:\n\n{bio_text}\n\nНиже приложены фото пользователя (по порядку: фото 1, фото 2, …)."}
    ]
    image_blocks = _load_images_for_claude(image_paths)
    for b in image_blocks:
        user_content.append(b)
    user_content.append({
        "type": "text",
        "text": "Верни один JSON-объект с ключом \"sections\" — массив блоков. Каждый блок: "
        "{\"type\": \"heading\", \"text\": \"Заголовок\"} или "
        "{\"type\": \"paragraph\", \"text\": \"Текст абзаца\"} или "
        "{\"type\": \"image\", \"image_index\": 0, \"caption\": \"Подпись\"}. "
        "image_index — номер фото (0, 1, 2…). Разбей биографию на логичные абзацы и вставь фото в подходящие места. Ответ дай только JSON, без markdown-блока."
    })

    client = Anthropic(api_key=api_key)
    try:
        resp = client.messages.create(
            model=model,
            max_tokens=4096,
            system=(
                "Ты — верстальщик семейной книги. Твоя задача — по тексту биографии и приложенным фото "
                "вернуть структуру макета в виде JSON (ключ sections). " + template
            ),
            messages=[{"role": "user", "content": user_content}],
        )
    except Exception as e:
        logger.exception("Claude API: %s", e)
        return None

    text = ""
    if resp.content:
        for block in resp.content:
            if getattr(block, "text", None):
                text += block.text

    if not text.strip():
        return None
    # Вытащить JSON из ответа (иногда обёрнут в ```json ... ```)
    json_match = re.search(r"\{[\s\S]*\}", text)
    if not json_match:
        return None
    try:
        layout = json.loads(json_match.group())
        if isinstance(layout.get("sections"), list):
            return layout
        return {"sections": [{"type": "paragraph", "text": bio_text[:5000]}]}
    except json.JSONDecodeError:
        logger.warning("Claude вернул невалидный JSON, используем простой макет")
        return {"sections": [{"type": "heading", "text": "Биография"}, {"type": "paragraph", "text": bio_text[:8000]}]}


def _find_cyrillic_font() -> str:
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        for _name, path in [
            ("CyrillicFont", "C:\\Windows\\Fonts\\arial.ttf"),
            ("CyrillicFont", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            ("CyrillicFont", "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
        ]:
            if Path(path).exists():
                pdfmetrics.registerFont(TTFont("CyrillicFont", path))
                return "CyrillicFont"
    except Exception:
        pass
    return "Helvetica"


def render_pdf(
    layout: dict[str, Any],
    image_paths: list[str],
    output_pdf_path: str,
) -> bool:
    """Собирает PDF из layout (sections) и путей к фото. Возвращает True при успехе."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Image as RLImage, Paragraph, SimpleDocTemplate, Spacer

    font_name = _find_cyrillic_font()
    doc = SimpleDocTemplate(
        output_pdf_path,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="BookTitle",
        fontName=font_name,
        fontSize=16,
        spaceAfter=14,
    ))
    styles.add(ParagraphStyle(
        name="BookBody",
        fontName=font_name,
        fontSize=11,
        leading=14,
        spaceAfter=10,
    ))
    styles.add(ParagraphStyle(
        name="BookCaption",
        fontName=font_name,
        fontSize=9,
        textColor=(0.4, 0.4, 0.4),
        spaceAfter=14,
    ))

    story = []
    sections = layout.get("sections") or []
    for s in sections:
        kind = s.get("type") or "paragraph"
        if kind == "heading":
            story.append(Paragraph(s.get("text", "").replace("&", "&amp;").replace("<", "&lt;"), styles["BookTitle"]))
            story.append(Spacer(1, 0.3 * cm))
        elif kind == "paragraph":
            text = (s.get("text") or "").replace("&", "&amp;").replace("<", "&lt;").replace("\n", "<br/>")
            story.append(Paragraph(text, styles["BookBody"]))
        elif kind == "image":
            idx = s.get("image_index", 0)
            caption = (s.get("caption") or "").strip().replace("&", "&amp;").replace("<", "&lt;")
            if 0 <= idx < len(image_paths) and Path(image_paths[idx]).exists():
                try:
                    story.append(RLImage(image_paths[idx], width=12 * cm))
                    if caption:
                        story.append(Paragraph(caption, styles["BookCaption"]))
                    story.append(Spacer(1, 0.5 * cm))
                except Exception as e:
                    logger.warning("Не удалось вставить изображение %s: %s", image_paths[idx], e)
    if not story:
        from reportlab.platypus import Preformatted
        story.append(Preformatted((layout.get("sections") or [{}])[0].get("text", "Нет содержимого.")[:5000], styles["BookBody"]))

    try:
        doc.build(story)
        return True
    except Exception as e:
        logger.exception("Ошибка сборки PDF: %s", e)
        return False


def run_typesetter(
    bio_text: str,
    image_paths: list[str],
    output_pdf_path: str,
    api_key: str | None = None,
    template_description: str | None = None,
) -> bool:
    """
    Полный шаг верстальщика: Claude даёт layout по тексту и фото, reportlab собирает PDF.
    image_paths — пути к локальным файлам фото (в том же порядке, что и при отправке в Claude).
    """
    import config
    key = api_key or getattr(config, "ANTHROPIC_API_KEY", None) or ""
    if not key:
        logger.warning("ANTHROPIC_API_KEY не задан, верстальщик пропущен")
        return False
    layout = get_layout_from_claude(key, bio_text, image_paths, template_description)
    if not layout:
        return False
    return render_pdf(layout, image_paths, output_pdf_path)
