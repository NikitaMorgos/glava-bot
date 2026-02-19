#!/usr/bin/env python3
"""
Пайплайн обработки длинного интервью (v2).

Новый техпроцесс:
1. Резка на чанки 3–5 мин
2. Транскрипция Whisper large-v2 (raw + clean)
3. Диаризация (interviewer / hero)
4. Сегментация по темам
5. Извлечение фактов и эпизодов
6. Сборка черновой главы
7. Сравнение со старой транскрипцией

Запуск:
  python pipeline_interview_v2.py --audio path/to/interview.ogg
  python pipeline_interview_v2.py --voice-id 123          # взять из БД по id
  python pipeline_interview_v2.py --longest               # самый длинный из БД
  python pipeline_interview_v2.py --audio X.ogg --old-transcript old.txt --old-story old_story.txt
  python pipeline_interview_v2.py --from-transcript exports/client_605154_ddmika/transcript.txt --duration 2393

Режим --from-transcript: берёт готовый текст, делает структуру/факты/диаризацию (без аудио).

Результат в pipelines/interview_{timestamp}/
  structured.json    — блоки, факты, эпизоды
  draft_chapter.txt  — черновая глава
  comparison_report.md — сравнение со старой версией
"""

import argparse
import json
import logging
import re
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root))

# Кэш для ML
import os
_cache = _project_root / ".cache"
_cache.mkdir(exist_ok=True)
for v in ("HF_HOME", "XDG_CACHE_HOME", "TORCH_HOME", "TRANSFORMERS_CACHE"):
    os.environ.setdefault(v, str(_cache))

# Константы
CHUNK_DURATION_SEC = 4 * 60  # 4 минуты
WHISPER_MODEL = "large-v2"   # лучшее качество
TOPIC_KEYWORDS = {
    "семья и происхождение": ["родители", "мама", "папа", "бабушка", "дедушка", "род", "родился", "фамилия"],
    "детство": ["детство", "детстве", "школа", "учился", "играли", "друзья", "игры"],
    "война и тяжёлые годы": ["война", "фронт", "блокад", "эвакуац", "немц", "оккупац", "голод", "погиб"],
    "учёба и работа": ["работа", "работал", "завод", "фабрика", "институт", "университет", "професс", "должность"],
    "семья и любовь": ["жена", "муж", "женился", "вышла замуж", "свадьба", "дети", "ребёнок", "внуки"],
    "переезды и география": ["переехал", "переехали", "город", "деревня", "москва", "ленинград", "ссср"],
}


@dataclass
class Chunk:
    chunk_id: str
    start_time: float
    end_time: float
    raw_transcript: str = ""
    clean_transcript: str = ""
    utterances: list = field(default_factory=list)  # [{speaker, start_time, end_time, text, confidence}]


@dataclass
class Block:
    block_id: str
    title: str
    start_time: float
    end_time: float
    chunks: list
    dialogue: list
    facts: list = field(default_factory=list)
    stories: list = field(default_factory=list)


def get_audio_duration_ffprobe(path: str) -> float:
    """Длительность в секундах через ffprobe."""
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if out.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {out.stderr}")
    return float(out.stdout.strip())


def split_audio_chunks(audio_path: str, chunk_sec: int = CHUNK_DURATION_SEC) -> list[dict]:
    """Разрезает аудио на чанки без перекрытия. Возвращает [{chunk_id, start_time, end_time, path}]."""
    duration = get_audio_duration_ffprobe(audio_path)
    chunks = []
    work_dir = Path(audio_path).parent / "_chunks"
    work_dir.mkdir(exist_ok=True)

    start = 0.0
    i = 0
    while start < duration:
        end = min(start + chunk_sec, duration)
        chunk_id = f"chunk_{i:03d}"
        out_path = work_dir / f"{chunk_id}{Path(audio_path).suffix}"
        subprocess.run(
            ["ffmpeg", "-y", "-i", audio_path, "-ss", str(start), "-to", str(end), "-c", "copy", str(out_path)],
            capture_output=True,
            check=True,
            timeout=60,
        )
        chunks.append({
            "chunk_id": chunk_id,
            "start_time": start,
            "end_time": end,
            "path": str(out_path),
        })
        start = end
        i += 1

    logger.info("Нарезано %d чанков (%.1f мин каждый)", len(chunks), chunk_sec / 60)
    return chunks


def transcribe_chunk(path: str, model_size: str = "large-v2", language: str = "ru", use_speechkit_fallback: bool = False) -> tuple[str, str]:
    """Транскрибирует чанк. Возвращает (raw_transcript, clean_transcript). Fallback: SpeechKit."""
    raw = ""
    # 1. faster-whisper / whisper
    try:
        from faster_whisper import WhisperModel
        model_name = "large-v2" if model_size == "large-v2" else ("large-v3" if model_size == "large-v3" else "medium")
        try:
            model = WhisperModel(model_name, device="cpu", compute_type="int8")
        except Exception:
            model = WhisperModel("medium", device="cpu", compute_type="int8")
        segments_gen, _ = model.transcribe(path, language=language, word_timestamps=False, vad_filter=True)
        parts = [s.text.strip() for s in segments_gen if s.text and s.text.strip()]
        raw = " ".join(parts)
    except ImportError:
        try:
            import whisper
            model = whisper.load_model("base" if model_size not in ("large-v2", "large-v3") else "medium")
            result = model.transcribe(path, language=language, fp16=False, task="transcribe")
            raw = (result.get("text") or "").strip()
        except Exception as e:
            logger.debug("Whisper: %s", e)
    except Exception as e:
        logger.debug("faster-whisper: %s", e)

    # 2. SpeechKit fallback (загружает чанк во временный объект S3)
    if not raw and use_speechkit_fallback:
        try:
            from dotenv import load_dotenv
            load_dotenv(_project_root / ".env")
            import storage
            import uuid
            ext = Path(path).suffix or ".ogg"
            temp_key = f"temp/pipeline_{uuid.uuid4().hex}{ext}"
            storage.upload_file_to_key(path, temp_key)
            try:
                from transcribe import transcribe_via_speechkit
                raw = transcribe_via_speechkit(temp_key, audio_path=path)
            finally:
                try:
                    storage.delete_object(temp_key)
                except Exception:
                    pass
        except Exception as e:
            logger.debug("SpeechKit fallback: %s", e)

    clean = _clean_transcript(raw)
    return raw, clean


def _clean_transcript(text: str) -> str:
    """Лёгкая правка орфографии/пунктуации без перефразирования."""
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\.\s*\.", ".", text)
    text = re.sub(r",\s*,", ",", text)
    text = text.strip()
    return text


def diarize_chunk(chunk_path: str, chunk_start: float, language: str = "ru") -> list[dict]:
    """Диаризация чанка. Возвращает [{speaker, start_time, end_time, text, confidence}]. """
    # Сначала транскрибируем с таймкодами
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel("medium", device="cpu", compute_type="int8")
        segments_gen, _ = model.transcribe(chunk_path, language=language, word_timestamps=False, vad_filter=True)
        transcribe_segments = [(s.start, s.end, (s.text or "").strip()) for s in segments_gen if (s.text or "").strip()]
    except Exception as e:
        logger.warning("Транскрипция для диаризации: %s", e)
        return []

    if not transcribe_segments:
        return []

    # Без диаризации — альтернация: короткие реплики = interviewer, длинные = hero
    def _fallback_utterances():
        result = []
        for idx, (t_start, t_end, text) in enumerate(transcribe_segments):
            sp = "interviewer" if len(text) < 80 and idx % 2 == 0 else "hero"
            result.append({
                "speaker": sp,
                "start_time": _ts(chunk_start + t_start),
                "end_time": _ts(chunk_start + t_end),
                "text": text,
                "confidence": "low",
            })
        return result

    # Диаризация: pyannote или librosa
    diar_segments: list[tuple[float, float, str]] = []
    try:
        from dotenv import load_dotenv
        load_dotenv(_project_root / ".env")
        import config
        hf = getattr(config, "HUGGINGFACE_TOKEN", None) or ""
        if hf:
            from pyannote.audio import Pipeline
            pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.0", use_auth_token=hf)
            diar = pipeline(chunk_path, min_speakers=2, max_speakers=4)
            for turn, _, spk in diar.itertracks(yield_label=True):
                diar_segments.append((turn.start, turn.end, spk))
    except Exception as e:
        logger.debug("Pyannote: %s", e)

    if not diar_segments:
        try:
            import librosa
            import numpy as np
            from sklearn.cluster import AgglomerativeClustering
            y, sr = librosa.load(chunk_path, sr=16000, mono=True)
            win = int(1.6 * sr)
            hop = int(0.4 * sr)
            n = max(2, (len(y) - win) // hop + 1)
            mfccs, times = [], []
            for i in range(n):
                s, e = i * hop, min(i * hop + win, len(y))
                seg = y[s:e]
                if len(seg) < sr // 2:
                    continue
                mfcc = librosa.feature.mfcc(y=seg, sr=sr, n_mfcc=13)
                mfccs.append(np.mean(mfcc, axis=1))
                times.append((s / sr, e / sr))
            if len(mfccs) >= 2:
                X = np.array(mfccs)
                cl = AgglomerativeClustering(n_clusters=min(2, len(X)), metric="euclidean", linkage="average")
                labels = cl.fit_predict(X)
                diar_segments = [(t[0], t[1], f"SPEAKER_{l:02d}") for t, l in zip(times, labels)]
        except Exception as e:
            logger.debug("Librosa diar: %s", e)

    if not diar_segments:
        return _fallback_utterances()

    # Сопоставление транскрипции с диаризацией
    utterances = []
    for t_start, t_end, text in transcribe_segments:
        if not text:
            continue
        best_spk = "SPEAKER_00"
        best_overlap = 0.0
        mid = (t_start + t_end) / 2
        for d_start, d_end, spk in diar_segments:
            o_start, o_end = max(t_start, d_start), min(t_end, d_end)
            if o_end > o_start:
                ov = o_end - o_start
                if ov > best_overlap:
                    best_overlap = ov
                    best_spk = spk
            elif d_start <= mid <= d_end:
                best_spk = spk
                break
        # Маппинг: SPEAKER_01 -> hero (отвечает), SPEAKER_00 -> interviewer
        speaker = "hero" if "01" in best_spk or best_spk.endswith("_1") else "interviewer"
        confidence = "high" if best_overlap > 0.5 else "low"
        utterances.append({
            "speaker": speaker,
            "start_time": _ts(chunk_start + t_start),
            "end_time": _ts(chunk_start + t_end),
            "text": text,
            "confidence": confidence,
        })
    return utterances


def _ts(sec: float) -> str:
    m, s = divmod(int(sec), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _assign_topic(text: str) -> str:
    """Присваивает тему по ключевым словам."""
    t = text.lower()
    best = "прочее"
    best_score = 0
    for topic, kws in TOPIC_KEYWORDS.items():
        score = sum(1 for kw in kws if kw in t)
        if score > best_score:
            best_score = score
            best = topic
    return best


def segment_by_topics(chunks: list[Chunk]) -> list[Block]:
    """Сегментация по темам: каждый чанк → тема, объединяем подряд идущие."""
    if not chunks:
        return []
    topics = [_assign_topic(c.clean_transcript) for c in chunks]
    blocks = []
    i = 0
    block_idx = 0
    while i < len(chunks):
        start_i = i
        topic = topics[i]
        block_chunk_ids = [chunks[i].chunk_id]
        block_dialogue = []
        for u in chunks[i].utterances:
            block_dialogue.append({"speaker": u["speaker"], "start_time": u["start_time"], "end_time": u["end_time"], "text": u["text"]})
        j = i + 1
        while j < len(chunks) and topics[j] == topic:
            block_chunk_ids.append(chunks[j].chunk_id)
            for u in chunks[j].utterances:
                block_dialogue.append({"speaker": u["speaker"], "start_time": u["start_time"], "end_time": u["end_time"], "text": u["text"]})
            j += 1
        block = Block(
            block_id=f"block_{block_idx:02d}",
            title=topic,
            start_time=chunks[start_i].start_time,
            end_time=chunks[j - 1].end_time,
            chunks=block_chunk_ids,
            dialogue=block_dialogue,
        )
        blocks.append(block)
        block_idx += 1
        i = j
    return blocks


# Паттерны начала новой реплики (вопрос/комментарий)
_TURN_START = r"(?:\s+|^)(Как |Где |Когда |Сколько |Что |Кто |А |Ну а |А че |Почему |Был ли |Какая |Какие |Кем |Зачем |Давай |Ну |Стоп |Ладно |То есть )"


def _split_transcript_into_turns(text: str) -> list[tuple[int, int, str, str]]:
    """
    Эвристика: разбивает текст на реплики (start_char, end_char, speaker, text).
    Короткие фразы/вопросы -> interviewer, длинные рассказы -> hero.
    """
    # Сплит по пунктуации + по началу типичных вопросов/реплик
    parts = re.split(r'(?<=[.?!])\s+|\s+(?=Как |Где |Когда |Сколько |Что |Кто |А вот |А че |Почему |Был ли |Какая |Какие |Кем |Зачем |Ну а |Давай |Ладно |То есть |Стоп )', text)
    turns = []
    pos = 0
    for p in parts:
        p = p.strip()
        if not p or len(p) < 5:
            continue
        start_char = text.find(p, pos)
        if start_char < 0:
            start_char = pos
        end_char = start_char + len(p)
        pos = end_char
        is_question = "?" in p or any(p.startswith(w) for w in ("Как ", "Где ", "Когда ", "Сколько ", "Что ", "Кто ", "А ", "Ну а ", "А че ", "Почему ", "Был ли "))
        if (len(p) < 100 and is_question) or len(p) < 50:
            speaker = "interviewer"
        else:
            speaker = "hero"
        turns.append((start_char, end_char, speaker, p))
    return turns


def build_chunks_from_transcript(transcript_path: str, duration_sec: float, chunk_sec: int = CHUNK_DURATION_SEC) -> list[Chunk]:
    """
    Строит chunks из готового транскрипта (без аудио).
    """
    text = Path(transcript_path).read_text(encoding="utf-8")
    text = re.sub(r"---[^-\n]+---\s*", "", text)
    text = " ".join(text.split())
    turns = _split_transcript_into_turns(text)
    n_chunks = max(1, int(duration_sec / chunk_sec))
    chars_per_chunk = len(text) / n_chunks if text else 1
    chunks = []
    for i in range(n_chunks):
        start_time = i * chunk_sec
        end_time = min((i + 1) * chunk_sec, duration_sec)
        chunk_start_char = int(i * chars_per_chunk)
        chunk_end_char = int((i + 1) * chars_per_chunk)
        chunk_text = text[chunk_start_char:chunk_end_char]
        utterances = []
        for tc_start, tc_end, speaker, txt in turns:
            if tc_start >= chunk_end_char or tc_end <= chunk_start_char:
                continue
            rel_start = start_time + (max(0, tc_start - chunk_start_char) / len(chunk_text)) * (end_time - start_time) if chunk_text else start_time
            rel_end = start_time + (min(len(chunk_text), tc_end - chunk_start_char) / len(chunk_text)) * (end_time - start_time) if chunk_text else end_time
            utterances.append({
                "speaker": speaker,
                "start_time": _ts(rel_start),
                "end_time": _ts(rel_end),
                "text": txt,
                "confidence": "heuristic",
            })
        if not utterances and chunk_text:
            utterances = [{"speaker": "hero", "start_time": _ts(start_time), "end_time": _ts(end_time), "text": chunk_text[:500], "confidence": "heuristic"}]
        chunks.append(Chunk(
            chunk_id=f"chunk_{i:03d}",
            start_time=start_time,
            end_time=end_time,
            raw_transcript=chunk_text,
            clean_transcript=_clean_transcript(chunk_text),
            utterances=utterances,
        ))
    return chunks


_EXCLUDE_PLACES = {
    "нету", "у", "в", "идти", "пройтись", "Перейти", "много", "да", "и", "на", "по", "из",
    "к", "с", "о", "за", "от", "до", "для", "при", "без", "под", "над", "через",
    "что", "как", "где", "туда", "сюда", "тут", "там", "вот", "есть", "было", "нет",
}

_EXCLUDE_NAMES = {
    "Москва", "Ленинград", "Россия", "Советский", "Крестьянская", "Крестьянской",
    "Разнорабочие", "Лаборанткой", "Кончила", "Приехал", "Понятно", "Ранетки",
    "Ворошилов", "Бабушка", "Мама", "Екатеринбург", "Угу", "Давай", "Понял",
    "Сначала", "Раньше", "Она", "Зачем", "Нет", "Что", "Тоже", "Было", "Туда",
    "Это", "Найти", "Где", "Бросим", "Ручей", "Течет", "Периодически", "Зарабатывала",
    "Компактная", "Нарциссы", "Получается", "Есть", "Все", "Мало", "Сказать",
    "Собирание", "Стоп", "Такая", "Елочка", "Круто", "Животных", "Ладно", "Или",
    "Как", "Судебный", "Скачать", "Чуть", "Из", "Слишком", "Наверно", "Фотографию",
    "Открыток", "Шкатулочки", "Лед", "Эмолюция", "Оно", "Когда", "Шура", "Нигде",
    "Дорогу", "Машину", "Поэтому", "Пьяного", "Огородом", "Бабушке", "Клиентскую",
    "Колхоз", "Канлон", "Кружево", "Крестьянской",
}


def extract_facts_and_stories(block: Block) -> tuple[list, list]:
    """Извлекает факты и эпизоды из dialogue блока."""
    facts = []
    seen = set()
    text = " ".join(d["text"] for d in block.dialogue)

    def _add(t: str, v: str):
        key = f"{t}:{v}"
        if key not in seen and v and len(v) < 100:
            seen.add(key)
            facts.append({"type": t, "value": v})

    # Годы
    for m in re.finditer(r"\b(19\d{2}|20\d{2})\b", text):
        _add("год", m.group(1))
    for m in re.finditer(r"(?:примерно|около|в )\s*(\d{4})", text, re.I):
        _add("год (примерно)", m.group(1))

    # Места (города, области, деревни)
    for m in re.finditer(r"\b(Москв[аеу]?|Ленинград[ае]?|Петербург[ае]?|Екатеринбург[ае]?|Киев[ае]?|Осташков[ае]?|Пасынково|Калининск[аяую]?|Рамешковский|Свердловск[ае]?)\b", text):
        _add("место", m.group(1))
    for m in re.finditer(r"деревн[ияеу] ([А-Яа-яё\-]{4,})", text):
        val = m.group(1).strip()
        if val not in _EXCLUDE_PLACES:
            _add("место (деревня)", val)

    # Имена: только похожие на Фамилия Имя (исключаем мусор)
    for m in re.finditer(r"\b([А-ЯЁ][а-яё]{2,})\s+([А-ЯЁ][а-яё]{2,}(?:ович|евич|овна|евна|ова|ева)?)\b", text):
        a, b = m.group(1), m.group(2)
        if a not in _EXCLUDE_NAMES and b not in _EXCLUDE_NAMES and not re.match(r"^(Как|Где|Что|Кто|Когда|Сколько|Почему|Куда|Откуда)", a):
            _add("имя", f"{a} {b}")

    # Должности
    for m in re.finditer(r"(?:работал[а]?|был[а]?)\s+([а-яёА-ЯЁ\s]{4,60}?)(?:\.|,|$)", text):
        job = m.group(1).strip()
        if 5 < len(job) < 70 and "или" not in job.lower():
            _add("должность", job)

    stories = []
    for d in block.dialogue:
        if d["speaker"] == "hero" and len(d["text"]) > 120:
            stories.append({"text": d["text"][:500], "start": d["start_time"], "end": d["end_time"]})
    if not facts:
        facts.append({"type": "нет данных", "value": "факты не извлечены автоматически"})
    return facts, stories


def build_dialogue_file(transcript_path: str, output_path: Path) -> None:
    """
    Собирает один диалоговый файл: каждая реплика со спикером.
    Валентина — основной рассказчик, Катя и Дима — вопросы и комментарии (чередуем).
    """
    text = Path(transcript_path).read_text(encoding="utf-8")
    text = re.sub(r"---[^-\n]+---\s*", "", text)
    text = " ".join(text.split())
    turns = _split_transcript_into_turns(text)
    lines = []
    katya_dima = 0  # 0 = Катя, 1 = Дима
    for _, _, speaker, txt in turns:
        txt = txt.strip()
        if not txt or len(txt) < 3:
            continue
        if speaker == "hero":
            spk = "Валентина"
        else:
            spk = "Катя" if katya_dima == 0 else "Дима"
            katya_dima = 1 - katya_dima
        lines.append(f"{spk}: {txt}")
    output_path.write_text("\n\n".join(lines), encoding="utf-8")


def build_draft_chapter(blocks: list[Block]) -> str:
    """Собирает черновую главу только из facts и stories (без мусорных фактов)."""
    lines = []
    skip_types = {"нет данных"}
    seen_stories = set()  # дедупликация эпизодов
    for b in blocks:
        valid_facts = [f for f in b.facts if f.get("type") not in skip_types]
        valid_stories = []
        for s in b.stories:
            if not s.get("text") or len(s["text"]) <= 50:
                continue
            txt_key = s["text"][:200]  # ключ для дедупликации
            if txt_key in seen_stories:
                continue
            seen_stories.add(txt_key)
            valid_stories.append(s)
        if not valid_facts and not valid_stories:
            continue
        lines.append(f"\n=== {b.title} ===\n")
        for f in valid_facts:
            lines.append(f"- {f['type']}: {f['value']}")
        for s in valid_stories:
            lines.append(f"\n{s['text'][:400]}{'...' if len(s['text']) > 400 else ''}")
    return "\n".join(lines).strip() or "[данных недостаточно — проверьте извлечение фактов]"


def run_comparison(
    old_transcript: str | None,
    old_story: str | None,
    new_blocks: list[Block],
    new_draft: str,
) -> str:
    """Краткий отчёт сравнения старой и новой версии."""
    lines = ["# Сравнительный отчёт: старая vs новая обработка\n"]
    if not old_transcript and not old_story:
        lines.append("Старая транскрипция/история не передана. Сравнение невозможно.")
        return "\n".join(lines)

    old_text = (old_transcript or "") + "\n" + (old_story or "")
    new_facts = []
    for b in new_blocks:
        new_facts.extend(b.facts)
    new_years = [f["value"] for f in new_facts if "год" in f.get("type", "")]
    old_years = re.findall(r"\b(19\d{2}|20\d{2})\b", old_text)
    years_diff = set(old_years) - set(new_years)
    if years_diff:
        lines.append("## Расхождения по годам")
        lines.append(f"- В старой версии есть годы, отсутствующие в новой: {years_diff}")
    lines.append("\n## Улучшения новой версии")
    lines.append("- Разделение интервьюера и героя по каждому сегменту")
    lines.append("- Структура по тематическим блокам")
    lines.append("- Извлечение фактов (годы, места, имена) структурированно")
    lines.append("\n## Примеры фрагментов (см. structured.json)")
    for i, b in enumerate(new_blocks[:3]):
        if b.dialogue:
            d = b.dialogue[0]
            lines.append(f"- [{b.title}] {d['speaker']}: {d['text'][:80]}...")
    return "\n".join(lines)


def fetch_longest_voice_from_db() -> tuple[str, str | None]:
    """Скачивает самый длинный голосовой из БД. Возвращает (local_path, old_transcript)."""
    from dotenv import load_dotenv
    load_dotenv(_project_root / ".env")
    import db
    import storage
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT v.id, v.storage_key, v.duration, v.transcript
                FROM voice_messages v
                WHERE v.duration >= 1800
                ORDER BY v.duration DESC NULLS LAST
                LIMIT 1
            """)
            row = cur.fetchone()
    if not row:
        raise FileNotFoundError("Нет голосовых 30+ минут в БД")
    vid, storage_key, duration, transcript = row
    out_dir = _project_root / "pipelines" / "interview_input"
    out_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(storage_key).suffix or ".ogg"
    local = out_dir / f"voice_{vid}{ext}"
    storage.download_file(storage_key, str(local))
    logger.info("Скачан voice_id=%s, %s сек, transcript=%s", vid, duration, "есть" if transcript else "нет")
    return str(local), transcript


def fetch_voice_by_id(voice_id: int) -> tuple[str, str | None]:
    """Скачивает голосовой по id. Возвращает (local_path, old_transcript)."""
    from dotenv import load_dotenv
    load_dotenv(_project_root / ".env")
    import db
    import storage
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT storage_key, transcript FROM voice_messages WHERE id = %s", (voice_id,))
            row = cur.fetchone()
    if not row:
        raise FileNotFoundError(f"voice_messages id={voice_id} не найден")
    storage_key, transcript = row
    out_dir = _project_root / "pipelines" / "interview_input"
    out_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(storage_key).suffix or ".ogg"
    local = out_dir / f"voice_{voice_id}{ext}"
    storage.download_file(storage_key, str(local))
    return str(local), transcript


def main():
    parser = argparse.ArgumentParser(description="Пайплайн обработки интервью v2")
    parser.add_argument("--audio", type=str, help="Путь к аудиофайлу")
    parser.add_argument("--voice-id", type=int, help="ID голосового в БД")
    parser.add_argument("--longest", action="store_true", help="Взять самый длинный из БД")
    parser.add_argument("--old-transcript", type=str, help="Путь к старой транскрипции")
    parser.add_argument("--old-story", type=str, help="Путь к старой истории/главе")
    parser.add_argument("--chunk-sec", type=int, default=CHUNK_DURATION_SEC, help="Длина чанка в секундах")
    parser.add_argument("--from-transcript", type=str, help="Готовый транскрипт — строит структуру без аудио")
    parser.add_argument("--duration", type=int, default=2400, help="Длительность в сек (для --from-transcript)")
    args = parser.parse_args()

    audio_path = None
    old_transcript = None
    old_story = None

    if args.from_transcript:
        transcript_path = Path(args.from_transcript)
        if not transcript_path.exists():
            transcript_path = _project_root / args.from_transcript
        if not transcript_path.exists():
            logger.error("Файл не найден: %s", args.from_transcript)
            sys.exit(1)
        chunks = build_chunks_from_transcript(str(transcript_path), args.duration, chunk_sec=args.chunk_sec)
        old_transcript = transcript_path.read_text(encoding="utf-8")
        out_dir = _project_root / "pipelines" / f"interview_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        out_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Режим --from-transcript, выход: %s", out_dir)
    elif args.longest:
        audio_path, old_transcript = fetch_longest_voice_from_db()
    elif args.voice_id:
        audio_path, old_transcript = fetch_voice_by_id(args.voice_id)
    elif args.audio:
        audio_path = args.audio
        if not Path(audio_path).exists():
            logger.error("Файл не найден: %s", audio_path)
            sys.exit(1)
    else:
        parser.print_help()
        logger.error("Укажи --audio, --voice-id, --longest или --from-transcript")
        sys.exit(1)

    if not args.from_transcript:
        if args.old_transcript and Path(args.old_transcript).exists():
            old_transcript = Path(args.old_transcript).read_text(encoding="utf-8")
        if args.old_story and Path(args.old_story).exists():
            old_story = Path(args.old_story).read_text(encoding="utf-8")
        if isinstance(old_transcript, str) and not old_transcript.strip():
            old_transcript = None

        out_dir = _project_root / "pipelines" / f"interview_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        out_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Выход: %s", out_dir)

        # 1. Резка
        chunk_specs = split_audio_chunks(audio_path, chunk_sec=args.chunk_sec)
        chunks = []

        # 2–3. Транскрипция + диаризация по чанкам
        use_sk = bool(args.longest or args.voice_id)
        for spec in chunk_specs:
            raw, clean = transcribe_chunk(spec["path"], model_size=WHISPER_MODEL, use_speechkit_fallback=use_sk)
            utterances = diarize_chunk(spec["path"], spec["start_time"])
            ch = Chunk(
                chunk_id=spec["chunk_id"],
                start_time=spec["start_time"],
                end_time=spec["end_time"],
                raw_transcript=raw,
                clean_transcript=clean,
                utterances=utterances if utterances else [{"speaker": "unknown", "start_time": _ts(spec["start_time"]), "end_time": _ts(spec["end_time"]), "text": clean[:200], "confidence": "low"}],
            )
            chunks.append(ch)
            logger.info("Чанк %s: %d реплик", ch.chunk_id, len(ch.utterances))

    # 4. Сегментация по темам
    blocks = segment_by_topics(chunks)
    logger.info("Блоков: %d", len(blocks))

    # 5. Извлечение фактов и эпизодов
    for b in blocks:
        b.facts, b.stories = extract_facts_and_stories(b)

    # 6. Черновая глава
    draft = build_draft_chapter(blocks)

    # 7. Сравнение
    report = run_comparison(old_transcript, old_story, blocks, draft)

    # Сохранение артефактов
    source = str(args.from_transcript) if args.from_transcript else str(audio_path or "")
    structured = {
        "source": source,
        "chunks": [asdict(c) for c in chunks],
        "blocks": [asdict(b) for b in blocks],
    }
    (out_dir / "structured.json").write_text(json.dumps(structured, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "draft_chapter.txt").write_text(draft, encoding="utf-8")
    (out_dir / "comparison_report.md").write_text(report, encoding="utf-8")

    # Диалог в один файл (Валентина, Катя, Дима) — только для --from-transcript
    if args.from_transcript:
        tp = Path(args.from_transcript)
        if not tp.is_absolute():
            tp = _project_root / tp
        if tp.exists():
            build_dialogue_file(str(tp), out_dir / "dialogue.txt")
            logger.info("Готово: structured.json, draft_chapter.txt, comparison_report.md, dialogue.txt")
        else:
            logger.info("Готово: structured.json, draft_chapter.txt, comparison_report.md")
    else:
        logger.info("Готово: structured.json, draft_chapter.txt, comparison_report.md")


if __name__ == "__main__":
    main()
