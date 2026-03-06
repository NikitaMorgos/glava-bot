"""
Транскрибация голосовых.

Приоритет:
1. Yandex SpeechKit (если YANDEX_API_KEY задан) — облако, работает с OGG
2. Whisper локально (если установлен) — pip install openai-whisper, ffmpeg

Диаризация (разделение по спикерам):
- С HuggingFace: faster-whisper + pyannote-audio (HUGGINGFACE_TOKEN)
- Без HuggingFace: Resemblyzer + Whisper (pip install Resemblyzer) — без регистрации
"""

import logging
import re
import time
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

_whisper_model = None
_whisper_available = None

SPEECHKIT_RECOGNIZE_URL = "https://transcribe.api.cloud.yandex.net/speech/stt/v2/longRunningRecognize"
SPEECHKIT_OPERATIONS_URL = "https://operation.api.cloud.yandex.net/operations/"


def _check_whisper():
    global _whisper_available
    if _whisper_available is None:
        try:
            import whisper  # noqa: F401
            _whisper_available = True
        except ImportError:
            _whisper_available = False
    return _whisper_available


def _get_model():
    global _whisper_model
    if _whisper_model is None:
        import whisper
        logger.info("Загрузка модели Whisper (base)...")
        _whisper_model = whisper.load_model("base")
    return _whisper_model


# SpeechKit поддерживает: OGG_OPUS, MP3, LINEAR16_PCM. M4A — нет, конвертируем в OGG.
_SPEECHKIT_UNSUPPORTED = {".m4a", ".mp4", ".aac", ".wav"}


def _convert_to_ogg_opus(source_path: str) -> str:
    """
    Конвертирует аудио в OGG Opus через ffmpeg.
    Возвращает путь к временному .ogg файлу.
    """
    import shutil
    import subprocess
    import tempfile

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg не найден. Установите: https://ffmpeg.org/download.html")

    fd, out_path = tempfile.mkstemp(suffix=".ogg", dir=tempfile.gettempdir())
    try:
        import os
        os.close(fd)
        subprocess.run(
            [ffmpeg, "-y", "-i", source_path, "-c:a", "libopus", "-b:a", "64k", out_path],
            check=True,
            capture_output=True,
        )
        return out_path
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        Path(out_path).unlink(missing_ok=True)
        raise RuntimeError(f"Конвертация в OGG не удалась: {e}") from e


def transcribe_via_speechkit(storage_key: str, audio_path: str | None = None) -> str:
    """
    Транскрибация через Yandex SpeechKit.
    API v2 принимает только URI (presigned URL). Сервисному аккаунту glava-speechkit
    нужна роль storage.viewer на бакет — иначе Object Storage вернёт 403 при чтении.

    Для m4a/mp4/aac: если передан audio_path, конвертирует в OGG и загружает во временный объект.
    """
    import config
    import storage
    import uuid

    api_key = getattr(config, "YANDEX_API_KEY", "") or ""
    if not api_key:
        return ""

    ext = (Path(storage_key).suffix or "").lower()
    use_uri_key = storage_key
    tried_convert = False

    # Конвертация для неподдерживаемых форматов (m4a, mp4, aac, wav)
    if ext in _SPEECHKIT_UNSUPPORTED and audio_path and Path(audio_path).exists():
        temp_ogg = _convert_to_ogg_opus(audio_path)
        temp_key = f"temp/transcribe_{uuid.uuid4().hex}.ogg"
        try:
            storage.upload_file_to_key(temp_ogg, temp_key)
            use_uri_key = temp_key
            tried_convert = True
        finally:
            Path(temp_ogg).unlink(missing_ok=True)

    headers = {"Authorization": f"Api-Key {api_key}"}

    def _do_recognize() -> "requests.Response":
        url = storage.get_presigned_download_url(use_uri_key, expires_in=3600)
        encoding = "OGG_OPUS" if tried_convert or use_uri_key != storage_key else ("MP3" if ext == ".mp3" else "OGG_OPUS")
        body = {
            "config": {"specification": {"audioEncoding": encoding, "languageCode": "ru-RU"}},
            "audio": {"uri": url},
        }
        return requests.post(SPEECHKIT_RECOGNIZE_URL, headers=headers, json=body, timeout=30)

    resp = _do_recognize()
    if not resp.ok:
        try:
            err_json = resp.json()
            err_text = str(err_json.get("message", err_json))
        except Exception:
            err_text = resp.text
        # "ogg header has not been found" — файл .ogg может быть с неправильным заголовком, конвертируем
        if resp.status_code == 400 and "ogg" in err_text.lower() and audio_path and Path(audio_path).exists() and not tried_convert:
            logger.info("SpeechKit не распознал заголовок OGG, конвертируем через ffmpeg и повторяем")
            temp_ogg = _convert_to_ogg_opus(audio_path)
            temp_key = f"temp/transcribe_{uuid.uuid4().hex}.ogg"
            try:
                storage.upload_file_to_key(temp_ogg, temp_key)
                use_uri_key = temp_key
                tried_convert = True
                resp = _do_recognize()
            finally:
                Path(temp_ogg).unlink(missing_ok=True)
        if not resp.ok:
            try:
                err_body = resp.json()
            except Exception:
                err_body = resp.text[:500]
            logger.warning("SpeechKit %s: %s", resp.status_code, err_body)
            resp.raise_for_status()
    op = resp.json()
    op_id = op.get("id")
    if not op_id:
        raise ValueError("SpeechKit: нет id операции")

    try:
        # Длинные файлы (40+ мин) требуют до ~20 мин обработки
        for _ in range(600):
            time.sleep(2)
            status = requests.get(SPEECHKIT_OPERATIONS_URL + op_id, headers=headers, timeout=120)
            status.raise_for_status()
            data = status.json()
            if data.get("done"):
                chunks = data.get("response", {}).get("chunks", [])
                parts = []
                for ch in chunks:
                    for alt in ch.get("alternatives", []):
                        text = alt.get("text", "").strip()
                        if text:
                            parts.append(text)
                return " ".join(parts)
        raise TimeoutError("SpeechKit: таймаут распознавания")
    finally:
        if use_uri_key != storage_key:
            try:
                storage.delete_object(use_uri_key)
            except Exception as e:
                logger.debug("Не удалось удалить временный объект %s: %s", use_uri_key, e)


def _parse_speechkit_time(s: str | float) -> float:
    """Парсит длительность из формата SpeechKit: '1.5s', '0.001234s' или число -> секунды."""
    if s is None:
        return 0.0
    if isinstance(s, (int, float)):
        return float(s)
    s = str(s).strip().rstrip("s")
    try:
        return float(s)
    except ValueError:
        return 0.0


def _split_text_to_utterances(text: str, min_parts: int = 5, max_parts: int = 80) -> list[str]:
    """
    Разбивает текст на реплики по предложениям/фразам для распределения по спикерам.
    Возвращает список непустых строк.
    """
    if not (text or "").strip():
        return []
    text = text.strip()
    # Разбить по концу предложения или по переносам
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    parts = [p.strip() for p in parts if p.strip()]
    if not parts:
        parts = [text]
    # Одна длинная часть — режем по запятым/точке с запятой
    if len(parts) < min_parts and len(parts) == 1 and len(text) > 200:
        parts = re.split(r"(?<=[,;:])\s+", text)
        parts = [p.strip() for p in parts if p.strip()] or [text]
    # Всё ещё одна часть (нет знаков препинания) — режем по длине ~250 символов по пробелам
    if len(parts) < 2 and len(text) > 300:
        chunk_size = max(150, min(400, len(text) // 15))
        parts = []
        rest = text
        while rest:
            rest = rest.lstrip()
            if len(rest) <= chunk_size:
                if rest:
                    parts.append(rest)
                break
            pos = rest.rfind(" ", 0, chunk_size + 1)
            if pos <= 0:
                pos = rest.find(" ", chunk_size)
            if pos <= 0:
                parts.append(rest)
                break
            parts.append(rest[:pos].strip())
            rest = rest[pos:]
        if not parts:
            parts = [text]
    if len(parts) > max_parts:
        step = (len(parts) + max_parts - 1) // max_parts
        parts = [" ".join(parts[i:i + step]) for i in range(0, len(parts), step)]
    return parts[:max_parts]


def _get_speechkit_segments_with_timing(
    storage_key: str, audio_path: str | None, api_key: str, use_uri_key: str, tried_convert: bool,
) -> list[tuple[float, float, str]]:
    """
    Выполняет longRunningRecognize и возвращает сегменты с таймкодами (start, end, text)
    для выравнивания с диаризацией. Использует те же use_uri_key/headers, что и основной поток.
    """
    import storage as storage_mod
    ext = (Path(storage_key).suffix or "").lower()
    encoding = "OGG_OPUS" if tried_convert or use_uri_key != storage_key else ("MP3" if ext == ".mp3" else "OGG_OPUS")
    headers = {"Authorization": f"Api-Key {api_key}"}
    url = storage_mod.get_presigned_download_url(use_uri_key, expires_in=3600)
    body = {
        "config": {"specification": {"audioEncoding": encoding, "languageCode": "ru-RU"}},
        "audio": {"uri": url},
    }
    resp = requests.post(SPEECHKIT_RECOGNIZE_URL, headers=headers, json=body, timeout=30)
    resp.raise_for_status()
    op_id = resp.json().get("id")
    if not op_id:
        return []

    segments_out: list[tuple[float, float, str]] = []
    for _ in range(600):
        time.sleep(2)
        status = requests.get(SPEECHKIT_OPERATIONS_URL + op_id, headers=headers, timeout=120)
        status.raise_for_status()
        data = status.json()
        if not data.get("done"):
            continue
        chunks = data.get("response", {}).get("chunks", [])
        for ch in chunks:
            alts = ch.get("alternatives", [])
            if not alts:
                continue
            alt = alts[0]
            text = (alt.get("text") or "").strip()
            if not text:
                continue
            start_sec = _parse_speechkit_time(ch.get("startTime") or ch.get("start_time") or alt.get("startTime") or alt.get("start_time") or "")
            end_sec = _parse_speechkit_time(ch.get("endTime") or ch.get("end_time") or alt.get("endTime") or alt.get("end_time") or "")
            words = alt.get("words") or []
            # В API таймкоды только в words[].start_time/end_time (snake_case или camelCase; Duration как "1.5s" или {seconds,nanos})
            if words:
                st = words[0].get("start_time") or words[0].get("startTime")
                et = words[-1].get("end_time") or words[-1].get("endTime")
                if isinstance(st, dict):
                    st = (st.get("seconds") or 0) + ((st.get("nanos") or 0) / 1e9)
                if isinstance(et, dict):
                    et = (et.get("seconds") or 0) + ((et.get("nanos") or 0) / 1e9)
                if st is not None:
                    start_sec = _parse_speechkit_time(st)
                if et is not None:
                    end_sec = _parse_speechkit_time(et)
            if start_sec >= 0 and end_sec > start_sec:
                segments_out.append((start_sec, end_sec, text))
            else:
                segments_out.append((0.0, 0.0, text))
        return segments_out
    return []


def _align_segments_to_speakers(
    transcribe_segments: list[tuple[float, float, str]],
    diarization_segments: list[tuple[float, float, str]],
) -> list[tuple[str, float, float, str]]:
    """
    Сопоставляет сегменты транскрипции с диаризацией по перекрытию по времени.
    Возвращает список (speaker, start, end, text).
    """
    result = []
    for t_start, t_end, text in transcribe_segments:
        text = (text or "").strip()
        if not text:
            continue
        best_speaker = "SPEAKER_00"
        best_overlap = 0.0
        seg_mid = (t_start + t_end) / 2
        for d_start, d_end, speaker in diarization_segments:
            overlap_start = max(t_start, d_start)
            overlap_end = min(t_end, d_end)
            if overlap_end > overlap_start:
                overlap = overlap_end - overlap_start
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_speaker = speaker
            elif d_start <= seg_mid <= d_end:
                best_speaker = speaker
                break
        result.append((best_speaker, t_start, t_end, text))
    return result


def _merge_consecutive_same_speaker(
    segments: list[tuple[str, float, float, str]],
) -> list[tuple[str, float, float, str]]:
    """Объединяет подряд идущие сегменты одного спикера."""
    if not segments:
        return []
    merged = [list(segments[0])]
    for speaker, start, end, text in segments[1:]:
        if speaker == merged[-1][0]:
            merged[-1][2] = end
            merged[-1][3] = (merged[-1][3] + " " + text).strip()
        else:
            merged.append([speaker, start, end, text])
    return [tuple(s) for s in merged]


def _force_alternate_speakers(
    segments: list[tuple[str, float, float, str]],
    num_speakers: int = 2,
) -> list[tuple[str, float, float, str]]:
    """Если все сегменты с одним спикером, но сегментов много — чередуем Спикер 1 / Спикер 2."""
    if len(segments) < 2:
        return segments
    speakers = {s[0] for s in segments}
    if len(speakers) >= 2:
        return segments
    names = [f"SPEAKER_{i:02d}" for i in range(num_speakers)]
    return [(names[i % num_speakers], start, end, text) for i, (_, start, end, text) in enumerate(segments)]


def _diarize_librosa(
    audio_path: str,
    num_speakers: int | None = None,
    min_speakers: int = 2,
    max_speakers: int = 6,
) -> list[tuple[float, float, str]]:
    """
    Диаризация через librosa + sklearn (без Resemblyzer, без webrtcvad).
    Проще в установке — только pip install librosa scikit-learn.
    """
    try:
        import librosa
        import numpy as np
        from sklearn.cluster import AgglomerativeClustering
    except ImportError as e:
        logger.warning("Нужны librosa и scikit-learn: pip install librosa scikit-learn. %s", e)
        return []

    path = Path(audio_path)
    if not path.exists():
        raise FileNotFoundError(f"Файл не найден: {audio_path}")

    logger.info("Диаризация (librosa)...")
    y, sr = librosa.load(path, sr=16000, mono=True)
    win_len = int(1.6 * sr)  # ~1.6 сек на сегмент
    hop_len = int(0.4 * sr)
    n_segments = max(2, (len(y) - win_len) // hop_len + 1)
    if n_segments < 2:
        return []

    mfccs_list = []
    times = []
    for i in range(n_segments):
        start = i * hop_len
        end = min(start + win_len, len(y))
        seg = y[start:end]
        if len(seg) < sr // 2:
            continue
        mfcc = librosa.feature.mfcc(y=seg, sr=sr, n_mfcc=13)
        mfccs_list.append(np.mean(mfcc, axis=1))
        times.append((start / sr, end / sr))
    if len(mfccs_list) < 2:
        return []

    X = np.array(mfccs_list)
    n_clusters = num_speakers or min(max(min_speakers, 2), min(max_speakers, len(X) - 1))
    clustering = AgglomerativeClustering(n_clusters=n_clusters, metric="euclidean", linkage="average")
    labels = clustering.fit_predict(X)

    return [(t[0], t[1], f"SPEAKER_{l:02d}") for t, l in zip(times, labels)]


def _diarize_resemblyzer(
    audio_path: str,
    num_speakers: int | None = None,
    min_speakers: int = 2,
    max_speakers: int = 6,
) -> list[tuple[float, float, str]]:
    """
    Диаризация через Resemblyzer (точнее, но требует webrtcvad/C++).
    """
    try:
        from resemblyzer import preprocess_wav, VoiceEncoder
    except ImportError:
        return []

    try:
        from sklearn.cluster import AgglomerativeClustering
    except ImportError:
        return []

    path = Path(audio_path)
    if not path.exists():
        raise FileNotFoundError(f"Файл не найден: {audio_path}")

    logger.info("Загрузка Resemblyzer...")
    encoder = VoiceEncoder("cpu", verbose=False)
    wav = preprocess_wav(path)
    sampling_rate = 16000

    _, partial_embeds, wav_slices = encoder.embed_utterance(wav, return_partials=True, rate=8, min_coverage=0.5)
    if len(partial_embeds) < 2:
        return []

    n_clusters = num_speakers
    if n_clusters is None:
        n_clusters = min(max(min_speakers, 2), min(max_speakers, len(partial_embeds)))

    clustering = AgglomerativeClustering(n_clusters=n_clusters, metric="cosine", linkage="average")
    labels = clustering.fit_predict(partial_embeds)

    segs = []
    for sl, lbl in zip(wav_slices, labels):
        start = sl.start / sampling_rate
        end = sl.stop / sampling_rate
        segs.append((start, end, f"SPEAKER_{lbl:02d}"))
    segs.sort(key=lambda x: x[0])
    return segs


def transcribe_with_diarization(
    audio_path: str,
    language: str = "ru",
    num_speakers: int | None = None,
    min_speakers: int | None = 2,
    max_speakers: int | None = 10,
    storage_key: str | None = None,
) -> list[tuple[str, float, float, str]]:
    """
    Транскрибирует аудио с разметкой по спикерам. Возвращает список (speaker, start, end, text).

    Реальная разбивка по репликам (кто что сказал) возможна только при наличии фраз с таймкодами:
    - либо SpeechKit вернёт несколько сегментов с таймкодами;
    - либо установлен faster-whisper или openai-whisper (фразы по времени → привязка к диаризации);
    - либо используйте AssemblyAI с speaker_labels=True (готовые спикеры из облака).

    Диаризация: pyannote (HUGGINGFACE_TOKEN) → Resemblyzer → librosa.
    """
    import config

    path = Path(audio_path)
    if not path.exists():
        raise FileNotFoundError(f"Файл не найден: {audio_path}")

    hf_token = getattr(config, "HUGGINGFACE_TOKEN", None) or ""
    diar_segments: list[tuple[float, float, str]] = []

    # 1. Диаризация: pyannote (если есть HF) или Resemblyzer
    if hf_token:
        try:
            from pyannote.audio import Pipeline
            from faster_whisper import WhisperModel
        except ImportError:
            pass
        else:
            try:
                logger.info("Загрузка pyannote pipeline...")
                try:
                    pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.0", token=hf_token)
                except TypeError:
                    pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.0", use_auth_token=hf_token)
                diarization = pipeline(
                    str(path),
                    num_speakers=num_speakers,
                    min_speakers=min_speakers or 2,
                    max_speakers=max_speakers or 10,
                )
                for turn, _, speaker in diarization.itertracks(yield_label=True):
                    diar_segments.append((turn.start, turn.end, speaker))
            except Exception as e:
                logger.warning("Pyannote не сработал: %s. Пробуем Resemblyzer.", e)
                diar_segments = []

    if not diar_segments:
        diar_segments = _diarize_resemblyzer(
            str(path),
            num_speakers=num_speakers,
            min_speakers=min_speakers or 2,
            max_speakers=max_speakers or 10,
        )
    if not diar_segments:
        logger.info("Диаризация через librosa (без Resemblyzer)...")
        diar_segments = _diarize_librosa(
            str(path),
            num_speakers=num_speakers,
            min_speakers=min_speakers or 2,
            max_speakers=max_speakers or 10,
        )

    if not diar_segments:
        logger.warning("Диаризация не нашла сегменты спикеров")
        return []

    # 2. Транскрипция с таймкодами — только так можно реально привязать фразы к спикерам
    # SpeechKit часто возвращает один chunk без таймкодов → не используем для диаризации, идём в Whisper
    transcribe_segments: list[tuple[float, float, str]] = []
    if storage_key:
        api_key = getattr(config, "YANDEX_API_KEY", None) or ""
        if api_key:
            try:
                sk_segments = _get_speechkit_segments_with_timing(
                    storage_key, str(path), api_key, use_uri_key=storage_key, tried_convert=False
                )
                segments_with_times = [s for s in (sk_segments or []) if s[0] < s[1]]
                # Один сегмент на весь файл → всё к одному спикеру; нужны несколько сегментов для разбивки по голосам
                if len(segments_with_times) >= 2:
                    aligned = _align_segments_to_speakers(segments_with_times, diar_segments)
                    merged = _merge_consecutive_same_speaker(aligned)
                    return merged
                # Один chunk или без таймкодов — идём в Whisper (ниже), там фразы по времени
            except Exception as e:
                logger.warning("SpeechKit: %s", e)

    # Реальная разбивка по репликам: нужны фразы с таймкодами (start, end, text). Их даёт только Whisper или SpeechKit с разбивкой по фразам.
    try:
        from faster_whisper import WhisperModel
        logger.info("Загрузка faster-whisper...")
        model = WhisperModel("base", device="cpu", compute_type="int8")
        segments_gen, _ = model.transcribe(str(path), language=language, word_timestamps=False, vad_filter=True)
        transcribe_segments = [(s.start, s.end, s.text or "") for s in segments_gen]
    except ImportError:
        if _check_whisper():
            model = _get_model()
            result = model.transcribe(str(path), language=language, fp16=False, task="transcribe")
            for seg in result.get("segments", []):
                transcribe_segments.append((seg["start"], seg["end"], seg.get("text", "") or ""))
        else:
            logger.warning(
                "Whisper не установлен — нельзя получить фразы с таймкодами для привязки к спикерам. "
                "Установите: pip install faster-whisper (рекомендуется) или openai-whisper. "
                "Либо используйте AssemblyAI (speaker_labels=True) для готовой разметки по спикерам."
            )

    if not transcribe_segments:
        logger.warning("Транскрипция пуста (нет фраз с таймкодами)")
        return []

    # 3. Выравнивание и объединение
    aligned = _align_segments_to_speakers(transcribe_segments, diar_segments)
    merged = _merge_consecutive_same_speaker(aligned)
    return merged


def format_diarized_transcript(segments: list[tuple[str, float, float, str]], include_timestamps: bool = False) -> str:
    """Форматирует диаризованную транскрипцию в диалог: Спикер 1: ..., Спикер 2: ..."""
    lines = []
    for speaker, start, end, text in segments:
        if not text:
            continue
        # Единый формат диалога: Спикер 1, Спикер 2 (или Спикер A при буквенных id)
        raw = (speaker or "").strip()
        if raw.upper().startswith("SPEAKER_"):
            num = raw.upper().replace("SPEAKER_", "").strip()
            label = f"Спикер {int(num) + 1}" if num.isdigit() else f"Спикер {raw}"
        elif raw and len(raw) == 1 and raw.upper().isalpha():
            label = f"Спикер {raw.upper()}"
        else:
            label = f"Спикер {raw}" if raw else f"Спикер {len(lines) + 1}"
        if include_timestamps:
            m_s, s_s = divmod(int(start), 60)
            m_e, s_e = divmod(int(end), 60)
            ts = f"[{m_s}:{s_s:02d}–{m_e}:{s_e:02d}] "
        else:
            ts = ""
        lines.append(f"{ts}{label}: {text}")
    return "\n".join(lines)


def transcribe_audio(audio_path: str, language: str = "ru", storage_key: str | None = None) -> str:
    """
    Транскрибирует аудио в текст.
    audio_path — путь к файлу (для Whisper).
    storage_key — ключ в S3 (для SpeechKit, если файл уже там).
    """
    import config

    # 1. SpeechKit, если есть API-ключ и storage_key
    if storage_key:
        api_key = getattr(config, "YANDEX_API_KEY", "") or ""
        if api_key:
            try:
                return transcribe_via_speechkit(storage_key, audio_path=audio_path)
            except Exception as e:
                logger.warning("SpeechKit: %s", e)

    # 2. Whisper
    if not _check_whisper():
        return ""

    path = Path(audio_path)
    if not path.exists():
        raise FileNotFoundError(f"Файл не найден: {audio_path}")

    try:
        model = _get_model()
        result = model.transcribe(str(path), language=language, fp16=False, task="transcribe")
        return (result.get("text") or "").strip()
    except Exception as e:
        logger.exception("Whisper: %s", e)
        raise
