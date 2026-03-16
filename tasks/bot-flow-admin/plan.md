# Bot Flow в админке — план

## Цель

Даша (продакт) может менять тексты сообщений бота и видеть сценарий без участия разработчика.

## Этапы

### 1. Сообщения бота в админке ✅
- Использовать таблицу `prompts` с role = `bot_<key>` (без новой миграции)
- Ключи: intro_main, intro_example, intro_price, config_characters, config_characters_list, email_input, email_error, order_summary, payment_init, payment_wait, payment_still_pending, resume_draft, resume_payment, blocked_media, online_meeting_*, ...
- Раздел «Сообщения бота» в админке Даши — список, редактирование
- API GET /api/prompts/bot_<key> — уже есть
- Миграция: seed дефолтных текстов в prompts

### 2. Бот читает из API
- Модуль `bot_messages.py` — get_message(key, **vars) для шаблонов
- Вызов Admin API, кеш 1–5 мин
- Fallback на `prepay.messages` если API недоступен

### 3. Схема сценария в админке
- Страница «Сценарий бота» — диаграмма из docs/USER_SCENARIOS.md (Mermaid или статика)
- Ссылка на полное описание

### 4. n8n workflow Bot Flow (опционально)
- Webhook: получает { telegram_id, state, action_type, action_data, context }
- Switch по state + action_type → Respond to Webhook { reply_key, next_state }
- Бот вызывает n8n перед отправкой ответа, подставляет reply_key
- Требует рефакторинга main.py — отложить на Phase 2

## Ограничения

- Шаблоны с {placeholders} — бот подставляет после получения текста
- Сценарий (порядок шагов, FSM) — пока в коде; n8n — при необходимости позже
