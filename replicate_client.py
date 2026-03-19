# -*- coding: utf-8 -*-
"""
Клиент для AI-генерации обложки книги через Replicate API.

Модель по умолчанию: black-forest-labs/flux-schnell
  - Быстрая (~5 сек), высокое качество, поддерживает соотношение 2:3 (книжный формат).

Использование:
    from replicate_client import generate_cover_image
    image_bytes = generate_cover_image(
        visual_style="warm vintage portrait of elderly Russian woman...",
        character_name="Мария Степановна",
    )
    # image_bytes — PNG/WebP байты, готовые для вставки в PDF
"""
import logging
import os
import time
import requests as _requests

logger = logging.getLogger(__name__)

# Модель Replicate для обложек
_MODEL = "black-forest-labs/flux-schnell"
_API_BASE = "https://api.replicate.com/v1"


def _build_prompt(visual_style: str, character_name: str) -> str:
    """Формирует финальный промпт для генерации обложки."""
    base = visual_style.strip()
    if not base:
        base = f"portrait of {character_name}, warm vintage style, family memoir book cover"

    # Добавляем технические суффиксы для качественной книжной обложки
    suffix = (
        "book cover illustration, warm color palette, soft lighting, "
        "editorial photography style, high quality, 2:3 portrait aspect ratio"
    )
    # Не дублировать если уже есть
    if "book cover" not in base.lower():
        base = f"{base}, {suffix}"

    return base


def generate_cover_image(
    visual_style: str,
    character_name: str = "Hero",
    *,
    api_token: str | None = None,
    timeout_s: int = 120,
) -> bytes | None:
    """
    Генерирует изображение обложки через Replicate FLUX Schnell.

    Args:
        visual_style: описание визуального стиля из cover_spec.visual_style
        character_name: имя героя (для fallback промпта)
        api_token: REPLICATE_API_TOKEN (если не передан — берём из env)
        timeout_s: максимальное время ожидания генерации (секунды)

    Returns:
        bytes: PNG/WebP данные изображения, или None при ошибке
    """
    token = api_token or os.environ.get("REPLICATE_API_TOKEN", "")
    if not token:
        logger.warning("replicate_client: REPLICATE_API_TOKEN не задан, пропускаем генерацию")
        return None

    prompt = _build_prompt(visual_style, character_name)
    logger.info("replicate_client: генерируем обложку, prompt=%r", prompt[:80])

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Prefer": "wait",  # Synchronous mode — ждём результат в одном запросе
    }

    payload = {
        "input": {
            "prompt": prompt,
            "aspect_ratio": "2:3",
            "num_outputs": 1,
            "output_format": "webp",
            "output_quality": 85,
            "go_fast": True,
        }
    }

    # Используем predictions endpoint для модели
    model_slug = _MODEL.replace("/", "%2F")

    try:
        # Сначала пробуем синхронный режим (Prefer: wait) через /models/.../predictions
        resp = _requests.post(
            f"{_API_BASE}/models/{_MODEL}/predictions",
            headers=headers,
            json=payload,
            timeout=timeout_s,
        )
        resp.raise_for_status()
        prediction = resp.json()
    except Exception as e:
        logger.error("replicate_client: ошибка создания prediction: %s", e)
        return None

    # Если ответ уже succeeded (синхронный режим сработал)
    if prediction.get("status") == "succeeded":
        return _download_output(prediction)

    # Иначе — polling
    pred_id = prediction.get("id")
    if not pred_id:
        logger.error("replicate_client: prediction без id: %s", prediction)
        return None

    logger.info("replicate_client: ожидаем prediction %s", pred_id)
    deadline = time.time() + timeout_s
    poll_interval = 2

    while time.time() < deadline:
        time.sleep(poll_interval)
        poll_interval = min(poll_interval * 1.5, 10)

        try:
            poll_resp = _requests.get(
                f"{_API_BASE}/predictions/{pred_id}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=30,
            )
            poll_resp.raise_for_status()
            prediction = poll_resp.json()
        except Exception as e:
            logger.warning("replicate_client: ошибка polling: %s", e)
            continue

        status = prediction.get("status")
        if status == "succeeded":
            logger.info("replicate_client: prediction успешен")
            return _download_output(prediction)
        if status in ("failed", "canceled"):
            logger.error(
                "replicate_client: prediction %s статус=%s error=%s",
                pred_id, status, prediction.get("error"),
            )
            return None

    logger.error("replicate_client: timeout %d сек для prediction %s", timeout_s, pred_id)
    return None


def _download_output(prediction: dict) -> bytes | None:
    """Скачивает первое изображение из output prediction."""
    output = prediction.get("output")
    if not output:
        logger.error("replicate_client: prediction без output: %s", prediction)
        return None

    # output — список URL (или одна строка)
    url = output[0] if isinstance(output, list) else output

    try:
        img_resp = _requests.get(url, timeout=60)
        img_resp.raise_for_status()
        data = img_resp.content
        logger.info("replicate_client: изображение загружено, %d байт", len(data))
        return data
    except Exception as e:
        logger.error("replicate_client: ошибка скачивания изображения с %s: %s", url, e)
        return None
