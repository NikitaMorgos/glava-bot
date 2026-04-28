#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест Cover Designer + Replicate — только генерация обложки.
Не запускает полный Stage 4 (нет Art Director, Layout Designer, QA).

Использование:
    python scripts/test_cover_only.py
    python scripts/test_cover_only.py --photos-dir exports/karakulina_photos/
"""
import argparse
import asyncio
import base64
import json
import os
import sys
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

try:
    import anthropic
except ImportError:
    print("[ERROR] pip install anthropic")
    sys.exit(1)

from pipeline_utils import load_config, load_prompt

PROJECT_ID   = "karakulina_stage4"
SUBJECT_NAME = "Каракулина Валентина Ивановна"
SUBJECT = {
    "name": SUBJECT_NAME,
    "surname": "Каракулина",
    "first_name": "Валентина",
    "patronymic": "Ивановна",
    "birth_year": 1920,
    "death_year": 2005,
    "subtitle": "История жизни, рассказанная родными",
}
MAX_PORTRAIT_ATTEMPTS = 3
DEFAULT_PHOTOS_DIR = ROOT / "exports" / "karakulina_photos"
DEFAULT_PREFIX     = "karakulina"


def parse_json_response(raw: str, agent_name: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:])
        if text.endswith("```"):
            text = text[:-3].strip()
    s, e = text.find("{"), text.rfind("}")
    if s != -1 and e > s:
        try:
            return json.loads(text[s:e + 1])
        except json.JSONDecodeError as exc:
            print(f"[{agent_name}] JSON parse error: {exc}")
    raise ValueError(f"[{agent_name}] Не удалось распарсить JSON")


async def call_agent(client, agent_name, cfg_key, system_prompt, user_message, cfg):
    agent_cfg = cfg[cfg_key]
    model       = agent_cfg["model"]
    max_tokens  = agent_cfg["max_tokens"]
    temperature = agent_cfg.get("temperature", 0.3)

    print(f"\n[{agent_name}] Запускаю ({model}, max_tokens={max_tokens})...")
    start = datetime.now()
    loop  = asyncio.get_event_loop()

    def _call():
        raw_parts = []
        with client.messages.stream(
            model=model, max_tokens=max_tokens, temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": json.dumps(user_message, ensure_ascii=False)}],
        ) as stream:
            for text in stream.text_stream:
                raw_parts.append(text)
            final = stream.get_final_message()
        return "".join(raw_parts), final.usage.input_tokens, final.usage.output_tokens

    import time as _time
    for attempt in range(4):
        try:
            raw, in_tok, out_tok = await loop.run_in_executor(None, _call)
            break
        except anthropic.RateLimitError:
            wait = 65 * (attempt + 1)
            print(f"[{agent_name}] Rate limit — жду {wait}с...")
            await asyncio.sleep(wait)
    else:
        raise RuntimeError(f"[{agent_name}] Rate limit не снялся")

    elapsed = (datetime.now() - start).total_seconds()
    print(f"[{agent_name}] Готово за {elapsed:.1f}с | in={in_tok} out={out_tok}")
    return parse_json_response(raw, agent_name), in_tok, out_tok


def load_photos(photos_dir: Path) -> list[dict]:
    manifest_path = photos_dir / "manifest.json"
    if not manifest_path.exists():
        files = sorted(list(photos_dir.glob("*.jpg")) + list(photos_dir.glob("*.png")))
        return [{"id": f"photo_{i+1:03d}", "filename": p.name, "local_path": str(p), "caption": ""}
                for i, p in enumerate(files)]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    photos = []
    for e in sorted(manifest, key=lambda x: x["index"]):
        if e.get("exclude"):
            continue
        actual_path = photos_dir / e["filename"]
        if not actual_path.exists():
            actual_path = Path(e.get("local_path", ""))
        if not actual_path.exists():
            continue
        photos.append({
            "id": f"photo_{e['index']:03d}",
            "photo_id": e["photo_id"],
            "filename": e["filename"],
            "local_path": str(actual_path),
            "caption": e.get("caption") or "",
        })
    return photos


def run_replicate_ink_sketch(prompt: str, reference_image_bytes: bytes | None = None) -> bytes | None:
    try:
        from replicate_client import generate_ink_sketch_portrait
        return generate_ink_sketch_portrait(
            prompt,
            reference_image_bytes=reference_image_bytes,
            aspect_ratio="3:4",
        )
    except Exception as e:
        print(f"[REPLICATE] Ошибка: {e}")
        return None


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--photos-dir", default=str(DEFAULT_PHOTOS_DIR))
    parser.add_argument("--prefix", default=DEFAULT_PREFIX)
    args = parser.parse_args()

    cfg    = load_config()
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    ts     = datetime.now().strftime("%Y%m%d_%H%M%S")

    # ── Загрузка фото ──────────────────────────────────────────────
    photos_dir = Path(args.photos_dir)
    photos = load_photos(photos_dir) if photos_dir.exists() else []
    print(f"\n[INPUT] Фото: {len(photos)}")
    for p in photos[:5]:
        print(f"  {p['id']} — {p['filename']}")
    if len(photos) > 5:
        print(f"  ... и ещё {len(photos) - 5}")

    has_replicate = bool(os.environ.get("REPLICATE_API_TOKEN"))
    print(f"[INPUT] Replicate: {'✅ токен есть' if has_replicate else '❌ токен не задан'}")

    # ── Cover Designer — Вызов 1 ───────────────────────────────────
    print("\n" + "─" * 60)
    print("Cover Designer — Вызов 1 (выбор фото + промпт)")
    print("─" * 60)

    system_prompt = load_prompt(cfg["cover_designer"]["prompt_file"])
    cd1_msg = {
        "context": {
            "call_type": "initial",
            "instruction": (
                "Выбери главное фото, составь промпт для генерации ink sketch портрета, "
                "сделай предварительный дизайн обложки. "
                "Если фотографий нет — составь промпт на основе метаданных героя."
            ),
        },
        "data": {"project_id": PROJECT_ID, "subject": SUBJECT, "photos": photos},
    }
    cd1_raw, _, _ = await call_agent(client, "COVER_DESIGNER_1", "cover_designer", system_prompt, cd1_msg, cfg)

    cd1_path = ROOT / "exports" / f"{args.prefix}_cover_test_call1_{ts}.json"
    cd1_path.write_text(json.dumps(cd1_raw, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[SAVED] {cd1_path.name}")

    selected = cd1_raw.get("selected_photo", {})
    pg       = cd1_raw.get("portrait_generation", {})
    prompt   = pg.get("image_gen_prompt", "")
    print(f"\n  Выбрано фото: {selected.get('photo_id', '—')}")
    print(f"  Причина: {selected.get('reason', '')[:120]}")
    print(f"  Промпт: {prompt[:150]}...")

    # ── Читаем байты референс-фото ─────────────────────────────────
    reference_bytes = None
    selected_id = selected.get("photo_id")
    if selected_id and photos:
        ref = next((p for p in photos if p.get("id") == selected_id or p.get("photo_id") == selected_id), None)
        if ref:
            ref_path = Path(ref["local_path"])
            if ref_path.exists():
                reference_bytes = ref_path.read_bytes()
                print(f"\n  Референс-фото: {ref_path.name} ({len(reference_bytes):,} байт) ✅")
            else:
                print(f"\n  ⚠️  Файл не найден: {ref_path}")
        else:
            print(f"\n  ⚠️  Фото {selected_id!r} не найдено в списке")

    # ── Replicate ──────────────────────────────────────────────────
    portrait_bytes = None
    if prompt and has_replicate:
        mode = "InstantID (с референсом)" if reference_bytes else "FLUX Schnell (без референса)"
        print(f"\n[REPLICATE] Генерируем портрет [{mode}]...")
        start_r = datetime.now()
        portrait_bytes = run_replicate_ink_sketch(prompt, reference_bytes)
        elapsed_r = (datetime.now() - start_r).total_seconds()

        if portrait_bytes:
            out_path = ROOT / "exports" / f"{args.prefix}_cover_test_portrait_{ts}.webp"
            out_path.write_bytes(portrait_bytes)
            print(f"[REPLICATE] ✅ Готово за {elapsed_r:.1f}с | {len(portrait_bytes):,} байт")
            print(f"[SAVED] {out_path.name}")
        else:
            print(f"[REPLICATE] ❌ Не удалось сгенерировать")
    elif not has_replicate:
        print("\n[REPLICATE] Пропуск: токен не задан")

    # ── Cover Designer — Вызов 2 (валидация) ──────────────────────
    if portrait_bytes:
        print("\n" + "─" * 60)
        print("Cover Designer — Вызов 2 (валидация портрета)")
        print("─" * 60)

        portrait_b64 = base64.b64encode(portrait_bytes).decode("utf-8")
        prev_comp = cd1_raw.get("cover_composition", {})
        cd2_msg = {
            "context": {
                "call_type": "validation", "iteration": 1,
                "max_iterations": MAX_PORTRAIT_ATTEMPTS,
                "instruction": "Оцени сгенерированный портрет. Если подходит — финализируй. Если нет — дай уточнённый промпт.",
            },
            "data": {
                "project_id": PROJECT_ID,
                "original_photo": None,
                "generated_portrait": portrait_b64,
                "previous_cover_composition": prev_comp,
                "subject": SUBJECT,
            },
        }
        cd2_raw, _, _ = await call_agent(client, "COVER_DESIGNER_2", "cover_designer", system_prompt, cd2_msg, cfg)

        cd2_path = ROOT / "exports" / f"{args.prefix}_cover_test_call2_{ts}.json"
        cd2_path.write_text(json.dumps(cd2_raw, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[SAVED] {cd2_path.name}")

        verdict = cd2_raw.get("portrait_verdict", "?")
        sym = "✅" if verdict == "approved" else ("🔄" if verdict == "retry" else "⚠️")
        print(f"\n  Вердикт: {sym} {verdict.upper()}")
        if verdict == "retry":
            rd = cd2_raw.get("retry_details", {})
            print(f"  Проблема: {rd.get('issue', '')}")

    print("\n" + "=" * 60)
    print("  ИТОГ")
    print("=" * 60)
    if portrait_bytes:
        print(f"  Портрет: exports/{args.prefix}_cover_test_portrait_{ts}.webp")
        print(f"  Режим: {'InstantID' if reference_bytes else 'FLUX Schnell'}")
    else:
        print("  Портрет: не сгенерирован")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
