# TMA Cabinet — заметки и диагностика

## 2026-03-14

### Ошибка авторизации "Ошибка авторизации" в TMA
- **Причина:** `glava-cabinet.service` запущен со старым `BOT_TOKEN` в памяти
- **Решение:** `sudo systemctl restart glava-cabinet` после смены токена в `.env`
- **Урок:** при смене BOT_TOKEN всегда перезапускать оба сервиса: `glava` и `glava-cabinet`

### TypeError при сборке InlineKeyboardMarkup
- **Ошибка:** `TypeError: can only concatenate tuple (not "list") to tuple`
- **Место:** `main.py`, конкатенация `markup.inline_keyboard + [[...]]`
- **Причина:** `markup.inline_keyboard` возвращает `tuple of tuples`, а `[[...]]` — list
- **Решение:** `list(markup.inline_keyboard) + [[...]]`

### set_chat_menu_button глотал ошибки молча
- Уровень логирования был `DEBUG` — в production-логах не видно
- Исправлено: `INFO` для успеха, `ERROR` для ошибки

### Кнопка "Open" в списке чатов — исследование
- `MenuButtonWebApp` установлен корректно (BotFather и API подтверждают)
- Кнопка "📱 Кабинет" отображается в нижнем углу чата ✅
- Шорткат "Open" в списке чатов НЕ появляется
- Аналог "Умный дневник" показывает "Open" — вероятно используют ReplyKeyboardMarkup
- **Вывод:** `MenuButtonWebApp` ≠ chat list "Open". Нужен `ReplyKeyboardMarkup` + `KeyboardButton(web_app=...)`
- Решение отложено

## 2026-03-11 — 2026-03-13

### Phantom bot (telegram.error.Conflict)
- Бот не отвечал из-за второго экземпляра на компьютере коллеги (Dropbox sync)
- **Решение:** отозвать токен в BotFather, выпустить новый
- **Правило:** prod-токен только на сервере, для локальной разработки — отдельный бот

### Устаревший код на сервере (FAQ кнопка)
- Фантомный бот отвечал старым кодом с кнопкой "FAQ"
- После смены токена старый бот перестал работать, GLAVA ответил правильным кодом
