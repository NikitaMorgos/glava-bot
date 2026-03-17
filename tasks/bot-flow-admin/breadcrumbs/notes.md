# Bot Flow в админке — заметки

## 2026-03-06

- Реализовано по аналогии с книгой: тексты в админке, схема сценария — в админке.
- Сообщения хранятся в `prompts` (role = `bot_<key>`), без новой миграции.
- API: GET /api/prompts/bot_<key> — уже существовал.
- Модуль `bot_messages.py` — get_message(key, **vars), кеш 60 сек, fallback на prepay.messages.
- Раздел «Сообщения бота» в админке Даши — список 19 ключей, редактирование.
- Страница «Сценарий бота» — схема флоу.
- n8n workflow для сценария — опционально, отложено.

## 2026-03-17 — Деплой

- `git push` → `git pull` на сервере, 10 файлов обновлено.
- `python scripts/seed_bot_messages.py` — 19 сообщений добавлено в БД.
- `sudo systemctl restart glava` + `glava-admin`.
- **Проблема:** gunicorn после перезапуска принимал TCP-соединения, но не отвечал на HTTP (504 Gateway Timeout от nginx). Диагностика показала, что воркер завис на предыдущем запросе (curl --max-time). Решение: `sudo systemctl restart glava-admin` → после чистого старта gunicorn ответил `302` и всё заработало.
- Итог: https://admin.glava.family → Даша → «Сообщения бота» ✅
