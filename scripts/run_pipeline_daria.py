"""Прогон последнего голосового от Даши через пайплайн: транскрипция -> LLM биография -> сохранение."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
import db

TELEGRAM_ID = 605154  # Даша (ddmika)


def main():
    user, voices, _ = db.get_user_all_data(TELEGRAM_ID)
    if not voices:
        print("Нет голосовых от Даши")
        return
    v = voices[-1]
    print("Последнее голосовое:", v["id"], v["storage_key"][:60] + "...")

    if config.MYMEET_API_KEY:
        from pipeline_mymeet_bio import run_pipeline_sync
        print("Пайплайн: mymeet.ai")
    elif config.PLAUD_API_TOKEN:
        from pipeline_plaud_bio import run_pipeline_sync
        print("Пайплайн: Plaud")
    else:
        from pipeline_transcribe_bio import run_pipeline_sync
        print("Пайплайн: SpeechKit/Whisper")

    ok = run_pipeline_sync(v["id"], v["storage_key"], TELEGRAM_ID, user.get("username"))
    print("Результат:", "OK" if ok else "Ошибка")

    if ok:
        folder = Path(__file__).resolve().parent.parent / "exports" / f"client_{TELEGRAM_ID}_{user.get('username', 'unknown')}"
        print("Файлы в:", folder)
        for f in folder.iterdir():
            if f.is_file():
                print("  -", f.name)


if __name__ == "__main__":
    main()
