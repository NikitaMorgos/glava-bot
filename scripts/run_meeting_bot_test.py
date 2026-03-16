#!/usr/bin/env python3
"""
Тестовый прогон meeting_bot — запись онлайн-созвона.

Запуск на Linux (pulseaudio, ffmpeg, playwright):
    cd /opt/glava && source venv/bin/activate
    pip install playwright && playwright install chromium
    python scripts/run_meeting_bot_test.py "https://zoom.us/j/123456789" 60

Параметры:
  URL встречи (Zoom, Telemost и др.)
  Длительность в секундах (по умолчанию 60 для теста)
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from meeting_bot import record_meeting


def main():
    if len(sys.argv) < 2:
        print("Использование: python scripts/run_meeting_bot_test.py <URL> [duration_sec]")
        print("Пример: python scripts/run_meeting_bot_test.py 'https://zoom.us/j/123' 60")
        sys.exit(1)

    url = sys.argv[1].strip()
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 60

    if not url.startswith(("http://", "https://")):
        print("URL должен начинаться с http:// или https://")
        sys.exit(1)

    print(f"URL: {url}")
    print(f"Длительность: {duration} сек")
    print("Запуск записи (Ctrl+C для остановки)...")

    out = record_meeting(url, duration_sec=duration)
    if out:
        print(f"OK — запись сохранена: {out}")
    else:
        print("Ошибка записи. Проверь: pulseaudio, parec, ffmpeg, playwright.")
        sys.exit(1)


if __name__ == "__main__":
    main()
