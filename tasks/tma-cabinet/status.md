# TMA Cabinet — статус

| Поле | Значение |
|------|---------|
| **Задача** | Telegram Mini App — личный кабинет |
| **Создана** | 2026-03-11 |
| **Обновлена** | 2026-03-14 |
| **Статус** | 🟡 В работе (пауза) |

## Прогресс

| Этап | Статус |
|------|--------|
| Структура задачи | ✅ |
| `cabinet/tma_api.py` — API + HMAC-верификация | ✅ |
| `tma/index.html` — фронтенд | ✅ |
| `cabinet/app.py` — Blueprint подключён | ✅ |
| `main.py` — кнопка WebApp + MenuButtonWebApp | ✅ |
| `deploy/nginx-glava.conf` — поддомен app.glava.family | ✅ |
| Деплой на сервер | ✅ |
| Авторизация через initData (HMAC) | ✅ |
| TMA открывается и работает в Telegram | ✅ |
| Кнопка "📱 Кабинет" в нижнем меню чата | ✅ |
| Inline-кнопка "Открыть кабинет" в /start | ✅ |
| Кнопка "Open" в списке чатов | ⏸ Пауза — требует ReplyKeyboardMarkup |

## Известные особенности

### Кнопка "Open" в списке чатов Telegram
- `MenuButtonWebApp` ✅ установлен (подтверждено BotFather и логами)
- Кнопка "📱 Кабинет" ✅ отображается внизу слева внутри чата
- Шорткат "Open" в списке чатов ❌ не появляется
- **Причина:** "Open" в списке чатов требует `ReplyKeyboardMarkup` +
  `KeyboardButton(web_app=...)`, а не `MenuButtonWebApp` / `InlineKeyboardButton`
- **Решение:** добавить постоянную reply-клавиатуру с web_app кнопкой
- **Статус:** отложено по решению команды

## Ключевые файлы

| Файл | Назначение |
|------|------------|
| `tma/index.html` | Фронтенд Mini App |
| `cabinet/tma_api.py` | API: auth, dashboard, questions |
| `cabinet/app.py` | Flask-приложение, регистрация Blueprint |
| `deploy/nginx-glava.conf` | Поддомен app.glava.family + /api/tma/ |
| `main.py` | MenuButtonWebApp + inline WebApp кнопка |

## Исправленные баги

| Баг | Решение |
|-----|---------|
| `TypeError: can only concatenate tuple to tuple` | `list(markup.inline_keyboard) + [...]` |
| "Ошибка авторизации" в TMA | Перезапуск `glava-cabinet` после смены BOT_TOKEN |
| `set_chat_menu_button` падал молча | Логирование переведено с DEBUG на INFO/ERROR |
