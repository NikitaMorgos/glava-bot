# Meeting Bot — документация

Self-hosted бот записи онлайн-созвонов (Telemost, Zoom) через Playwright + Chromium.

## Архитектура

```
Пользователь → /online + ссылка → main.py
    → meeting_bot.record_meeting_background()
        → Playwright: goto URL, fill name, click Join
        → pulseaudio sink (glava_meeting_rec) + parec + ffmpeg
        → /tmp/meeting_xxx.ogg
    → pipeline_*_bio (транскрипция → bio)
```

## Переменные окружения

| Переменная | Описание |
|------------|----------|
| `MEETING_BOT_ENABLED` | `true` — включить провайдер meeting_bot |
| `MEETING_JOIN_DEBUG` | `true` — скриншот и лог input для отладки имени |

## Селекторы имени

Бот пытается заполнить поле имени перед входом. Селекторы (в порядке приоритета):

- `input[placeholder*="Гость"]`, `input[placeholder*="гость"]`, `input[placeholder*="Guest"]`
- `input[name="name"]`, `input[placeholder*="имя"]`, `#inputname`
- `input[type="text"]`, `[contenteditable="true"]`

Поиск выполняется в main frame и во всех iframe.

## Команды

```bash
# Тест записи (60 сек)
python scripts/run_meeting_bot_test.py "https://telemost.yandex.ru/j/xxx" 60

# С отладкой имени
MEETING_JOIN_DEBUG=true python scripts/run_meeting_bot_test.py "URL" 60
```

## Ограничения

- Только Linux (pulseaudio)
- Только Chromium (Firefox headless не поддерживает audio capture)
- Имя в Telemost может не подставляться — зависит от структуры страницы
