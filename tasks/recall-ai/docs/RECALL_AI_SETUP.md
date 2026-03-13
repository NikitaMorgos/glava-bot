# Recall.ai — инструкция по настройке

## Что это

[Recall.ai](https://www.recall.ai/) — API для подключения бота к онлайн-встречам (Google Meet, Zoom, Teams).
Бот присоединяется по URL, записывает, транскрибирует через выбранный ASR провайдер.

Используется вместо MyMeet для флоу `/online` в GLAVA.

---

## 1. Регистрация

1. Перейти на https://www.recall.ai/
2. "Get Started" → зарегистрироваться
3. Создать организацию

---

## 2. API ключ

Dashboard → Settings → API Keys → "Create new key"

Скопировать ключ — он показывается один раз.

---

## 3. Переменные окружения

```env
# .env
RECALL_API_KEY=your_key_here
RECALL_REGION=us-east-1    # us-east-1 | eu-west-2 | us-west-2
TRANSCRIBER=recall
```

`ASSEMBLYAI_API_KEY` тоже должен быть задан — Recall.ai передаёт его своему ASR.

---

## 4. Деплой на сервер

```bash
# Добавить переменные
nano /opt/glava/.env

# Перезапустить
sudo systemctl restart glava
sudo journalctl -u glava -n 30
```

---

## 5. Как работает флоу

```
Пользователь: /online → отправляет ссылку на встречу
Бот: recall_client.create_bot(meeting_url)  → bot_id
Бот: pipeline_recall_bio.run_online_meeting_background(bot_id, ...)
  [фоновый поток]
  polling статуса каждые 15 сек → ждём done
  recall_client.get_transcript(bot_id) → текст с спикерами
  run_pipeline_from_transcript_sync(...) → LLM bio + вопросы
  Сохранение в exports/client_{id}_{username}/
```

---

## 6. Поддерживаемые платформы

| Платформа | Статус |
|-----------|--------|
| Google Meet | ✅ |
| Zoom | ✅ |
| Microsoft Teams | ✅ |
| Webex | ✅ |
| Yandex Telemost | ❌ (нет поддержки) |

Для Telemost: файл записи загружается напрямую через AssemblyAI.

---

## 7. Тарификация

Pay-as-you-go: оплата за минуты записи.  
Актуальные цены: https://www.recall.ai/pricing

---

## 8. Диагностика

```bash
# Логи бота
journalctl -u glava -f

# Ожидаемая последовательность
# recall bot created, bot_id=abc123
# recall status: joining_call, ждём...
# recall status: in_call_recording, ждём...
# recall status: done
# Транскрипт получен (N символов)
# Биография сохранена: exports/client_.../bio_story.txt
```

### Возможные ошибки

| Ошибка | Причина | Решение |
|--------|---------|---------|
| 401 Unauthorized | Неверный `RECALL_API_KEY` | Проверить ключ в дашборде |
| `fatal` статус | Бот не смог войти в звонок | Проверить доступность ссылки |
| Пустой транскрипт | ASR не отработал | Проверить `ASSEMBLYAI_API_KEY` |
| Таймаут | Встреча длилась > 2 часов | Увеличить `timeout_sec` в config |
