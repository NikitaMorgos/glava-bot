# TMA Cabinet — чеклист подзадач

## Реализовано

- [x] Создать `cabinet/tma_api.py` — Blueprint, HMAC-верификация, эндпоинты
- [x] Создать `tma/index.html` — фронтенд (авторизация, дашборд, вопросы)
- [x] Подключить Blueprint в `cabinet/app.py`
- [x] Настроить `main.py`: MenuButtonWebApp + InlineKeyboardButton
- [x] Настроить Nginx: поддомен app.glava.family + /api/tma/ → Flask
- [x] Задеплоить на сервер
- [x] Исправить TypeError при конкатенации InlineKeyboardMarkup
- [x] Исправить ошибку авторизации после смены BOT_TOKEN (restart cabinet)
- [x] Добавить логирование в `_verify_init_data` и `set_chat_menu_button`
- [x] Зарегистрировать Menu Button в BotFather (app.glava.family)

## Отложено

- [ ] Кнопка "Open" в списке чатов (ReplyKeyboardMarkup + KeyboardButton(web_app=...))
