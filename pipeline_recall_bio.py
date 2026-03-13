"""
Пайплайн: Recall.ai онлайн-встреча → транскрипция → LLM биография → сохранение.

Бот Recall.ai подключается к встрече по URL, записывает и транскрибирует
через AssemblyAI (поддерживает русский язык, диаризацию).
После получения транскрипта — тот же пайплайн, что у mymeet: bio + вопросы.
"""

import logging
import os
import threading
from datetime import datetime
from pathlib import Path

import config

logger = logging.getLogger(__name__)

EXPORTS_DIR = Path(__file__).resolve().parent / "exports"


def _ensure_client_dir(telegram_id: int, username: str | None) -> Path:
    """Создаёт папку exports/client_{telegram_id}_{username}/."""
    username = (username or "unknown").replace("/", "_")
    folder = EXPORTS_DIR / f"client_{telegram_id}_{username}"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _get_recall_config() -> tuple[str, str]:
    """Возвращает (api_key, region). Берёт из config / env."""
    api_key = getattr(config, "RECALL_API_KEY", None) or os.getenv("RECALL_API_KEY", "")
    region = getattr(config, "RECALL_REGION", None) or os.getenv("RECALL_REGION", "us-east-1")
    return api_key, region


def run_pipeline_from_transcript_sync(
    telegram_id: int,
    username: str | None,
    transcript: str,
    source_label: str = "recall-online",
) -> bool:
    """
    Пайплайн по готовому транскрипту: сохранение + LLM bio + уточняющие вопросы.
    Совместим с pipeline_mymeet_bio.run_pipeline_from_transcript_sync.
    Возвращает True при успехе.
    """
    if not transcript or not transcript.strip():
        logger.warning("recall pipeline: пустой транскрипт")
        return False

    openai_key = getattr(config, "OPENAI_API_KEY", None) or os.getenv("OPENAI_API_KEY", "")
    client_dir = _ensure_client_dir(telegram_id, username)

    # Сохраняем транскрипт
    transcript_path = client_dir / "transcript.txt"
    existing = transcript_path.read_text(encoding="utf-8") if transcript_path.exists() else ""
    new_block = (
        f"\n\n--- {source_label} {datetime.now().strftime('%Y-%m-%d %H:%M')} ---\n{transcript.strip()}"
    )
    transcript_path.write_text((existing + new_block).strip(), encoding="utf-8")

    if not openai_key:
        logger.info("OPENAI_API_KEY не задан, биография не генерируется")
        return True

    try:
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
    except Exception as e:
        logger.exception("recall LLM pipeline error: %s", e)

    logger.info("Пайплайн recall (онлайн-встреча) завершён: %s", client_dir)
    return True


def run_online_meeting_background(
    bot_id: str,
    telegram_id: int,
    username: str | None,
    timeout_sec: int = 7200,
    poll_interval: int = 15,
) -> None:
    """
    В фоне ждёт завершения записи Recall.ai, забирает транскрипт и запускает пайплайн.
    Вызывать после recall_client.create_bot().

    Аналог pipeline_mymeet_bio.run_online_meeting_background.
    """
    api_key, region = _get_recall_config()
    if not api_key:
        logger.warning("RECALL_API_KEY не задан, онлайн-встреча не обработана")
        return

    def _run() -> None:
        try:
            from recall_client import wait_for_done, get_transcript

            if not wait_for_done(
                bot_id, api_key, region=region,
                timeout_sec=timeout_sec, poll_interval=poll_interval,
            ):
                logger.warning("recall bot %s не завершён (таймаут или fatal)", bot_id)
                return

            transcript = get_transcript(bot_id, api_key, region=region)
            if not transcript or not transcript.strip():
                logger.warning("recall bot %s: пустой транскрипт", bot_id)
                return

            run_pipeline_from_transcript_sync(
                telegram_id, username, transcript, source_label="recall-online",
            )
        except Exception as e:
            logger.exception("Пайплайн recall онлайн-встречи: %s", e)

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    logger.info("Ожидание записи recall bot_id=%s для user %s", bot_id, telegram_id)
