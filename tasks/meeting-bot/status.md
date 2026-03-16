# Meeting Bot — бот записи онлайн-разговоров

| Поле | Значение |
|------|----------|
| **Задача** | Self-hosted бот для записи онлайн-созвонов (Telemost, Zoom и др.) |
| **Создана** | 2026-03-17 |
| **Статус** | 📋 Планирование — следующий этап после Phase A v5 |

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

- `mymeet_client.py` — текущий клиент MyMeet (reference)
- `pipeline_mymeet_bio.py` — пайплайн после получения транскрипта
- `main.py` — команда `/online`
