"""
Проверка и скачивание фото Каракулиной из S3.

Использование:
    python scripts/fetch_karakulina_photos.py           # только проверить
    python scripts/fetch_karakulina_photos.py --download  # скачать в exports/karakulina_photos/
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

import db
import storage

TELEGRAM_ID = 577528  # Каракулина
PHOTOS_DIR = ROOT / "exports" / "karakulina_photos"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--download", action="store_true", help="Скачать фото в exports/karakulina_photos/")
    args = parser.parse_args()

    print(f"[CHECK] Ищем фото для telegram_id={TELEGRAM_ID} (Каракулина)...")
    photos = db.get_user_photos(TELEGRAM_ID, limit=50)

    if not photos:
        print("[WARN] Фото не найдены в БД!")
        return

    print(f"\n[FOUND] {len(photos)} фото в базе:\n")
    print(f"{'#':<4} {'ID':<6} {'Caption':<50} {'Storage key':<45} {'Date'}")
    print("-" * 130)
    for i, p in enumerate(photos, 1):
        caption = (p.get("caption") or "—")[:48]
        key = (p.get("storage_key") or "")[:43]
        ts = str(p.get("created_at", ""))[:16]
        print(f"{i:<4} {p['id']:<6} {caption:<50} {key:<45} {ts}")

    with_caption = [p for p in photos if p.get("caption")]
    without_caption = [p for p in photos if not p.get("caption")]
    print(f"\n  С подписью:   {len(with_caption)}")
    print(f"  Без подписи:  {len(without_caption)}")

    if not args.download:
        print("\n[INFO] Для скачивания запустите с флагом: --download")
        return

    # Скачиваем
    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\n[DOWNLOAD] Скачиваем в {PHOTOS_DIR} ...")

    ok = 0
    fail = 0
    for i, p in enumerate(photos, 1):
        key = p.get("storage_key", "")
        if not key:
            print(f"  [{i}] SKIP — нет storage_key")
            fail += 1
            continue

        ext = Path(key).suffix or ".jpg"
        caption_slug = ""
        if p.get("caption"):
            safe = "".join(c if c.isalnum() or c in " _-" else "_" for c in p["caption"][:40]).strip()
            caption_slug = f"_{safe}"
        local_name = f"{i:02d}_{p['id']}{caption_slug}{ext}"
        local_path = PHOTOS_DIR / local_name

        try:
            storage.download_file(key, str(local_path))
            size = local_path.stat().st_size
            print(f"  [{i:02d}] OK  {local_name} ({size // 1024} KB)")
            ok += 1
        except Exception as e:
            print(f"  [{i:02d}] ERR {key}: {e}")
            fail += 1

    print(f"\n[RESULT] Скачано: {ok}, ошибок: {fail}")
    if ok:
        print(f"[PATH]   {PHOTOS_DIR}")
        print("\n[NEXT]   Теперь можно запустить Stage 4:")
        print(f"         python scripts/test_stage4_karakulina.py --photos-dir {PHOTOS_DIR}")


if __name__ == "__main__":
    main()
