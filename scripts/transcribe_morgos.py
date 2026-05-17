#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Транскрипция аудиозаписей для Григория Моргося (деда Гриши).

Рассказчик: внук Никита (пересказывает со слов отца Вадима, сына Григория).

Файлы:
  Новая запись 31.m4a  — запись 1
  Новая запись 32.m4a  — запись 2

Результаты сохраняются в exports/transcripts/morgos/.

Использование:
    python scripts/transcribe_morgos.py
    python scripts/transcribe_morgos.py --skip-existing
"""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Аудиофайлы — скачаны в Downloads
DOWNLOADS = Path.home() / "Downloads"

OUT_DIR = ROOT / "exports" / "transcripts" / "morgos"

# (путь к файлу, метка, описание)
AUDIO_FILES = [
    (DOWNLOADS / "Новая запись 31.m4a", "ЗАПИСЬ_31", "Никита пересказывает (часть 1)"),
    (DOWNLOADS / "Новая запись 32.m4a", "ЗАПИСЬ_32", "Никита пересказывает (часть 2)"),
]


def transcribe_file(audio_path: Path, api_key: str) -> str:
    """Транскрибирует один файл через AssemblyAI (русский, с диаризацией)."""
    try:
        import assemblyai as aai
    except ImportError:
        logger.error("pip install assemblyai")
        return ""

    aai.settings.api_key = api_key
    if getattr(aai.settings, "http_timeout", None) is None or aai.settings.http_timeout < 600:
        aai.settings.http_timeout = 600

    config = aai.TranscriptionConfig(
        language_code="ru",
        speech_models=["universal-3-pro", "universal-2"],
        speaker_labels=True,
        punctuate=True,
        format_text=True,
    )

    size_mb = audio_path.stat().st_size / 1024 / 1024
    logger.info("Транскрибирую: %s (%.1f МБ)...", audio_path.name, size_mb)

    transcriber = aai.Transcriber()
    transcript = transcriber.transcribe(str(audio_path), config=config)

    if transcript.status == aai.TranscriptStatus.error:
        logger.error("Ошибка AssemblyAI для %s: %s", audio_path.name, transcript.error)
        return ""

    if transcript.utterances:
        lines = [f"Спикер {u.speaker}: {u.text}" for u in transcript.utterances]
        return "\n".join(lines)

    return transcript.text or ""


def main():
    parser = argparse.ArgumentParser(description="Транскрипция записей Моргося")
    parser.add_argument("--skip-existing", action="store_true",
                        help="Пропустить файлы у которых уже есть транскрипт")
    args = parser.parse_args()

    api_key = os.getenv("ASSEMBLYAI_API_KEY", "")
    if not api_key:
        print("[ERROR] ASSEMBLYAI_API_KEY не задан в .env")
        sys.exit(1)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    results = []
    total_chars = 0

    for audio_path, label, description in AUDIO_FILES:
        stem = audio_path.stem.replace(" ", "_")
        out_txt = OUT_DIR / f"{stem}_transcript.txt"
        out_meta = OUT_DIR / f"{stem}_meta.json"

        if not audio_path.exists():
            logger.warning("Файл не найден, пропускаю: %s", audio_path)
            continue

        if args.skip_existing and out_txt.exists():
            logger.info("Пропускаю (уже есть): %s", out_txt.name)
            text = out_txt.read_text(encoding="utf-8")
            results.append((label, description, audio_path.name, text))
            total_chars += len(text)
            continue

        t0 = time.time()
        text = transcribe_file(audio_path, api_key)
        elapsed = time.time() - t0

        if not text:
            logger.error("Транскрипт пустой для %s", audio_path.name)
            continue

        out_txt.write_text(text, encoding="utf-8")
        meta = {
            "filename": audio_path.name,
            "label": label,
            "description": description,
            "subject": "Григорий Моргось (деда Гриша)",
            "narrator": "Никита (внук), пересказывает со слов отца Вадима",
            "chars": len(text),
            "elapsed_s": round(elapsed, 1),
            "size_mb": round(audio_path.stat().st_size / 1024 / 1024, 1),
        }
        out_meta.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("[OK] %s → %d символов за %.0fс", audio_path.name, len(text), elapsed)

        total_chars += len(text)
        results.append((label, description, audio_path.name, text))

    if not results:
        print("[ERROR] Ни один файл не транскрибирован")
        sys.exit(1)

    # Объединённый транскрипт
    combined_path = OUT_DIR / "morgos_combined_transcript.txt"
    sections = []
    for label, description, filename, text in results:
        header = f"\n{'='*60}\n[{label}] {description} ({filename})\n{'='*60}\n"
        sections.append(header + text)

    combined_path.write_text("\n\n".join(sections), encoding="utf-8")

    print(f"\n{'='*60}")
    print(f"ТРАНСКРИПЦИЯ ЗАВЕРШЕНА — Григорий Моргось")
    print(f"{'='*60}")
    print(f"  Файлов обработано: {len(results)}")
    print(f"  Итого символов:    {total_chars:,}")
    print(f"  Объединённый:      {combined_path}")
    print(f"  Отдельные файлы:   {OUT_DIR}")
    print(f"\nСледующий шаг: смотрим транскрипт, затем запускаем Stage 1 bio-pipeline")


if __name__ == "__main__":
    main()
