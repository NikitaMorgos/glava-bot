# TMA Cabinet — архитектура

## URL и домены

| Сервис | URL |
|--------|-----|
| Mini App (фронтенд) | https://app.glava.family |
| API авторизации | https://app.glava.family/api/tma/auth |
| API дашборд | https://app.glava.family/api/tma/dashboard |
| API вопросы | https://app.glava.family/api/tma/questions |

## Поток авторизации

```
Пользователь нажимает кнопку в Telegram
    → Telegram открывает https://app.glava.family
    → JS: const initData = Telegram.WebApp.initData
    → POST /api/tma/auth { init_data: initData }
    → Flask: HMAC-SHA256("WebAppData", BOT_TOKEN) → проверяет hash
    → Flask возвращает { token, user }
    → JS сохраняет token, запрашивает /api/tma/dashboard
```

## Верификация initData (HMAC-SHA256)

По алгоритму Telegram: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app

```python
secret_key = HMAC-SHA256(key=b"WebAppData", msg=bot_token)
data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
expected_hash = HMAC-SHA256(key=secret_key, msg=data_check_string)
```

## Nginx конфиг (app.glava.family)

```nginx
server {
    server_name app.glava.family;
    root /var/www/tma;           # tma/index.html
    location /api/tma/ {
        proxy_pass http://127.0.0.1:5000;
    }
}
```

## Кнопки в боте

| Тип | Код | Где видно |
|-----|-----|-----------|
| `MenuButtonWebApp` | `set_chat_menu_button(...)` | Иконка снизу слева в чате |
| `InlineKeyboardButton(web_app=...)` | в `/start` ответе | Внутри пузыря сообщения |
| `KeyboardButton(web_app=...)` | **не реализовано** | Постоянная клавиатура + "Open" в списке чатов |

## Переменные окружения

| Переменная | Использование |
|-----------|---------------|
| `BOT_TOKEN` | Верификация initData в `tma_api.py` |
| `CABINET_SECRET_KEY` | Подпись stateless-токена |
| `DATABASE_URL` | Получение данных пользователя |
| `S3_*` | Presigned URL для скачивания файлов |
