# Meeting Bot — план работ

## Цель

Бот подключается к онлайн-созвону по ссылке пользователя, записывает аудио, передаёт в пайплайн транскрипции → биография.

## Этапы

### 1. Прототип `meeting_bot.py` ✅
- Playwright + Chromium (non-headless + Xvfb)
- Переход по URL созвона
- Заполнение имени (GlavaBot), клик «Войти» (в т.ч. в iframe)
- Захват аудио (PulseAudio sink + parec + ffmpeg)
- Запись в `.ogg` файл

### 2. Интеграция с ботом ✅
- Команда `/online` — пользователь отправляет ссылку
- Запуск `meeting_bot` в фоне (`record_meeting_background`)
- По окончании — транскрипция через AssemblyAI → пайплайн биографии

### 3. Фикс аудио: Xvfb + non-headless ✅
- Headless Chrome не выводит аудио в PulseAudio
- `_start_xvfb()` запускает виртуальный дисплей `:99` автоматически
- Chrome запускается в обычном (non-headless) режиме

### 4. Фикс PulseAudio под systemd ✅
- systemd не передаёт `XDG_RUNTIME_DIR` — pactl получал "Access denied"
- Добавлены `XDG_RUNTIME_DIR=/run/user/0` и `PULSE_SERVER=unix:/run/user/0/pulse/native` в `.env`

### 5. Авто-остановка по концу встречи ✅
- `_wait_for_meeting_end()`: URL / текст страницы / тишина >45 сек
- Защитный лимит 4 ч вместо 30 мин
- После остановки — немедленный запуск транскрипции

### 6. Имя в Telemost 🟡
- Селекторы для placeholder «Гость», поиск в iframe
- Режим отладки `MEETING_JOIN_DEBUG=true` — скриншот, лог input
- При необходимости — подобрать селектор по выводу debug

### 7. Генерация ссылок ⏳ (опционально)
- Zoom API — создание встречи
- Yandex Telemost API — создание встречи
- Бот отдаёт ссылку пользователю

## Ограничения

- **Chromium only** — Firefox/Safari headless не подходят для надёжного audio capture
- **Linux** — pulseaudio + Xvfb на сервере
- **WebRTC** — платформа должна поддерживать вход по ссылке без инвайта
