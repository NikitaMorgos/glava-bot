# Meeting Bot — чеклист

## Запуск теста записи

- [ ] Сервер Linux с pulseaudio (или pipewire)
- [ ] Установлены: `playwright`, `chromium`, `ffmpeg`, `parec`
- [ ] pulseaudio запущен: `pulseaudio -D --system`
- [ ] В `.env`: `MEETING_BOT_ENABLED=true`
- [ ] Запуск: `python scripts/run_meeting_bot_test.py "https://telemost.yandex.ru/j/xxx" 60`
- [ ] Проверить: файл `/tmp/meeting_xxx.ogg` создан, размер > 1 KB

## Отладка имени в Telemost

Если бот отображается как «Гость»:

- [ ] Добавить в `.env`: `MEETING_JOIN_DEBUG=true`
- [ ] Запустить тест, посмотреть лог: `DEBUG: frame ... inputs:`
- [ ] Скриншот: `/tmp/meeting_join_debug.png`
- [ ] По выводу inputs подобрать селектор и добавить в `meeting_bot.py` (name_selectors)

## Интеграция с ботом

- [ ] Пользователь отправляет ссылку в `/online`
- [ ] Бот запускает `record_meeting_background`
- [ ] После записи — транскрипция → bio → уточняющие вопросы
