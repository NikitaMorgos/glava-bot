#!/usr/bin/env python3
"""
Прогон последнего голосового через пайплайн: транскрипция (Yandex) -> LLM биография (ChatGPT).
Запускать на сервере: cd /opt/glava && ./venv/bin/python scripts/run_latest_voice_pipeline.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
import db

# Выбор пайплайна: TRANSCRIBER или первый с ключом (mymeet → plaud → assemblyai → speechkit)
_transcriber = getattr(config, "TRANSCRIBER", None)
if _transcriber == "mymeet" and config.MYMEET_API_KEY:
    from pipeline_mymeet_bio import run_pipeline_sync
    print("Пайплайн: mymeet + ChatGPT")
elif _transcriber == "plaud" and config.PLAUD_API_TOKEN:
    from pipeline_plaud_bio import run_pipeline_sync
    print("Пайплайн: Plaud + ChatGPT")
elif _transcriber == "assemblyai" and config.ASSEMBLYAI_API_KEY:
    from pipeline_assemblyai_bio import run_pipeline_sync
    print("Пайплайн: AssemblyAI + ChatGPT")
elif _transcriber == "speechkit" and config.YANDEX_API_KEY:
    from pipeline_transcribe_bio import run_pipeline_sync
    print("Пайплайн: Yandex SpeechKit + ChatGPT")
elif config.MYMEET_API_KEY:
    from pipeline_mymeet_bio import run_pipeline_sync
    print("Пайплайн: mymeet + ChatGPT")
elif config.PLAUD_API_TOKEN:
    from pipeline_plaud_bio import run_pipeline_sync
    print("Пайплайн: Plaud + ChatGPT")
elif config.ASSEMBLYAI_API_KEY:
    from pipeline_assemblyai_bio import run_pipeline_sync
    print("Пайплайн: AssemblyAI + ChatGPT")
elif config.YANDEX_API_KEY:
    from pipeline_transcribe_bio import run_pipeline_sync
    print("Пайплайн: Yandex SpeechKit + ChatGPT")
else:
    print("Нет ключа транскрипции (YANDEX_API_KEY, MYMEET_API_KEY, PLAUD_API_TOKEN, ASSEMBLYAI_API_KEY)")
    sys.exit(1)

row = None
with db.get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT v.id, v.storage_key, v.duration, v.created_at, u.telegram_id, u.username
            FROM voice_messages v
            JOIN users u ON v.user_id = u.id
            WHERE v.created_at >= CURRENT_DATE
            ORDER BY v.created_at DESC
            LIMIT 1
        """)
        row = cur.fetchone()
        if not row:
            cur.execute("""
                SELECT v.id, v.storage_key, v.duration, v.created_at, u.telegram_id, u.username
                FROM voice_messages v
                JOIN users u ON v.user_id = u.id
                ORDER BY v.created_at DESC
                LIMIT 1
            """)
            row = cur.fetchone()

if not row:
    print("Голосовых в БД нет.")
    sys.exit(1)

voice_id, storage_key, duration, created_at, telegram_id, username = row
print(f"Голосовое: id={voice_id}, duration={duration} сек, user {telegram_id} @{username or '-'}")
print(f"Запуск пайплайна...")

ok = run_pipeline_sync(voice_id, storage_key, telegram_id, username)

if ok:
    folder = Path(__file__).resolve().parent.parent / "exports" / f"client_{telegram_id}_{username or 'unknown'}"
    print(f"\nГотово! Файлы в: {folder}")
    if folder.exists():
        for f in sorted(folder.iterdir()):
            if f.is_file():
                print(f"  - {f.name}")
else:
    print("Ошибка пайплайна. Проверь логи.")
