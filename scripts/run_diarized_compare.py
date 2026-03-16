#!/usr/bin/env python3
"""
Прогон последнего голосового через SpeechKit (с диаризацией) и AssemblyAI (speaker_labels).
Результаты в exports/client_{telegram_id}_{username}/ с именами:
  transcript_speechkit_diarized.txt
  transcript_assemblyai_diarized.txt
  transcript_comparison_diarized.txt

Запуск: python scripts/run_diarized_compare.py

Опционально: сохранить в фиксированную папку client_605154_ddmika:
  python scripts/run_diarized_compare.py --output-dir client_605154_ddmika

Нужны: YANDEX_API_KEY (и при диаризации — HUGGINGFACE_TOKEN или librosa+scikit-learn),
ASSEMBLYAI_API_KEY и pip install assemblyai.
"""
import argparse
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


def _ensure_client_dir(telegram_id: int, username: str | None, force_dir: str | None = None) -> Path:
    if force_dir:
        folder = EXPORTS_DIR / force_dir
    else:
        username = (username or "unknown").replace("/", "_")
        folder = EXPORTS_DIR / f"client_{telegram_id}_{username}"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _transcribe_speechkit_diarized(tmp_path: str, storage_key: str) -> str | None:
    key = getattr(config, "YANDEX_API_KEY", "") or os.getenv("YANDEX_API_KEY", "")
    if not key:
        return None
    try:
        import transcribe as transcribe_mod
        segments = transcribe_mod.transcribe_with_diarization(tmp_path, storage_key=storage_key)
        if not segments:
            return None
        out = transcribe_mod.format_diarized_transcript(segments, include_timestamps=False)
        return out
    except Exception as e:
        print(f"  [speechkit diarized] ошибка: {e}")
        return None


def _transcribe_assemblyai_diarized(tmp_path: str, storage_key: str | None = None) -> str | None:
    key = getattr(config, "ASSEMBLYAI_API_KEY", "") or os.getenv("ASSEMBLYAI_API_KEY", "")
    if not key:
        return None
    try:
        from assemblyai_client import transcribe_via_assemblyai
        # Для длинных файлов передаём URL (presigned) — AssemblyAI сам скачает, без загрузки с машины
        if storage_key:
            try:
                url = storage.get_presigned_download_url(storage_key, expires_in=7200)
                if url and url.startswith("http"):
                    return transcribe_via_assemblyai(
                        audio_path="",
                        api_key=key,
                        language_code="ru",
                        speaker_labels=True,
                        audio_url=url,
                    )
            except Exception:
                pass
        return transcribe_via_assemblyai(
            tmp_path, api_key=key, language_code="ru", speaker_labels=True
        )
    except Exception as e:
        print(f"  [assemblyai diarized] ошибка: {e}")
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Сравнение транскрипций с разделением по голосам")
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Папка в exports/ для сохранения (например client_605154_ddmika)",
    )
    args = parser.parse_args()

    row = None
    with db.get_connection() as conn:
        with conn.cursor() as cur:
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

    out_dir_name = args.output_dir or f"client_{telegram_id}_{username or 'unknown'}".replace("/", "_")
    client_dir = _ensure_client_dir(telegram_id, username, force_dir=out_dir_name)
    print(f"Сохраняем в: {client_dir}\nТранскрипция с разделением по голосам...")

    ext = Path(storage_key).suffix or ".ogg"
    tmp_path = None

    try:
        fd, tmp_path = tempfile.mkstemp(suffix=ext, dir=tempfile.gettempdir())
        os.close(fd)
        storage.download_file(storage_key, tmp_path)

        results: dict[str, str] = {}

        print("  speechkit (диаризация)...", end=" ", flush=True)
        text_sk = _transcribe_speechkit_diarized(tmp_path, storage_key)
        if text_sk and text_sk.strip():
            results["speechkit"] = text_sk.strip()
            (client_dir / "transcript_speechkit_diarized.txt").write_text(
                text_sk.strip(), encoding="utf-8"
            )
            print(f"OK ({len(text_sk)} символов)")
        else:
            print("пропущен или пусто")

        print("  assemblyai (speaker_labels)...", end=" ", flush=True)
        text_aa = _transcribe_assemblyai_diarized(tmp_path, storage_key=storage_key)
        if text_aa and text_aa.strip():
            results["assemblyai"] = text_aa.strip()
            (client_dir / "transcript_assemblyai_diarized.txt").write_text(
                text_aa.strip(), encoding="utf-8"
            )
            print(f"OK ({len(text_aa)} символов)")
        else:
            print("пропущен или пусто")

        if not results:
            print("\nНет результата ни от одного транскрибера.")
            sys.exit(1)

        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        lines = [
            f"# Сравнение транскрипций (диалоги) — voice_id={voice_id} — {now}",
            f"# Длительность: {duration} сек",
            "",
        ]
        for name, text in results.items():
            lines.append(f"--- {name} ---")
            lines.append(text.strip())
            lines.append("")

        (client_dir / "transcript_comparison_diarized.txt").write_text(
            "\n".join(lines).strip(), encoding="utf-8"
        )
        print(f"\nГотово. Файлы в: {client_dir}")
        for f in sorted(client_dir.glob("transcript_*diarized*")):
            print(f"  - {f.name}")

    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


if __name__ == "__main__":
    main()
