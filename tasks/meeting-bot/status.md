# Meeting Bot — бот записи онлайн-разговоров

| Поле | Значение |
|------|----------|
| **Задача** | Self-hosted бот для записи онлайн-созвонов (Telemost, Zoom и др.) |
| **Создана** | 2026-03-17 |
| **Статус** | 🟡 Прототип готов — требуется тест на Linux с pulseaudio |

## Контекст

- MyMeet — дорого, нужен крупный пакет минут
- Recall.ai — проблемы с регистрацией (сайт недоступен из РФ)
- Fireflies.ai — не поддерживает Telemost
- **Выбрано:** Option A — свой headless browser бот (Playwright + Chromium)

## Поддерживаемые платформы

- **Telemost** (Яндекс) — приоритет
- **Zoom** — через ссылку
- **Google Meet, Jitsi** — WebRTC, теоретически поддерживаются

## Технический стек

- **Playwright** — управление браузером
- **Chromium** — единственный практичный выбор (headless, audio capture)
- **pulseaudio / ffmpeg** — захват аудио на Linux
- **Транскрипция** — существующий пайплайн (AssemblyAI / SpeechKit)

## Связанные модули

- `meeting_bot.py` — прототип (Playwright + Chromium, pulseaudio, ffmpeg)
- `main.py` — команда `/online`, провайдер `meeting_bot` при `MEETING_BOT_ENABLED=true`
- `mymeet_client.py` — reference
- `pipeline_mymeet_bio.py` — `run_pipeline_from_transcript_sync` для fallback без n8n

## Включение

В `.env`: `MEETING_BOT_ENABLED=true`  
Приоритет провайдеров: recall → mymeet → meeting_bot (если Linux и включён).

Зависимости: `pip install playwright && playwright install chromium`  
Сервер: pulseaudio, ffmpeg, parec.

Тест: `python scripts/run_meeting_bot_test.py "https://..." 60`
