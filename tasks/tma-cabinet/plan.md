# TMA Cabinet — план задачи

## Цель

Telegram Mini App — личный кабинет пользователя прямо внутри Telegram.
Без логина/пароля: авторизация через Telegram (initData + HMAC-SHA256).
Дополняет, но не заменяет cabinet.glava.family.

## Архитектура

```
main.py → MenuButtonWebApp "📱 Кабинет"  +  InlineKeyboardButton
    │
    ▼
https://app.glava.family  (tma/index.html, Nginx static)
    │
    ├── Telegram.WebApp.initData → POST /api/tma/auth
    │       └── Flask HMAC-SHA256(BOT_TOKEN) → stateless токен
    │
    ├── GET /api/tma/dashboard  → голосовые + фото + bio
    ├── GET /api/tma/questions  → вопросы для интервью
    └── (всё через Authorization: Bearer <token>)
```

## Компоненты

| Файл | Назначение |
|------|------------|
| `tma/index.html` | Единственный HTML-файл Mini App |
| `cabinet/tma_api.py` | Flask Blueprint с API-эндпоинтами и HMAC |
| `cabinet/app.py` | Регистрация Blueprint |
| `deploy/nginx-glava.conf` | Поддомен `app.glava.family` + проксирование /api/tma/ |
| `main.py` | Кнопка WebApp в боте |

## Этапы

- [x] Структура задачи
- [x] `cabinet/tma_api.py` — Blueprint с HMAC-верификацией и JSON API
- [x] `tma/index.html` — фронтенд Mini App (3 экрана: материалы, биография, вопросы)
- [x] `cabinet/app.py` — подключить Blueprint
- [x] `main.py` — MenuButtonWebApp + InlineKeyboardButton(web_app=...)
- [x] `deploy/nginx-glava.conf` — поддомен app.glava.family
- [x] Деплой на сервер (git pull + systemctl restart)
- [x] Авторизация через initData работает
- [x] Отладка BOT_TOKEN после смены токена
- [ ] Кнопка "Open" в списке чатов (ReplyKeyboardMarkup) — **отложено**

## Отложенное: кнопка "Open" в списке чатов

Чтобы Telegram показывал шорткат "Open" в превью чата (как у некоторых ботов),
нужно отправлять `ReplyKeyboardMarkup` с `KeyboardButton(web_app=WebAppInfo(...))`.

Это отличается от `MenuButtonWebApp` (иконка снизу слева в чате).

**Когда делать:** по запросу, не приоритетно.

**Реализация (когда понадобится):**
```python
from telegram import KeyboardButton, ReplyKeyboardMarkup

reply_kb = ReplyKeyboardMarkup(
    [[KeyboardButton("📱 Открыть кабинет", web_app=WebAppInfo(url=TMA_URL))]],
    resize_keyboard=True,
)
await update.message.reply_text("...", reply_markup=reply_kb)
```
