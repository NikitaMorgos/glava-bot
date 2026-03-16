"""
Клиент AssemblyAI API для транскрипции.

Поддерживает локальные файлы и URL.
API: https://www.assemblyai.com/docs
Ключ: https://www.assemblyai.com/dashboard
"""

import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)

# Таймаут для загрузки больших файлов (секунды)
UPLOAD_TIMEOUT = 600
MAX_RETRIES = 3
RETRY_DELAY = 10


def transcribe_via_assemblyai(
    audio_path: str = "",
    api_key: str = "",
    language_code: str = "ru",
    speaker_labels: bool = False,
    audio_url: str | None = None,
) -> str:
    """
    Транскрибирует аудио через AssemblyAI.

    Либо передайте audio_path (локальный файл), либо audio_url (прямая ссылка на файл).
    Для длинных файлов предпочтительно audio_url (presigned URL из S3) — не нужно загружать с машины.

    audio_path — путь к локальному файлу (mp3, ogg, m4a, wav и др.)
    audio_url — прямая URL на аудио/видео (AssemblyAI сам скачает). Рекомендуется для файлов >10–15 мин.
    api_key — API key из dashboard.assemblyai.com
    language_code — ru, en и др.
    speaker_labels — если True, возвращает диалог (Спикер A: ... Спикер B: ...).

    Возвращает текст транскрипта или пустую строку при ошибке.
    """
    if not api_key:
        logger.warning("AssemblyAI: api_key не задан")
        return ""

    use_url = (audio_url or "").strip().startswith("http")
    if not use_url:
        path = Path(audio_path or "")
        if not path.exists():
            logger.error("AssemblyAI: файл не найден: %s", audio_path)
            return ""

    try:
        import assemblyai as aai
    except ImportError:
        logger.warning("AssemblyAI: pip install assemblyai")
        return ""

    try:
        aai.settings.api_key = api_key
        if getattr(aai.settings, "http_timeout", None) is None or aai.settings.http_timeout < UPLOAD_TIMEOUT:
            aai.settings.http_timeout = UPLOAD_TIMEOUT
        cfg = aai.TranscriptionConfig(
            language_code=language_code,
            speech_models=["universal-2"],
            speaker_labels=speaker_labels,
        )
        transcriber = aai.Transcriber()
        transcript = None
        for attempt in range(MAX_RETRIES):
            try:
                if use_url:
                    transcript = transcriber.transcribe(audio_url, config=cfg)
                else:
                    transcript = transcriber.transcribe(str(Path(audio_path)), config=cfg)
                break
            except (Exception, OSError) as e:
                if attempt + 1 >= MAX_RETRIES:
                    raise
                logger.warning("AssemblyAI загрузка/запрос (попытка %s/%s): %s. Повтор через %s с...", attempt + 1, MAX_RETRIES, e, RETRY_DELAY)
                time.sleep(RETRY_DELAY)

        if transcript.status == aai.TranscriptStatus.error:
            logger.warning("AssemblyAI: ошибка транскрипции: %s", transcript.error)
            return ""

        if speaker_labels and getattr(transcript, "utterances", None):
            return _format_utterances_dialogue(transcript.utterances)
        return (transcript.text or "").strip()
    except Exception as e:
        logger.exception("AssemblyAI: %s", e)
        return ""


def _format_utterances_dialogue(utterances) -> str:
    """Форматирует utterances AssemblyAI в вид диалога: Спикер A: ... Спикер B: ..."""
    lines = []
    for u in utterances:
        speaker = getattr(u, "speaker", None) or getattr(u, "speaker_label", "?")
        text = (getattr(u, "text", None) or "").strip()
        if text:
            lines.append(f"Спикер {speaker}: {text}")
    return "\n".join(lines)
