"""
Генерирует JSON-манифест фото Каракулиной с подписями из БД.
Сохраняет в exports/karakulina_photos/manifest.json
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

import db
import storage

TELEGRAM_ID = 577528
PHOTOS_DIR = ROOT / "exports" / "karakulina_photos"


def main():
    photos = db.get_user_photos(TELEGRAM_ID, limit=50)
    print(f"[INFO] Фото в БД: {len(photos)}")

    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

    manifest = []
    for i, p in enumerate(photos, 1):
        key = p.get("storage_key", "")
        ext = Path(key).suffix or ".jpg"
        caption = p.get("caption") or ""

        caption_slug = ""
        if caption:
            safe = "".join(c if c.isalnum() or c in " _-" else "_" for c in caption[:40]).strip()
            caption_slug = f"_{safe}"
        filename = f"{i:02d}_{p['id']}{caption_slug}{ext}"
        local_path = PHOTOS_DIR / filename

        entry = {
            "index": i,
            "photo_id": p["id"],
            "filename": filename,
            "local_path": str(local_path),
            "storage_key": key,
            "caption": caption,
            "created_at": str(p.get("created_at", "")),
            "exists_locally": local_path.exists(),
        }
        manifest.append(entry)
        caption_display = caption[:60] if caption else "(без подписи)"
        status = "OK" if local_path.exists() else "!!"
        print(f"  [{status}] {i:02d}  {caption_display}")

    manifest_path = PHOTOS_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[SAVED] {manifest_path}")

    existing = [e for e in manifest if e["exists_locally"]]
    with_cap = [e for e in manifest if e["caption"]]
    print(f"[STATS] Всего: {len(manifest)}, скачано: {len(existing)}, с подписью: {len(with_cap)}")

    print("\n[CAPTIONS]")
    for e in manifest:
        if e["caption"]:
            print(f"  #{e['index']:02d} (id={e['photo_id']}): {e['caption']}")


if __name__ == "__main__":
    main()
