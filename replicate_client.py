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


def _build_prompt(visual_style: str, character_name: str, *, raw: bool = False) -> str:
    """Формирует финальный промпт для генерации изображения.

    raw=True — промпт передаётся как есть (для SMM-иллюстраций, где Лена
    сама описывает стиль). raw=False — добавляет book-cover суффикс (для книг).
    """
    base = visual_style.strip()
    if not base:
        base = f"portrait of {character_name}, warm vintage style, family memoir book cover"

    if raw:
        return base

    # Добавляем технические суффиксы для качественной книжной обложки
    suffix = (
        "book cover illustration, warm color palette, soft lighting, "
        "editorial photography style, high quality, 2:3 portrait aspect ratio"
    )
    if "book cover" not in base.lower():
        base = f"{base}, {suffix}"

    return base


def generate_cover_image(
    visual_style: str,
    character_name: str = "Hero",
    *,
    api_token: str | None = None,
    timeout_s: int = 120,
    raw: bool = False,
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

    prompt = _build_prompt(visual_style, character_name, raw=raw)
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


def generate_ink_sketch_portrait(
    image_gen_prompt: str,
    *,
    reference_image_bytes: bytes | None = None,
    aspect_ratio: str = "3:4",
    api_token: str | None = None,
    timeout_s: int = 180,
) -> bytes | None:
    """
    Генерирует тушевой скетч-портрет для обложки книги.

    Цепочка fallback при наличии reference_image_bytes:
      1. FLUX Dev img2img — основной путь: передаёт реальное фото, трансформирует стиль
         в ink sketch, сохраняя черты лица (prompt_strength=0.82).
      2. nano-banana-2 — альтернативный img2img (Gemini Flash Image).
      3. FLUX Schnell text-to-image — последний fallback без сходства с оригиналом.

    Если reference_image_bytes=None — сразу FLUX Schnell.
    """
    token = api_token or os.environ.get("REPLICATE_API_TOKEN", "")
    if not token:
        logger.warning("replicate_client: REPLICATE_API_TOKEN не задан, пропускаем генерацию портрета")
        return None

    if reference_image_bytes:
        # --- Попытка 1: FLUX Dev img2img (основной) ---
        logger.info("replicate_client: генерируем portrait с референс-фото (flux-dev img2img)")
        result = _generate_flux_dev_img2img(
            image_gen_prompt, reference_image_bytes,
            api_token=token, aspect_ratio=aspect_ratio, timeout_s=timeout_s,
        )
        if result:
            return result
        logger.warning("replicate_client: flux-dev img2img не удался — пробуем nano-banana-2")

        # --- Попытка 2: nano-banana-2 (альтернативный img2img) ---
        for _attempt in range(1, 3):
            result = _generate_nano_banana(
                image_gen_prompt, reference_image_bytes,
                api_token=token, aspect_ratio=aspect_ratio, timeout_s=timeout_s,
            )
            if result:
                return result
            if _attempt < 2:
                logger.warning(
                    "replicate_client: nano-banana-2 попытка %d/2 не удалась — ждём 15с",
                    _attempt,
                )
                time.sleep(15)
        logger.warning("replicate_client: оба img2img не удались — fallback на FLUX Schnell (без референса)")

    return _generate_flux_text_to_image(
        image_gen_prompt, aspect_ratio=aspect_ratio,
        api_token=token, timeout_s=timeout_s,
    )


def _generate_flux_dev_img2img(
    prompt: str,
    reference_image_bytes: bytes,
    *,
    api_token: str,
    aspect_ratio: str = "3:4",
    prompt_strength: float = 0.82,
    timeout_s: int = 180,
) -> bytes | None:
    """
    Генерирует ink sketch портрет через FLUX Dev img2img.

    Передаёт реальное фото как image reference (data URI).
    prompt_strength=0.82 — достаточно для стилизации ink sketch при сохранении черт лица.
    Соотношение сторон задаётся через width/height (flux-dev не поддерживает aspect_ratio=3:4).
    """
    import base64 as _b64

    mime = "image/png" if reference_image_bytes[:8] == b'\x89PNG\r\n\x1a\n' else "image/jpeg"
    ref_b64 = _b64.b64encode(reference_image_bytes).decode("utf-8")
    data_uri = f"data:{mime};base64,{ref_b64}"

    # Размеры под формат FLUX Dev (кратные 8)
    _RATIO_TO_DIMS = {
        "3:4": (864, 1152),
        "2:3": (768, 1152),
        "1:1": (1024, 1024),
        "4:3": (1152, 864),
    }
    width, height = _RATIO_TO_DIMS.get(aspect_ratio, (864, 1152))

    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
        "Prefer": "wait",
    }

    payload = {
        "input": {
            "prompt": prompt,
            "image": data_uri,
            "prompt_strength": prompt_strength,
            "num_inference_steps": 28,
            "guidance": 3.5,
            "width": width,
            "height": height,
            "output_format": "webp",
            "output_quality": 90,
            "disable_safety_checker": True,
        }
    }

    _FLUX_DEV_MODEL = "black-forest-labs/flux-dev"
    logger.info("replicate_client: flux-dev img2img prompt=%r strength=%.2f", prompt[:80], prompt_strength)

    try:
        resp = _requests.post(
            f"{_API_BASE}/models/{_FLUX_DEV_MODEL}/predictions",
            headers=headers,
            json=payload,
            timeout=timeout_s,
        )
        resp.raise_for_status()
        prediction = resp.json()
    except Exception as e:
        logger.error("replicate_client: ошибка создания flux-dev prediction: %s", e)
        return None

    if prediction.get("status") == "succeeded":
        return _download_output(prediction)

    pred_id = prediction.get("id")
    if not pred_id:
        logger.error("replicate_client: flux-dev prediction без id: %s", prediction)
        return None

    logger.info("replicate_client: ожидаем flux-dev prediction %s", pred_id)
    deadline = time.time() + timeout_s
    poll_interval = 3

    while time.time() < deadline:
        time.sleep(poll_interval)
        poll_interval = min(poll_interval * 1.5, 10)

        try:
            poll_resp = _requests.get(
                f"{_API_BASE}/predictions/{pred_id}",
                headers={"Authorization": f"Bearer {api_token}"},
                timeout=30,
            )
            poll_resp.raise_for_status()
            prediction = poll_resp.json()
        except Exception as e:
            logger.warning("replicate_client: ошибка polling flux-dev: %s", e)
            continue

        status = prediction.get("status")
        if status == "succeeded":
            logger.info("replicate_client: flux-dev prediction успешен")
            return _download_output(prediction)
        if status in ("failed", "canceled"):
            logger.error(
                "replicate_client: flux-dev prediction %s статус=%s error=%s",
                pred_id, status, prediction.get("error"),
            )
            return None

    logger.error("replicate_client: timeout %d сек для flux-dev prediction %s", timeout_s, pred_id)
    return None


def _generate_nano_banana(
    prompt: str,
    reference_image_bytes: bytes,
    *,
    api_token: str,
    aspect_ratio: str = "3:4",
    timeout_s: int = 120,
) -> bytes | None:
    """
    Генерирует ink sketch портрет через google/nano-banana-2 (Gemini Flash Image).
    Передаёт реальное фото героя как image_input — модель редактирует его
    в стиле ink sketch, сохраняя черты лица.
    """
    import base64 as _b64

    mime = "image/png" if reference_image_bytes[:8] == b'\x89PNG\r\n\x1a\n' else "image/jpeg"
    ref_b64 = _b64.b64encode(reference_image_bytes).decode("utf-8")
    data_uri = f"data:{mime};base64,{ref_b64}"

    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
        "Prefer": "wait",
    }

    payload = {
        "input": {
            "prompt": prompt,
            "image_input": [data_uri],
            "aspect_ratio": aspect_ratio,
            "output_format": "png",
        }
    }

    _NANO_BANANA_MODEL = "google/nano-banana-2"
    logger.info("replicate_client: nano-banana-2 prompt=%r", prompt[:80])

    try:
        resp = _requests.post(
            f"{_API_BASE}/models/{_NANO_BANANA_MODEL}/predictions",
            headers=headers,
            json=payload,
            timeout=timeout_s,
        )
        resp.raise_for_status()
        prediction = resp.json()
    except Exception as e:
        logger.error("replicate_client: ошибка создания nano-banana-2 prediction: %s", e)
        return None

    if prediction.get("status") == "succeeded":
        return _download_output(prediction)

    pred_id = prediction.get("id")
    if not pred_id:
        logger.error("replicate_client: nano-banana-2 prediction без id: %s", prediction)
        return None

    logger.info("replicate_client: ожидаем nano-banana-2 prediction %s", pred_id)
    deadline = time.time() + timeout_s
    poll_interval = 2

    while time.time() < deadline:
        time.sleep(poll_interval)
        poll_interval = min(poll_interval * 1.5, 10)

        try:
            poll_resp = _requests.get(
                f"{_API_BASE}/predictions/{pred_id}",
                headers={"Authorization": f"Bearer {api_token}"},
                timeout=30,
            )
            poll_resp.raise_for_status()
            prediction = poll_resp.json()
        except Exception as e:
            logger.warning("replicate_client: ошибка polling nano-banana-2: %s", e)
            continue

        status = prediction.get("status")
        if status == "succeeded":
            logger.info("replicate_client: nano-banana-2 prediction успешен")
            return _download_output(prediction)
        if status in ("failed", "canceled"):
            logger.error(
                "replicate_client: nano-banana-2 prediction %s статус=%s error=%s",
                pred_id, status, prediction.get("error"),
            )
            return None

    logger.error("replicate_client: timeout %d сек для nano-banana-2 prediction %s", timeout_s, pred_id)
    return None


def _generate_flux_text_to_image(
    prompt: str,
    *,
    aspect_ratio: str = "3:4",
    api_token: str,
    timeout_s: int = 120,
) -> bytes | None:
    """
    Генерирует портрет через FLUX Schnell (text-to-image).
    Используется как fallback когда референс-фото недоступен.
    Не гарантирует сходство с реальным человеком.
    """
    logger.info("replicate_client: FLUX Schnell text-to-image, prompt=%r", prompt[:80])

    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
        "Prefer": "wait",
    }

    payload = {
        "input": {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "num_outputs": 1,
            "output_format": "webp",
            "output_quality": 90,
            "go_fast": True,
        }
    }

    try:
        resp = _requests.post(
            f"{_API_BASE}/models/{_MODEL}/predictions",
            headers=headers,
            json=payload,
            timeout=timeout_s,
        )
        resp.raise_for_status()
        prediction = resp.json()
    except Exception as e:
        logger.error("replicate_client: ошибка создания FLUX prediction: %s", e)
        return None

    if prediction.get("status") == "succeeded":
        return _download_output(prediction)

    pred_id = prediction.get("id")
    if not pred_id:
        logger.error("replicate_client: FLUX prediction без id: %s", prediction)
        return None

    logger.info("replicate_client: ожидаем FLUX prediction %s", pred_id)
    deadline = time.time() + timeout_s
    poll_interval = 2

    while time.time() < deadline:
        time.sleep(poll_interval)
        poll_interval = min(poll_interval * 1.5, 10)

        try:
            poll_resp = _requests.get(
                f"{_API_BASE}/predictions/{pred_id}",
                headers={"Authorization": f"Bearer {api_token}"},
                timeout=30,
            )
            poll_resp.raise_for_status()
            prediction = poll_resp.json()
        except Exception as e:
            logger.warning("replicate_client: ошибка polling FLUX: %s", e)
            continue

        status = prediction.get("status")
        if status == "succeeded":
            logger.info("replicate_client: FLUX prediction успешен")
            return _download_output(prediction)
        if status in ("failed", "canceled"):
            logger.error(
                "replicate_client: FLUX prediction %s статус=%s error=%s",
                pred_id, status, prediction.get("error"),
            )
            return None

    logger.error("replicate_client: timeout %d сек для FLUX prediction %s", timeout_s, pred_id)
    return None
