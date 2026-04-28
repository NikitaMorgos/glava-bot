#!/usr/bin/env python3
"""Test nano-banana-2 availability and generate cover portrait with reference photo."""
import os
import sys
import json
import base64
import time
import requests
import pathlib

EXPORTS = pathlib.Path("/opt/glava/exports")
PHOTOS_DIR = EXPORTS / "karakulina_photos"

# Load token from .env
env_path = pathlib.Path("/opt/glava/.env")
for line in env_path.read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

TOKEN = os.environ.get("REPLICATE_API_TOKEN", "")
if not TOKEN:
    print("[ERROR] REPLICATE_API_TOKEN not found")
    sys.exit(1)
print(f"[TOKEN] {TOKEN[:8]}...")

# ── Get prompt and reference photo from last Cover Designer call ──
call1_files = sorted(EXPORTS.glob("karakulina_stage4_cover_designer_call1_*.json"))
if not call1_files:
    print("[ERROR] No cover designer call1 JSON found")
    sys.exit(1)

call1 = json.loads(call1_files[-1].read_text(encoding="utf-8"))
print(f"[INPUT] From: {call1_files[-1].name}")

pg = call1.get("portrait_generation", {})
prompt = pg.get("image_gen_prompt", "")
ref_photo_id = pg.get("reference_photo_id") or call1.get("selected_photo", {}).get("photo_id", "")
print(f"[PROMPT] {prompt[:120]}...")
print(f"[REF]    {ref_photo_id}")

# ── Load reference photo ──────────────────────────────────────────
manifest = json.loads((PHOTOS_DIR / "manifest.json").read_text(encoding="utf-8"))
ref_photo = None
for e in manifest:
    photo_id_str = f"photo_{e['index']:03d}"
    if photo_id_str == ref_photo_id or str(e.get("photo_id")) == ref_photo_id:
        fpath = PHOTOS_DIR / e["filename"]
        if fpath.exists():
            ref_photo = fpath
            break

if not ref_photo:
    print(f"[ERROR] Reference photo {ref_photo_id!r} not found in manifest")
    sys.exit(1)

ref_bytes = ref_photo.read_bytes()
print(f"[PHOTO] {ref_photo.name} ({len(ref_bytes):,} bytes)")

# ── Encode reference photo ────────────────────────────────────────
mime = "image/png" if ref_bytes[:8] == b'\x89PNG\r\n\x1a\n' else "image/jpeg"
ref_b64 = base64.b64encode(ref_bytes).decode("utf-8")
data_uri = f"data:{mime};base64,{ref_b64}"

# ── Test nano-banana-2 ────────────────────────────────────────────
print("\n[TEST] Проверяем nano-banana-2...")
headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
}

payload = {
    "input": {
        "prompt": prompt,
        "image_input": [data_uri],
        "aspect_ratio": "3:4",
        "output_format": "png",
    }
}

resp = requests.post(
    "https://api.replicate.com/v1/models/google/nano-banana-2/predictions",
    headers=headers,
    json=payload,
    timeout=30,
)
print(f"[HTTP]  {resp.status_code}")
d = resp.json()

if resp.status_code != 201:
    print(f"[ERROR] {d.get('detail') or d.get('error') or json.dumps(d)[:300]}")
    sys.exit(1)

pred_id = d.get("id")
status  = d.get("status")
print(f"[PRED]  id={pred_id}  status={status}")

if status == "failed":
    print(f"[FAIL]  {d.get('error')}")
    sys.exit(1)

# ── Poll ──────────────────────────────────────────────────────────
print("[WAIT] Ожидаем результат...")
deadline = time.time() + 180
interval = 3
while time.time() < deadline:
    time.sleep(interval)
    interval = min(interval * 1.4, 12)
    r = requests.get(
        f"https://api.replicate.com/v1/predictions/{pred_id}",
        headers={"Authorization": f"Bearer {TOKEN}"},
        timeout=20,
    )
    d = r.json()
    status = d.get("status")
    print(f"  status={status}", flush=True)
    if status == "succeeded":
        break
    if status in ("failed", "canceled"):
        print(f"[FAIL] {d.get('error')}")
        sys.exit(1)

if status != "succeeded":
    print("[TIMEOUT]")
    sys.exit(1)

# ── Download output ───────────────────────────────────────────────
output = d.get("output", [])
if isinstance(output, list):
    output = output[0] if output else None
if not output:
    print("[ERROR] No output URL")
    sys.exit(1)

img_resp = requests.get(output, timeout=60)
img_bytes = img_resp.content
print(f"[IMG]   {len(img_bytes):,} bytes")

out_path = EXPORTS / "karakulina_cover_nanobana_FINAL.webp"
out_path.write_bytes(img_bytes)
print(f"\n[SAVED] {out_path}")
print("[OK] nano-banana-2 доступен и отработал!")
