# Recall.ai — заметки и диагностика

## Решение о выборе Recall.ai

MyMeet отклонён по экономическим причинам: требует покупки большого объёма минут наперёд, не подходит для pay-as-you-go модели.

HappyScribe отклонён по техническим причинам: AI Notetaker не поддерживает программный join по URL — работает только через интеграцию с календарём. Не совместим с архитектурой GLAVA (мы отправляем ссылку на встречу через API).

Recall.ai выбран: поддерживает `POST /api/v1/bot` с `meeting_url`, AssemblyAI как ASR (русский язык), pay-as-you-go pricing.

## API регион

По умолчанию `us-east-1.recall.ai`. Если нужен EU — `eu-west-2.recall.ai`.
Задаётся через `RECALL_REGION` в `.env`.

## ASR провайдер

Recall.ai поддерживает несколько ASR:
- `assembly_ai` — наш выбор (русский, диаризация, хорошее качество). Нужен `ASSEMBLYAI_API_KEY`.
- `deepgram` — альтернатива, тоже поддерживает русский.
- `speechmatics` — тоже вариант для русского.

В `recall_client.py` используем `assembly_ai` с `language_code: ru`.

## Статусы бота Recall.ai

Жизненный цикл:
```
ready → joining_call → in_call_not_recording → in_call_recording → call_ended → done
```
Ошибка: `fatal`

Polling: каждые 15 секунд, таймаут 2 часа (для длинных интервью).

## Формат транскрипта

Recall.ai возвращает список сегментов:
```json
[
  {
    "speaker": "Спикер 1",
    "words": [{"text": "Привет", "start_timestamp": {...}, "end_timestamp": {...}}],
    "is_final": true
  }
]
```

Извлечение: конкатенируем `words[].text` в строку для каждого спикера.

## Совместимые платформы

- Google Meet ✅
- Zoom ✅
- Microsoft Teams ✅
- Webex ✅
- Yandex Telemost — нет официальной поддержки (Recall.ai не интегрирован с Telemost)

Для Telemost используем `upload_audio` через AssemblyAI напрямую.
