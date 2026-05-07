# GLAVA — контекст для Claude Code

## Проект

GLAVA — Telegram-бот и AI-пайплайн для создания семейных книг-биографий.
Приём голосовых и фото → транскрипция → биография через цепочку AI-агентов → PDF в Telegram. Оплата через ЮKassa.

## Стек

Python 3.10+, Flask, PostgreSQL, Telegram Bot API, OpenAI (GPT-4o), n8n.

## Правила (всегда, без исключений)

- **`_user_has_paid`** — не отключать, не обходить. Пайплайн только после оплаты.
- **`.env`** — не читать, не редактировать, не выводить содержимое.
- **Промпты** — новая версия = новый файл (`v3.md → v4.md`), не перезаписывать.
- **Формат данных** (`book_draft.json`, `fact_map.json`, `layout.json`) — изменение формата ломает downstream-агентов, всегда предупреждать в комментарии задачи.

## Кто работает в проекте

| Роль | Агент | Ветка | Правила |
|------|-------|-------|---------|
| Тим-лид | Cursor | main, dev | полный доступ |
| Продакт (Даша) | Claude Code | feature/dasha/* | `.cursor/rules/dasha-agent.mdc` |
| Маркетолог (Лена) | Claude Code | feature/lena/* | `.cursor/rules/lena-agent.mdc` |

## В начале сессии

Если ты агент Даши — прочитай `.cursor/rules/dasha-agent.mdc`.
Если ты агент Лены — прочитай `.cursor/rules/lena-agent.mdc`.

## Задачи

Лежат в `collab/tasks/*.md`. Шаблон — `collab/tasks/_template.md` (для Даши) и `collab/tasks/_template_lena.md` (для Лены).

Брать только задачи со статусом `new` или `spec-approved`.
