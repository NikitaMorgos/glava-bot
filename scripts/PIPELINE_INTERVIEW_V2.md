# Пайплайн обработки интервью v2

Новый техпроцесс для переработки длинных интервью (40–60 мин) и сравнения с прежней транскрипцией.

## Этапы

1. **Резка на чанки** — 3–5 мин без перекрытия (`chunk_id`, `start_time`, `end_time`)
2. **Транскрипция** — Whisper large-v2 (или medium), `raw_transcript` + `clean_transcript`
3. **Диаризация** — pyannote / librosa, метки `interviewer` / `hero`, флаг `confidence`
4. **Сегментация по темам** — детство, война, работа, семья, переезды и т.п.
5. **Извлечение фактов и эпизодов** — годы, места, имена, должности, истории
6. **Черновая глава** — только из facts/stories, без придумывания
7. **Сравнение со старой версией** — расхождения, улучшения, примеры

## Запуск

```bash
# Взять самый длинный интервью из БД (30+ мин)
python scripts/pipeline_interview_v2.py --longest

# Конкретный голосовой по id
python scripts/pipeline_interview_v2.py --voice-id 42

# Локальный аудиофайл
python scripts/pipeline_interview_v2.py --audio path/to/interview.ogg

# С передачей старой транскрипции/истории для сравнения
python scripts/pipeline_interview_v2.py --audio X.ogg --old-transcript old.txt --old-story old_story.txt

# Длина чанка (по умолчанию 4 мин)
python scripts/pipeline_interview_v2.py --longest --chunk-sec 300
```

## Зависимости

- **ffmpeg** — для резки и конвертации
- **faster-whisper** — транскрипция (large-v2)
- **pyannote-audio** (опционально) — HUGGINGFACE_TOKEN в .env
- **librosa, scikit-learn** — диаризация без pyannote

## Результат

Папка `pipelines/interview_YYYYMMDD_HHMMSS/`:

| Файл | Описание |
|------|----------|
| `structured.json` | chunks, blocks, facts, stories, dialogue |
| `draft_chapter.txt` | черновая глава 2–4 страницы |
| `comparison_report.md` | сравнение со старой версией |

## Формат structured.json

```json
{
  "chunks": [
    {
      "chunk_id": "chunk_000",
      "start_time": 0,
      "end_time": 240,
      "raw_transcript": "...",
      "clean_transcript": "...",
      "utterances": [
        {"speaker": "interviewer", "start_time": "0:00", "end_time": "0:15", "text": "...", "confidence": "high"},
        {"speaker": "hero", "start_time": "0:16", "end_time": "2:30", "text": "...", "confidence": "high"}
      ]
    }
  ],
  "blocks": [
    {
      "block_id": "block_00",
      "title": "детство",
      "start_time": 0,
      "end_time": 480,
      "chunks": ["chunk_000", "chunk_001"],
      "dialogue": [...],
      "facts": [{"type": "год", "value": "1945"}, {"type": "место", "value": "Москва"}],
      "stories": [{"text": "...", "start": "1:20", "end": "3:00"}]
    }
  ]
}
```
