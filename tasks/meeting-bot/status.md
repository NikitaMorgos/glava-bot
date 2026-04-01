# Meeting Bot — статус задачи

| Поле | Значение |
|------|----------|
| **Задача** | Self-hosted бот для записи онлайн-созвонов (Telemost, Zoom и др.) |
| **Создана** | 2026-03-17 |
| **Обновлена** | 2026-04-01 |
| **Статус** | ✅ Работает в продакшне |

---

## Контекст

- MyMeet — дорого, нужен крупный пакет минут
- Recall.ai — не поддерживает Telemost; сайт недоступен из РФ
- Fireflies.ai — не поддерживает Telemost
- **Выбрано:** Option A — свой бот (Playwright + Chromium + Xvfb + PulseAudio)

---

## Прогресс

| Этап | Статус | Примечание |
|------|--------|------------|
| `meeting_bot.py` — Playwright + Chromium | ✅ Готово | Join по URL, pulseaudio sink + ffmpeg |
| Интеграция с `main.py` | ✅ Готово | `/online`, провайдер `meeting_bot` при `MEETING_BOT_ENABLED=true` |
| `config.py` + `.env.example` | ✅ Готово | `MEETING_BOT_ENABLED`, `PULSE_SERVER`, `XDG_RUNTIME_DIR` |
| Приоритет провайдеров | ✅ Готово | meeting_bot → mymeet → recall |
| Xvfb + non-headless Chrome | ✅ Готово | Headless не выводит аудио в PulseAudio; Xvfb запускается автоматически |
| PulseAudio под systemd | ✅ Готово | `PULSE_SERVER` + `XDG_RUNTIME_DIR` в `.env` |
| Реальная запись в Telemost | ✅ Протестировано | 707 KB, ~12 мин, OPUS 64kbps |
| Транскрипция AssemblyAI | ✅ Протестировано | Диаризация по спикерам, русский язык |
| Авто-остановка по концу встречи | ✅ Готово | URL / текст / тишина >45 сек; лимит 4 ч |
| Имя бота в Telemost | 🟡 Частично | Бот отображается как «Гость»; debug-режим `MEETING_JOIN_DEBUG=true` |
| Генерация ссылок Zoom/Telemost | ⏳ Опционально | Не реализовано |

---

## Поддерживаемые платформы

- **Telemost** (Яндекс) — приоритет, протестировано ✅
- **Zoom** — через ссылку
- **Google Meet, Jitsi** — WebRTC, теоретически поддерживаются

---

## Технический стек

- **Playwright** — управление браузером
- **Chromium** (non-headless) + **Xvfb** `:99` — виртуальный дисплей для аудио
- **PulseAudio** — виртуальный sink `glava_meeting_rec`; `parec` → `ffmpeg` → `.ogg`
- **AssemblyAI** — транскрипция с диаризацией, язык `ru`
- **n8n Phase A** (или fallback `pipeline_mymeet_bio`) — пайплайн биографии

---

## Связанные модули

| Модуль | Назначение |
|--------|------------|
| `meeting_bot.py` | Xvfb + Chromium, PulseAudio, ffmpeg; авто-стоп по URL/тексту/тишине |
| `main.py` | Команда `/online`, `_online_meeting_provider`, `_start_online_meeting_recording` |
| `assemblyai_client.py` | Транскрипция через AssemblyAI |
| `pipeline_mymeet_bio.py` | `run_pipeline_from_transcript_sync` — fallback без n8n |
| `scripts/run_meeting_bot_test.py` | Тест записи: `python scripts/run_meeting_bot_test.py "URL" 60` |

---

## Включение (.env на сервере)

```env
MEETING_BOT_ENABLED=true
XDG_RUNTIME_DIR=/run/user/0
PULSE_SERVER=unix:/run/user/0/pulse/native
ASSEMBLYAI_API_KEY=...
ALLOW_ONLINE_WITHOUT_PAYMENT=true   # только для теста, потом убрать
```

Приоритет провайдеров: **meeting_bot** → mymeet → recall.

---

## Зависимости (сервер Linux)

```bash
pip install playwright && playwright install chromium
apt install xvfb pulseaudio pulseaudio-utils ffmpeg
```

---

## Авто-остановка записи

`_wait_for_meeting_end()` проверяет каждые 10 сек:
1. **URL** — если страница ушла с домена встречи
2. **Текст** — фразы «встреча завершена», «meeting ended» и др.
3. **Тишина** — PulseAudio sink IDLE/SUSPENDED >45 сек

Защитный лимит: 4 часа (`duration_sec=14400`).

---

## Известные ограничения

- **Имя «Гость» в Telemost** — `MEETING_JOIN_DEBUG=true` даёт скриншот и лог input-полей
- **Chromium only** — Firefox/Safari headless не подходят
- **Linux** — требуется pulseaudio/pipewire + Xvfb на сервере
