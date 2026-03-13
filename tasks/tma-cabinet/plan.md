# TMA Cabinet — план задачи

## Цель

Telegram Mini App — личный кабинет пользователя прямо внутри Telegram.
Без логина/пароля: авторизация через Telegram (initData).
Дополняет, но не заменяет cabinet.glava.family.

## Архитектура

```
main.py → кнопка "📱 Мой кабинет" (WebApp)
    │
    ▼
https://app.glava.family  (tma/index.html, Nginx)
    │
    ├── Telegram.WebApp.initData → POST /api/tma/auth
    │       └── Flask verifies HMAC → возвращает JWT-токен
    │
    ├── GET /api/tma/dashboard  → голосовые + фото + bio
    ├── GET /api/tma/questions  → вопросы для интервью
    └── (всё через Authorization: Bearer <token>)
```

## Компоненты

| Файл | Назначение |
|------|------------|
| `tma/index.html` | Единственный HTML-файл Mini App |
| `cabinet/tma_api.py` | Flask Blueprint с API-эндпоинтами |
| `cabinet/app.py` | Регистрация Blueprint |
| `deploy/nginx-glava.conf` | Поддомен `app.glava.family` |
| `main.py` | Кнопка WebApp в боте |

## Экраны Mini App

1. **Загрузка** — инициализация Telegram.WebApp, авторизация
2. **Дашборд** — голосовые записи, фото, биография
3. **Вопросы** — список вопросов для интервью по блокам
4. **Материалы** — кнопки скачать/прослушать

## Этапы

- [x] Структура задачи
- [ ] `cabinet/tma_api.py` — Blueprint с HMAC-верификацией и JSON API
- [ ] `tma/index.html` — фронтенд Mini App
- [ ] `cabinet/app.py` — подключить Blueprint
- [ ] `main.py` — кнопка WebApp
- [ ] `deploy/nginx-glava.conf` — поддомен app.glava.family
- [ ] Деплой и тест
