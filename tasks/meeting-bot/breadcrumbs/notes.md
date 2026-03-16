# Meeting Bot — заметки

## 2026-03-06

- **Имя «Гость» в Telemost:** бот подключается, но отображается как гость.
- Добавлены селекторы: `input[placeholder*="Гость"]`, поиск в iframe, повторная попытка после клика «Войти».
- Режим отладки `MEETING_JOIN_DEBUG=true` — скриншот `/tmp/meeting_join_debug.png`, лог всех input во всех frame.
- Telemost использует проприетарную платформу Goloom (не Jitsi). Форма входа может быть в iframe.
- Дополнительное ожидание 5 сек для Telemost при загрузке страницы.

## 2026-03-17

- Прототип: Playwright + Chromium, pulseaudio sink, ffmpeg.
- Тест 60 сек в Telemost — успешно, файл создаётся.
- Интеграция с main.py — провайдер meeting_bot при MEETING_BOT_ENABLED.
