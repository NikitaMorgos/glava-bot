# -*- coding: utf-8 -*-
"""
Генерация логотипов GLAVA через Replicate (nano-banana-2 / FLUX Schnell).

Запуск:
    python scripts/_gen_glava_logo.py
"""
import os
import sys
import base64
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.environ.get("REPLICATE_API_TOKEN", "")
if not TOKEN:
    print("REPLICATE_API_TOKEN не задан, выход")
    sys.exit(1)

API_BASE = "https://api.replicate.com/v1"
OUT_DIR = Path(__file__).parent.parent / "tasks" / "audience-research" / "brand"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Маленькое белое изображение 1x1 PNG как нейтральный image_input для nano-banana-2
_WHITE_1x1_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI6QAAAABJRU5ErkJggg=="
)
_DATA_URI = "data:image/png;base64," + base64.b64encode(_WHITE_1x1_PNG).decode()


CONCEPTS = [
    {
        "name": "concept_A_serif_gold",
        "prompt": (
            "Elegant logo for Russian family memoir brand GLAVA (ГЛАВА). "
            "Cyrillic wordmark 'ГЛАВА' set in a refined classic serif typeface (like Garamond or Didot style), "
            "warm gold #C9922A color on pure white background. "
            "Below the wordmark: small subtitle 'glava.family' in thin sans-serif. "
            "Minimal, premium, literary. No illustrations, clean vector-style logo. "
            "White background, centered composition, high resolution branding."
        ),
    },
    {
        "name": "concept_B_ornamental_initial",
        "prompt": (
            "Premium brand logo design for ГЛАВА (GLAVA) — a Russian family biography memoir service. "
            "Large ornamental Cyrillic capital letter Г (G) as monogram/medallion, "
            "surrounded by delicate Art Nouveau laurel wreath or feather motif. "
            "Deep ink color #1A1410 and warm gold #C9922A on cream #FAF6EF background. "
            "Below: wordmark 'ГЛАВА' in elegant serif capitals, and 'glava.family' in small caps. "
            "Heritage, family heirloom feel. Round or shield badge shape. Vector clean style."
        ),
    },
    {
        "name": "concept_C_modern_minimal",
        "prompt": (
            "Modern minimalist wordmark logo for ГЛАВА (GLAVA) family memoir app. "
            "The word 'ГЛАВА' in bold geometric sans-serif Cyrillic, with the letter Г "
            "subtly stylized as an open book or turned page corner. "
            "Color: warm dark #2C2118 on off-white #FAF6EF. Thin horizontal rule below the wordmark. "
            "Clean, contemporary, trustworthy. White background. Suitable for app icon and web favicon."
        ),
    },
]


def call_nano_banana(prompt: str, timeout_s: int = 180) -> bytes | None:
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
        "Prefer": "wait",
    }
    payload = {
        "input": {
            "prompt": prompt,
            "image_input": [_DATA_URI],
            "aspect_ratio": "1:1",
            "output_format": "png",
        }
    }
    print(f"  → nano-banana-2: {prompt[:70]}...")
    try:
        resp = requests.post(
            f"{API_BASE}/models/google/nano-banana-2/predictions",
            headers=headers,
            json=payload,
            timeout=timeout_s,
        )
        resp.raise_for_status()
        pred = resp.json()
    except Exception as e:
        print(f"  ✗ ошибка запроса: {e}")
        return None

    if pred.get("status") == "succeeded":
        return _download(pred)

    pred_id = pred.get("id")
    if not pred_id:
        print(f"  ✗ нет id: {pred}")
        return None

    print(f"  ⏳ ожидаем prediction {pred_id}...")
    deadline = time.time() + timeout_s
    interval = 3
    while time.time() < deadline:
        time.sleep(interval)
        interval = min(interval * 1.4, 12)
        try:
            r = requests.get(f"{API_BASE}/predictions/{pred_id}",
                             headers={"Authorization": f"Bearer {TOKEN}"}, timeout=30)
            r.raise_for_status()
            pred = r.json()
        except Exception as e:
            print(f"  ⚠ polling error: {e}")
            continue
        status = pred.get("status")
        print(f"  ... статус: {status}")
        if status == "succeeded":
            return _download(pred)
        if status in ("failed", "canceled"):
            print(f"  ✗ prediction провалился: {pred.get('error')}")
            return None

    print(f"  ✗ timeout {timeout_s}s")
    return None


def call_flux_schnell(prompt: str, timeout_s: int = 120) -> bytes | None:
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
        "Prefer": "wait",
    }
    payload = {
        "input": {
            "prompt": prompt,
            "aspect_ratio": "1:1",
            "num_outputs": 1,
            "output_format": "png",
            "output_quality": 95,
            "go_fast": True,
        }
    }
    print(f"  → FLUX Schnell fallback...")
    try:
        resp = requests.post(
            f"{API_BASE}/models/black-forest-labs/flux-schnell/predictions",
            headers=headers,
            json=payload,
            timeout=timeout_s,
        )
        resp.raise_for_status()
        pred = resp.json()
    except Exception as e:
        print(f"  ✗ ошибка FLUX: {e}")
        return None

    if pred.get("status") == "succeeded":
        return _download(pred)

    pred_id = pred.get("id")
    if not pred_id:
        return None

    deadline = time.time() + timeout_s
    interval = 2
    while time.time() < deadline:
        time.sleep(interval)
        interval = min(interval * 1.5, 10)
        try:
            r = requests.get(f"{API_BASE}/predictions/{pred_id}",
                             headers={"Authorization": f"Bearer {TOKEN}"}, timeout=30)
            r.raise_for_status()
            pred = r.json()
        except Exception:
            continue
        status = pred.get("status")
        if status == "succeeded":
            return _download(pred)
        if status in ("failed", "canceled"):
            return None
    return None


def _download(pred: dict) -> bytes | None:
    output = pred.get("output")
    if not output:
        print(f"  ✗ нет output в prediction")
        return None
    url = output[0] if isinstance(output, list) else output
    try:
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        return r.content
    except Exception as e:
        print(f"  ✗ ошибка скачивания: {e}")
        return None


def main():
    print(f"\n🎨 Генерация логотипов ГЛАВА → {OUT_DIR}\n")
    results = []
    for c in CONCEPTS:
        name = c["name"]
        prompt = c["prompt"]
        print(f"\n[{name}]")
        data = call_nano_banana(prompt)
        if not data:
            print("  nano-banana не сработал, пробуем FLUX Schnell...")
            data = call_flux_schnell(prompt)
        if data:
            out_path = OUT_DIR / f"logo_{name}.png"
            out_path.write_bytes(data)
            print(f"  ✓ сохранено: {out_path.name} ({len(data)//1024} KB)")
            results.append(str(out_path))
        else:
            print(f"  ✗ не удалось сгенерировать {name}")

    print(f"\n✅ Готово. Сгенерировано: {len(results)}/{len(CONCEPTS)}")
    for r in results:
        print(f"  {r}")


if __name__ == "__main__":
    main()
