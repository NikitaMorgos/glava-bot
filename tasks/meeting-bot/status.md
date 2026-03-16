# Meeting Bot — статус задачи

| Поле | Значение |
|------|----------|
| **Задача** | Self-hosted бот для записи онлайн-созвонов (Telemost, Zoom и др.) |
| **Создана** | 2026-03-17 |
| **Обновлена** | 2026-03-06 |
| **Статус** | 🟢 Прототип готов, запись работает |

---

## Контекст

- MyMeet — дорого, нужен крупный пакет минут
- Recall.ai — проблемы с регистрацией (сайт недоступен из РФ)
- Fireflies.ai — не поддерживает Telemost
- **Выбрано:** Option A — свой headless browser бот (Playwright + Chromium)

---

## Прогресс

| Этап | Статус | Примечание |
|------|--------|------------|
| `meeting_bot.py` — Playwright + Chromium | ✅ Готово | Join по URL, pulseaudio sink + ffmpeg |
| Интеграция с `main.py` | ✅ Готово | Команда `/online`, провайдер `meeting_bot` при `MEETING_BOT_ENABLED=true` |
| `config.py` + `.env.example` | ✅ Готово | `MEETING_BOT_ENABLED`, `MEETING_JOIN_DEBUG` |
| Тест записи Telemost (60 сек) | ✅ Готово | Файл `/tmp/meeting_xxx.ogg` создаётся |
| Имя бота в Telemost | 🟡 Частично | Бот отображается как «Гость»; селекторы добавлены, iframe-поиск, debug-режим |
| Генерация ссылок Zoom/Telemost | ⏳ Опционально | Не реализовано |
| Деплой (systemd) | ⏳ Ожидает | При необходимости |

---

## Поддерживаемые платформы

- **Telemost** (Яндекс) — приоритет, запись работает
- **Zoom** — через ссылку
- **Google Meet, Jitsi** — WebRTC, теоретически поддерживаются

---

## Технический стек

- **Playwright** — управление браузером
- **Chromium** — headless, audio capture
- **pulseaudio / ffmpeg** — захват аудио на Linux
- **Транскрипция** — существующий пайплайн (AssemblyAI / SpeechKit)

---

## Связанные модули

| Модуль | Назначение |
|--------|------------|
| `meeting_bot.py` | Запись через Playwright, pulseaudio, ffmpeg; имя GlavaBot, поиск в iframe |
| `main.py` | Команда `/online`, провайдер `meeting_bot` при `MEETING_BOT_ENABLED=true` |
| `pipeline_mymeet_bio.py` | `run_pipeline_from_transcript_sync` — fallback без n8n |
| `scripts/run_meeting_bot_test.py` | Тест записи: `python scripts/run_meeting_bot_test.py "URL" 60` |

---

## Включение

```env
# .env
MEETING_BOT_ENABLED=true
# Отладка входа (скриншот + список input в лог):
# MEETING_JOIN_DEBUG=true
```

Приоритет провайдеров: recall → mymeet → meeting_bot (если Linux и включён).

---

## Зависимости (сервер Linux)

```bash
pip install playwright && playwright install chromium
playwright install-deps chromium
# Системные: pulseaudio, pulseaudio-utils, ffmpeg
pulseaudio -D --system  # или pipewire
```

---

## Известные ограничения

- **Имя «Гость» в Telemost** — селекторы для поля имени добавлены (в т.ч. placeholder «Гость»), поиск в iframe. Если не срабатывает — запустить с `MEETING_JOIN_DEBUG=true`, посмотреть лог `DEBUG: frame ... inputs:` и подобрать селектор.
- **Chromium only** — Firefox/Safari headless не подходят для надёжного audio capture
- **Linux** — pulseaudio/pipewire на сервере
