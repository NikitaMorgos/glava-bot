# Recall.ai — план задачи

## Цель

Подключить [Recall.ai](https://www.recall.ai/) как замену MyMeet для транскрипции онлайн-встреч.  
Бот присоединяется к звонку по URL, записывает и транскрибирует через AssemblyAI (поддерживает русский язык).  
Полностью совместимо с флоу `/online` в боте.

## Почему Recall.ai

| Критерий | MyMeet | Recall.ai |
|----------|--------|-----------|
| Бот приходит по URL | ✅ | ✅ |
| Русский язык | ✅ | ✅ (через AssemblyAI) |
| Доступен из РФ | ✅ | ✅ |
| Google Meet / Zoom / Teams | ✅ | ✅ |
| Диаризация по спикерам | Частично | ✅ (AssemblyAI) |
| Стоимость | 💸 Дорого (объём минут) | 💲 Pay-as-you-go |
| Программный API (по URL) | ✅ | ✅ |
| Документация | Средняя | Отличная |

## Архитектура

```
/online команда
      │
      ▼
recall_client.create_bot(meeting_url, api_key)
      │  → bot_id
      ▼
pipeline_recall_bio.run_online_meeting_background(bot_id, ...)
      │  (в фоне, polling статуса)
      ▼
recall_client.wait_for_done(bot_id)
      │  → status == "done"
      ▼
recall_client.get_transcript(bot_id)
      │  → текст с разбивкой по спикерам
      ▼
pipeline_mymeet_bio.run_pipeline_from_transcript_sync(...)
      │  → LLM bio + уточняющие вопросы
      ▼
exports/client_{telegram_id}_{username}/
```

## Этапы

### Этап 1 — Кодовая база (выполнено)
- [x] `recall_client.py` — клиент Recall.ai API
- [x] `pipeline_recall_bio.py` — пайплайн (аналог pipeline_mymeet_bio.py)
- [x] `config.py` — добавить `RECALL_API_KEY`, `RECALL_REGION`
- [x] `.env.example` — задокументировать новые переменные
- [x] `main.py` — подключить recall к `/online` команде

### Этап 2 — Конфигурация (нужен API ключ)
- [ ] Зарегистрироваться на recall.ai
- [ ] Создать API ключ: Settings → API Keys
- [ ] Добавить `RECALL_API_KEY` в `.env` локально и на сервере
- [ ] Установить `TRANSCRIBER=recall` в `.env`

### Этап 3 — Тестирование
- [ ] Запустить тест с реальным Google Meet
- [ ] Проверить транскрипт (русский язык, диаризация)
- [ ] Проверить запись в `exports/client_*/`

## Конфигурация Recall.ai

```
RECALL_API_KEY=<ключ из дашборда recall.ai>
RECALL_REGION=us-east-1   # или eu-west-2, us-west-2
TRANSCRIBER=recall
```

ASR провайдер по умолчанию: `assembly_ai` (наш `ASSEMBLYAI_API_KEY` используется через Recall.ai).

## Ссылки

- Дашборд: https://www.recall.ai/
- Документация API: https://docs.recall.ai/
- Pricing: https://www.recall.ai/pricing
