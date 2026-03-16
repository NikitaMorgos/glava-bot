#!/usr/bin/env python3
"""
Прогон последнего голосового через ВСЕ доступные транскриберы и сохранение в один файл для сравнения.

Запуск: python scripts/run_compare_transcribers.py

Результат: exports/client_{id}_{username}/transcript_comparison.txt
В файле — блоки по каждому сервису: assemblyai, mymeet, plaud, speechkit
"""
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
import db
import storage

EXPORTS_DIR = Path(__file__).resolve().parent.parent / "exports"


def _ensure_client_dir(telegram_id: int, username: str | None) -> Path:
    username = (username or "unknown").replace("/", "_")
    folder = EXPORTS_DIR / f"client_{telegram_id}_{username}"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _transcribe_assemblyai(tmp_path: str) -> str | None:
    key = getattr(config, "ASSEMBLYAI_API_KEY", "") or os.getenv("ASSEMBLYAI_API_KEY", "")
    if not key:
        return None
    try:
        from assemblyai_client import transcribe_via_assemblyai
        return transcribe_via_assemblyai(tmp_path, api_key=key, language_code="ru")
    except Exception as e:
        print(f"  [assemblyai] ошибка: {e}")
        return None


def _transcribe_mymeet(tmp_path: str) -> str | None:
    key = getattr(config, "MYMEET_API_KEY", "") or os.getenv("MYMEET_API_KEY", "")
    if not key:
        return None
    try:
        from mymeet_client import transcribe_via_mymeet
        return transcribe_via_mymeet(tmp_path, api_key=key, template_name="research-interview")
    except Exception as e:
        print(f"  [mymeet] ошибка: {e}")
        return None


def _transcribe_plaud(tmp_path: str) -> str | None:
    token = getattr(config, "PLAUD_API_TOKEN", "") or os.getenv("PLAUD_API_TOKEN", "")
    if not token:
        return None
    try:
        from plaud_client import transcribe_via_plaud
        owner = getattr(config, "PLAUD_OWNER_ID", "glava_default") or "glava_default"
        return transcribe_via_plaud(tmp_path, api_token=token, owner_id=owner, language="ru", diarization=True)
    except Exception as e:
        print(f"  [plaud] ошибка: {e}")
        return None


def _transcribe_speechkit(tmp_path: str, storage_key: str) -> str | None:
    key = getattr(config, "YANDEX_API_KEY", "") or os.getenv("YANDEX_API_KEY", "")
    if not key:
        return None
    try:
        from transcribe import transcribe_via_speechkit
        return transcribe_via_speechkit(storage_key, audio_path=tmp_path)
    except Exception as e:
        print(f"  [speechkit] ошибка: {e}")
        return None


def main() -> None:
    row = None
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT v.id, v.storage_key, v.duration, v.created_at, u.telegram_id, u.username
                FROM voice_messages v
                JOIN users u ON v.user_id = u.id
                WHERE v.created_at >= CURRENT_DATE - INTERVAL '7 days'
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

    ext = Path(storage_key).suffix or ".ogg"
    tmp_path = None

    try:
        fd, tmp_path = tempfile.mkstemp(suffix=ext, dir=tempfile.gettempdir())
        os.close(fd)
        storage.download_file(storage_key, tmp_path)
        print(f"Аудио скачано: {tmp_path}\nТранскрипция...")

        results: dict[str, str] = {}

        for name, fn in [
            ("assemblyai", lambda: _transcribe_assemblyai(tmp_path)),
            ("mymeet", lambda: _transcribe_mymeet(tmp_path)),
            ("plaud", lambda: _transcribe_plaud(tmp_path)),
            ("speechkit", lambda: _transcribe_speechkit(tmp_path, storage_key)),
        ]:
            print(f"  {name}...", end=" ", flush=True)
            text = fn()
            if text and text.strip():
                results[name] = text.strip()
                print(f"OK ({len(text)} символов)")
            else:
                print("пропущен (нет ключа или пустой результат)")

        if not results:
            print("\nНет ни одного успешного транскрибера. Проверь ключи в .env")
            sys.exit(1)

        client_dir = _ensure_client_dir(telegram_id, username)
        out_path = client_dir / "transcript_comparison.txt"
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        lines = [
            f"# Сравнение транскрипций — voice_id={voice_id} — {now}",
            f"# Длительность: {duration} сек",
            "",
        ]
        for name, text in results.items():
            lines.append(f"--- {name} ---")
            lines.append(text.strip())
            lines.append("")

        out_path.write_text("\n".join(lines).strip(), encoding="utf-8")
        print(f"\nГотово: {out_path}")

    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


if __name__ == "__main__":
    main()
