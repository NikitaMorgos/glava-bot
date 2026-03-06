"""
Пайплайн: голосовое -> SpeechKit/Whisper транскрипция -> LLM биография -> сохранение в папку пользователя.

Альтернатива Plaud: использует Yandex SpeechKit (или Whisper) для транскрипции.
Запускается автоматически после сохранения голосового, когда Plaud недоступен.
"""

import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path

import config
import db
import storage

logger = logging.getLogger(__name__)

EXPORTS_DIR = Path(__file__).resolve().parent / "exports"


def _ensure_client_dir(telegram_id: int, username: str | None) -> Path:
    """Создаёт папку exports/client_{telegram_id}_{username}/."""
    username = (username or "unknown").replace("/", "_")
    folder = EXPORTS_DIR / f"client_{telegram_id}_{username}"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def run_pipeline_sync(
    voice_id: int,
    storage_key: str,
    telegram_id: int,
    username: str | None,
    use_diarization: bool = False,
) -> bool:
    """
    Синхронный пайплайн:
    1. Скачать аудио из S3
    2. Транскрипция: SpeechKit (если YANDEX_API_KEY) или Whisper
    3. LLM: биографический текст по промпту Даши
    4. Сохранить transcript.txt и bio_story.txt в папку пользователя
    5. Обновить transcript в БД

    use_diarization: если True — transcribe_with_diarization (нужен HUGGINGFACE_TOKEN или Resemblyzer).
    """
    openai_key = getattr(config, "OPENAI_API_KEY", None) or os.getenv("OPENAI_API_KEY", "")

    client_dir = _ensure_client_dir(telegram_id, username)
    ext = Path(storage_key).suffix or ".ogg"
    tmp_path = None

    try:
        fd, tmp_path = tempfile.mkstemp(suffix=ext, dir=tempfile.gettempdir())
        os.close(fd)
        storage.download_file(storage_key, tmp_path)

        # Транскрипция: SpeechKit или Whisper
        import transcribe as transcribe_mod

        if use_diarization and hasattr(transcribe_mod, "transcribe_with_diarization"):
            try:
                segments = transcribe_mod.transcribe_with_diarization(
                    tmp_path, storage_key=storage_key
                )
                transcript = (
                    transcribe_mod.format_diarized_transcript(segments, include_timestamps=False)
                    if segments
                    else ""
                )
            except Exception as e:
                logger.warning("Диаризация не удалась: %s, пробуем обычную транскрипцию", e)
                transcript = transcribe_mod.transcribe_audio(tmp_path, storage_key=storage_key)
        else:
            transcript = transcribe_mod.transcribe_audio(tmp_path, storage_key=storage_key)

        if not transcript or not transcript.strip():
            logger.warning("Транскрипция пуста")
            return False

        # Сохраняем сырой транскрипт
        transcript_path = client_dir / "transcript.txt"
        existing = transcript_path.read_text(encoding="utf-8") if transcript_path.exists() else ""
        new_block = f"\n\n--- Голосовое (voice_id={voice_id}) {datetime.now().strftime('%Y-%m-%d %H:%M')} ---\n{transcript}"
        transcript_path.write_text((existing + new_block).strip(), encoding="utf-8")

        # Обновляем БД
        db.update_voice_transcript(voice_id, transcript)

        # LLM — биографический текст и уточняющие вопросы (если есть ключ)
        if openai_key:
            from llm_bio import process_transcript_to_bio, generate_clarifying_questions

            bio_text = process_transcript_to_bio(transcript, api_key=openai_key)
            if bio_text:
                bio_path = client_dir / "bio_story.txt"
                prev = bio_path.read_text(encoding="utf-8") if bio_path.exists() else ""
                block = f"\n\n--- Обработка от {datetime.now().strftime('%Y-%m-%d %H:%M')} ---\n{bio_text}"
                bio_path.write_text((prev + block).strip(), encoding="utf-8")
                logger.info("Биография сохранена: %s", bio_path)
                # Уточняющие вопросы по обработанному интервью (промпт из WEEEK)
                questions_text = generate_clarifying_questions(bio_text, api_key=openai_key)
                if questions_text:
                    q_path = client_dir / "clarifying_questions.txt"
                    prev_q = q_path.read_text(encoding="utf-8") if q_path.exists() else ""
                    q_block = f"\n\n--- От {datetime.now().strftime('%Y-%m-%d %H:%M')} ---\n{questions_text}"
                    q_path.write_text((prev_q + q_block).strip(), encoding="utf-8")
                    logger.info("Уточняющие вопросы сохранены: %s", q_path)
        else:
            logger.info("OPENAI_API_KEY не задан, биография не генерируется")

        logger.info("Пайплайн (SpeechKit/Whisper) завершён: %s", client_dir)
        return True

    except Exception as e:
        logger.exception("Пайплайн ошибка: %s", e)
        return False
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def run_pipeline_background(
    voice_id: int,
    storage_key: str,
    telegram_id: int,
    username: str | None,
    use_diarization: bool = False,
) -> None:
    """Запускает пайплайн в фоновом потоке (не блокирует бота)."""
    import threading

    def _run():
        try:
            run_pipeline_sync(
                voice_id, storage_key, telegram_id, username, use_diarization=use_diarization
            )
        except Exception as e:
            logger.exception("Фоновый пайплайн: %s", e)

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    logger.info("Пайплайн (transcribe) запущен в фоне для voice_id=%s", voice_id)
