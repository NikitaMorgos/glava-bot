#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stage 1 — Транскрипция аудиофайлов Дмитриева.

Файлы:
  папа.m4a        — основная запись (33 МБ)
  папад1-3.m4a   — источник Д (рассказчик 1, 3 файла)
  папак1-2.m4a   — источник К (рассказчик 2, 2 файла)

Результаты сохраняются в exports/transcripts/dmitriev/.
После завершения объединяет все тексты в dmitriev_combined_transcript.txt.

Использование:
    python scripts/transcribe_dmitriev.py
    python scripts/transcribe_dmitriev.py --skip-existing   # пропустить уже готовые
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

AUDIO_DIR = ROOT / "exports" / "dmitriev_audio"
OUT_DIR = ROOT / "exports" / "transcripts" / "dmitriev"

# Описание файлов: (filename, source_label, narrator_hint)
# Уточни narrator_hint когда узнаешь кто рассказывает
AUDIO_FILES = [
    ("папа.m4a",   "ОСНОВНАЯ",  "Основная запись"),
    ("папад1.m4a", "ИСТОЧНИК_Д",  "Рассказчик Д, часть 1"),
    ("папад2.m4a", "ИСТОЧНИК_Д",  "Рассказчик Д, часть 2"),
    ("папад3.m4a", "ИСТОЧНИК_Д",  "Рассказчик Д, часть 3"),
    ("папак1.m4a", "ИСТОЧНИК_К",  "Рассказчик К, часть 1"),
    ("папак2.m4a", "ИСТОЧНИК_К",  "Рассказчик К, часть 2"),
]


def transcribe_file(audio_path: Path, api_key: str, speaker_labels: bool = True) -> str:
    """Транскрибирует один файл через AssemblyAI."""
    try:
        import assemblyai as aai
    except ImportError:
        logger.error("pip install assemblyai")
        return ""

    aai.settings.api_key = api_key

    config = aai.TranscriptionConfig(
        speech_models=["universal-3-pro", "universal-2"],
        language_code="ru",
        speaker_labels=speaker_labels,
        punctuate=True,
        format_text=True,
    )

    logger.info("Загружаю и транскрибирую: %s (%.1f МБ)...",
                audio_path.name, audio_path.stat().st_size / 1024 / 1024)

    transcriber = aai.Transcriber()
    transcript = transcriber.transcribe(str(audio_path), config=config)

    if transcript.status == aai.TranscriptStatus.error:
        logger.error("Ошибка AssemblyAI для %s: %s", audio_path.name, transcript.error)
        return ""

    if speaker_labels and transcript.utterances:
        lines = []
        for utt in transcript.utterances:
            lines.append(f"Спикер {utt.speaker}: {utt.text}")
        return "\n".join(lines)
    else:
        return transcript.text or ""


def main():
    parser = argparse.ArgumentParser()
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

    for filename, source_label, narrator_hint in AUDIO_FILES:
        audio_path = AUDIO_DIR / filename
        out_txt = OUT_DIR / (Path(filename).stem + "_transcript.txt")
        out_meta = OUT_DIR / (Path(filename).stem + "_meta.json")

        if not audio_path.exists():
            logger.warning("Файл не найден, пропускаю: %s", audio_path)
            continue

        if args.skip_existing and out_txt.exists():
            logger.info("Пропускаю (уже есть): %s", out_txt.name)
            text = out_txt.read_text(encoding="utf-8")
            results.append((source_label, narrator_hint, filename, text))
            total_chars += len(text)
            continue

        # Большой файл (папа.m4a) всегда с диаризацией
        use_speakers = True

        t0 = time.time()
        text = transcribe_file(audio_path, api_key, speaker_labels=use_speakers)
        elapsed = time.time() - t0

        if not text:
            logger.error("Транскрипт пустой для %s, пропускаю", filename)
            continue

        out_txt.write_text(text, encoding="utf-8")
        meta = {
            "filename": filename,
            "source_label": source_label,
            "narrator_hint": narrator_hint,
            "chars": len(text),
            "elapsed_s": round(elapsed, 1),
            "size_mb": round(audio_path.stat().st_size / 1024 / 1024, 1),
        }
        out_meta.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

        logger.info("[OK] %s → %d символов за %.0fс", filename, len(text), elapsed)
        total_chars += len(text)
        results.append((source_label, narrator_hint, filename, text))

    if not results:
        print("[ERROR] Ни один файл не транскрибирован")
        sys.exit(1)

    # Объединённый транскрипт
    combined_path = ROOT / "exports" / "transcripts" / "dmitriev_combined_transcript.txt"
    sections = []
    for source_label, narrator_hint, filename, text in results:
        header = f"\n{'='*60}\n[{source_label}] {narrator_hint} ({filename})\n{'='*60}\n"
        sections.append(header + text)

    combined_text = "\n\n".join(sections)
    combined_path.write_text(combined_text, encoding="utf-8")

    print(f"\n{'='*60}")
    print(f"ТРАНСКРИПЦИЯ ЗАВЕРШЕНА")
    print(f"{'='*60}")
    print(f"  Файлов обработано: {len(results)}")
    print(f"  Итого символов: {total_chars:,}")
    print(f"  Объединённый транскрипт: {combined_path}")
    print(f"  Отдельные файлы: {OUT_DIR}")
    print(f"\nСледующий шаг:")
    print(f"  python scripts/test_stage1_dmitriev.py")


if __name__ == "__main__":
    main()
