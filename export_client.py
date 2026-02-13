"""
Экспорт данных клиента в единую папку для верстки.

Для Даши — чтобы работать с данными без вопросов.

Запуск:
  python export_client.py           — показать список клиентов
  python export_client.py 123456789 — экспортировать клиента (telegram_id)
  python export_client.py 123456789 --no-transcribe — без транскрибации (если Whisper не работает)
  python export_client.py 123456789 --diarize      — с диаризацией (разделение по спикерам)

Результат: папка exports/client_123456789_username/
  voice/        — голосовые (001.ogg, 002.ogg...)
  photos/       — фото (001.jpg, 002.jpg...)
  transcript.txt — текст интервью (транскрипция голосовых; при --diarize — с метками Спикер 1, Спикер 2...)
  captions.txt  — подписи к фото
  manifest.txt  — описание содержимого
"""

import logging
import os
import sys
from pathlib import Path

# Кэш в папку проекта — избегаем WinError 5 на системном .cache
_project_root = Path(__file__).resolve().parent
_cache_dir = _project_root / ".cache"
_cache_dir.mkdir(exist_ok=True)
for _var in ("HF_HOME", "XDG_CACHE_HOME", "TORCH_HOME", "TRANSFORMERS_CACHE"):
    os.environ.setdefault(_var, str(_cache_dir))

from dotenv import load_dotenv
load_dotenv()

import config
import db
import storage

logging.basicConfig(level=logging.INFO)

EXPORTS_DIR = Path(__file__).parent / "exports"


def list_clients() -> None:
    """Показать список клиентов."""
    clients = db.get_all_clients()
    if not clients:
        print("Клиентов пока нет.")
        return
    print("\nКлиенты (telegram_id — голосовых — фото с подписями):\n")
    for c in clients:
        name = c.get("username") or "(без username)"
        print(f"  {c['telegram_id']}  @{name}  — {c['voice_count']} голос., {c['photo_count']} фото")
    print(f"\nЭкспорт: python export_client.py TELEGRAM_ID")


def export_client(telegram_id: int, transcribe: bool = True, diarize: bool = False) -> Path | None:
    """Экспортировать данные клиента в папку."""
    user, voices, photos = db.get_user_all_data(telegram_id)
    if not user:
        print(f"Клиент с telegram_id={telegram_id} не найден.")
        return None

    username = (user.get("username") or "unknown").replace("/", "_")
    folder_name = f"client_{telegram_id}_{username}"
    client_dir = EXPORTS_DIR / folder_name
    voice_dir = client_dir / "voice"
    photos_dir = client_dir / "photos"

    voice_dir.mkdir(parents=True, exist_ok=True)
    photos_dir.mkdir(parents=True, exist_ok=True)

    # Скачиваем голосовые и транскрибируем при необходимости
    for i, v in enumerate(voices, 1):
        num = str(i).zfill(3)
        ext = Path(v["storage_key"]).suffix or ".ogg"
        local_path = voice_dir / f"{num}{ext}"
        storage.download_file(v["storage_key"], str(local_path))

        # Транскрибация: с диаризацией или обычная (SpeechKit / Whisper)
        if transcribe and not v.get("transcript"):
            try:
                import transcribe as transcribe_mod
                if diarize and hasattr(transcribe_mod, "transcribe_with_diarization"):
                    segments = transcribe_mod.transcribe_with_diarization(
                        str(local_path), storage_key=v["storage_key"]
                    )
                    if segments:
                        transcript = transcribe_mod.format_diarized_transcript(segments, include_timestamps=False)
                    else:
                        transcript = transcribe_mod.transcribe_audio(str(local_path), storage_key=v["storage_key"])
                else:
                    transcript = transcribe_mod.transcribe_audio(
                        str(local_path), storage_key=v["storage_key"]
                    )
                if transcript:
                    db.update_voice_transcript(v["id"], transcript)
                    v["transcript"] = transcript
            except ImportError:
                pass
            except Exception as e:
                logging.warning("Транскрибация не удалась: %s", e)
        v.setdefault("transcript", v.get("transcript", ""))

    # Скачиваем фото и собираем подписи
    caption_lines = []
    for i, p in enumerate(photos, 1):
        num = str(i).zfill(3)
        ext = Path(p["storage_key"]).suffix or ".jpg"
        local_path = photos_dir / f"{num}{ext}"
        storage.download_file(p["storage_key"], str(local_path))
        caption = p.get("caption") or ""
        caption_lines.append(f"{num}{ext}: {caption}")

    # manifest.txt
    manifest_path = client_dir / "manifest.txt"
    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write(f"Клиент: telegram_id={telegram_id}, @{user.get('username') or '-'}\n")
        f.write(f"Дата экспорта: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write(f"Голосовых: {len(voices)}\n")
        for i, v in enumerate(voices, 1):
            dur = f" {v['duration']} сек" if v.get("duration") else ""
            f.write(f"  {str(i).zfill(3)}{Path(v['storage_key']).suffix or '.ogg'}{dur}\n")
        f.write(f"\nФото с подписями: {len(photos)}\n")
        for i, p in enumerate(photos, 1):
            f.write(f"  {str(i).zfill(3)}{Path(p['storage_key']).suffix or '.jpg'}: {p.get('caption') or ''}\n")

    # captions.txt — только подписи (удобно для верстки)
    captions_path = client_dir / "captions.txt"
    with open(captions_path, "w", encoding="utf-8") as f:
        f.write("\n".join(caption_lines))

    # transcript.txt — полный текст интервью (все голосовые подряд)
    transcript_parts = []
    for i, v in enumerate(voices, 1):
        text = v.get("transcript") or ""
        if text:
            transcript_parts.append(f"--- Голосовое {i} ---\n{text}")
    if transcript_parts:
        transcript_path = client_dir / "transcript.txt"
        with open(transcript_path, "w", encoding="utf-8") as f:
            f.write("\n\n".join(transcript_parts))

    print(f"Готово: {client_dir}")
    print(f"  voice/ — {len(voices)} файлов")
    print(f"  photos/ — {len(photos)} файлов")
    has_transcript = any(v.get("transcript") for v in voices)
    print(f"  transcript.txt, manifest.txt, captions.txt" + (" (с транскрипцией)" if has_transcript else ""))
    return client_dir


def main() -> None:
    EXPORTS_DIR.mkdir(exist_ok=True)

    if len(sys.argv) < 2:
        list_clients()
        return

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]

    if not args or args[0].lower() in ("list", "-l", "-list"):
        list_clients()
        return

    try:
        telegram_id = int(args[0])
    except ValueError:
        print("Укажи telegram_id числом, например: python export_client.py 123456789")
        sys.exit(1)

    transcribe = "--no-transcribe" not in flags
    diarize = "--diarize" in flags
    export_client(telegram_id, transcribe=transcribe, diarize=diarize)


if __name__ == "__main__":
    main()
