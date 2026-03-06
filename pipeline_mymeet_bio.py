"""
Пайплайн: голосовое -> mymeet.ai транскрипция -> LLM биография -> сохранение в папку пользователя.

Также: онлайн-встреча по ссылке -> бот MyMeet записывает -> транскрипт -> тот же пайплайн (bio + вопросы).
Альтернатива Plaud: использует mymeet.ai для транскрипции (с диаризацией).
Шаблон research-interview подходит для биографических интервью.
"""

import logging
import os
import tempfile
import threading
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
) -> bool:
    """
    Синхронный пайплайн:
    1. Скачать аудио из S3
    2. mymeet.ai: транскрипция (research-interview)
    3. LLM: биографический текст
    4. Сохранить transcript.txt и bio_story.txt в папку пользователя
    5. Обновить transcript в БД

    Возвращает True при успехе.
    """
    mymeet_key = getattr(config, "MYMEET_API_KEY", None) or os.getenv("MYMEET_API_KEY", "")
    openai_key = getattr(config, "OPENAI_API_KEY", None) or os.getenv("OPENAI_API_KEY", "")

    if not mymeet_key:
        logger.warning("MYMEET_API_KEY не задан, пропускаем mymeet")
        return False

    client_dir = _ensure_client_dir(telegram_id, username)
    ext = Path(storage_key).suffix or ".ogg"
    tmp_path = None

    try:
        fd, tmp_path = tempfile.mkstemp(suffix=ext, dir=tempfile.gettempdir())
        os.close(fd)
        storage.download_file(storage_key, tmp_path)

        from mymeet_client import transcribe_via_mymeet

        transcript = transcribe_via_mymeet(
            tmp_path,
            api_key=mymeet_key,
            template_name="research-interview",
        )

        if not transcript or not transcript.strip():
            logger.warning("mymeet вернул пустой транскрипт")
            return False

        # Сохраняем сырой транскрипт (mymeet в заголовке для сравнения с plaud)
        transcript_path = client_dir / "transcript.txt"
        existing = transcript_path.read_text(encoding="utf-8") if transcript_path.exists() else ""
        new_block = f"\n\n--- Голосовое (voice_id={voice_id}) mymeet {datetime.now().strftime('%Y-%m-%d %H:%M')} ---\n{transcript}"
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
                questions_text = generate_clarifying_questions(bio_text, api_key=openai_key)
                if questions_text:
                    q_path = client_dir / "clarifying_questions.txt"
                    prev_q = q_path.read_text(encoding="utf-8") if q_path.exists() else ""
                    q_block = f"\n\n--- От {datetime.now().strftime('%Y-%m-%d %H:%M')} ---\n{questions_text}"
                    q_path.write_text((prev_q + q_block).strip(), encoding="utf-8")
                    logger.info("Уточняющие вопросы сохранены: %s", q_path)
        else:
            logger.info("OPENAI_API_KEY не задан, биография не генерируется")

        logger.info("Пайплайн (mymeet) завершён: %s", client_dir)
        return True

    except Exception as e:
        logger.exception("Пайплайн mymeet ошибка: %s", e)
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
) -> None:
    """Запускает пайплайн в фоновом потоке (не блокирует бота)."""
    import threading

    def _run():
        try:
            run_pipeline_sync(voice_id, storage_key, telegram_id, username)
        except Exception as e:
            logger.exception("Фоновый пайплайн mymeet: %s", e)

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    logger.info("Пайплайн (mymeet) запущен в фоне для voice_id=%s", voice_id)


def run_pipeline_from_transcript_sync(
    telegram_id: int,
    username: str | None,
    transcript: str,
    source_label: str = "mymeet-online",
) -> bool:
    """
    Пайплайн по готовому транскрипту (без аудио): сохранение в папку пользователя + LLM bio + уточняющие вопросы.
    Используется после записи онлайн-встречи MyMeet.
    Возвращает True при успехе.
    """
    if not transcript or not transcript.strip():
        logger.warning("run_pipeline_from_transcript: пустой транскрипт")
        return False
    openai_key = getattr(config, "OPENAI_API_KEY", None) or os.getenv("OPENAI_API_KEY", "")
    client_dir = _ensure_client_dir(telegram_id, username)
    transcript_path = client_dir / "transcript.txt"
    existing = transcript_path.read_text(encoding="utf-8") if transcript_path.exists() else ""
    new_block = (
        f"\n\n--- {source_label} {datetime.now().strftime('%Y-%m-%d %H:%M')} ---\n{transcript.strip()}"
    )
    transcript_path.write_text((existing + new_block).strip(), encoding="utf-8")

    if openai_key:
        from llm_bio import process_transcript_to_bio, generate_clarifying_questions
        bio_text = process_transcript_to_bio(transcript, api_key=openai_key)
        if bio_text:
            bio_path = client_dir / "bio_story.txt"
            prev = bio_path.read_text(encoding="utf-8") if bio_path.exists() else ""
            block = f"\n\n--- Обработка от {datetime.now().strftime('%Y-%m-%d %H:%M')} ---\n{bio_text}"
            bio_path.write_text((prev + block).strip(), encoding="utf-8")
            logger.info("Биография сохранена: %s", bio_path)
            questions_text = generate_clarifying_questions(bio_text, api_key=openai_key)
            if questions_text:
                q_path = client_dir / "clarifying_questions.txt"
                prev_q = q_path.read_text(encoding="utf-8") if q_path.exists() else ""
                q_block = f"\n\n--- От {datetime.now().strftime('%Y-%m-%d %H:%M')} ---\n{questions_text}"
                q_path.write_text((prev_q + q_block).strip(), encoding="utf-8")
                logger.info("Уточняющие вопросы сохранены: %s", q_path)
    else:
        logger.info("OPENAI_API_KEY не задан, биография не генерируется")
    logger.info("Пайплайн из транскрипта (mymeet-online) завершён: %s", client_dir)
    return True


def run_online_meeting_background(
    meeting_id: str,
    telegram_id: int,
    username: str | None,
    timeout_sec: int = 7200,
    poll_interval: int = 30,
) -> None:
    """
    В фоне ждёт обработки встречи MyMeet, забирает транскрипт и запускает пайплайн.
    Вызывать после record_meeting().
    """
    mymeet_key = getattr(config, "MYMEET_API_KEY", None) or os.getenv("MYMEET_API_KEY", "")
    if not mymeet_key:
        logger.warning("MYMEET_API_KEY не задан, онлайн-встреча не обработана")
        return

    def _run():
        try:
            from mymeet_client import (
                wait_for_processed,
                get_meeting_report,
                _extract_transcript_from_report,
            )
            if not wait_for_processed(meeting_id, mymeet_key, timeout_sec=timeout_sec, poll_interval=poll_interval):
                logger.warning("Онлайн-встреча %s не обработана (таймаут или failed)", meeting_id)
                return
            report = get_meeting_report(meeting_id, mymeet_key)
            if not report:
                logger.warning("Не удалось получить отчёт встречи %s", meeting_id)
                return
            transcript = _extract_transcript_from_report(report)
            if not transcript or not transcript.strip():
                logger.warning("Пустой транскрипт встречи %s", meeting_id)
                return
            run_pipeline_from_transcript_sync(
                telegram_id, username, transcript, source_label="mymeet-online",
            )
        except Exception as e:
            logger.exception("Пайплайн онлайн-встречи mymeet: %s", e)

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    logger.info("Ожидание обработки встречи mymeet meeting_id=%s для user %s", meeting_id, telegram_id)
