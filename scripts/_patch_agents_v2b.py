"""Добавляет раздел 'Bot Scenario v2' и обновляет документацию задач в AGENTS.md."""
import pathlib

path = pathlib.Path("AGENTS.md")
content = path.read_text(encoding="utf-8")

# 1. Обновляем список задач — добавляем bot-scenario-v2
old_tasks = "| **tasks/server-ops-access/** | ✅ Выполнено (2026-03-19). SSH без пароля, N8N API, ops.sh с 12 командами. |"
new_tasks = (
    "| **tasks/server-ops-access/** | ✅ Выполнено (2026-03-19). SSH без пароля, N8N API, ops.sh с 12 командами. |\n"
    "| **tasks/bot-scenario-v2/** | ✅ Выполнено (2026-03-19). Бот v2 по постановке Даши: нарраторы, 2 интервью, 3 круга правок, возврат, /versions. |"
)
content = content.replace(old_tasks, new_tasks)

# 2. Добавляем раздел про Bot Scenario v2 после State Machine n8n
insert_marker = "Реализован в `admin/db_admin.py`. Переходы через `POST /api/state/transition`."

bot_v2_section = """

---

## Бот — сценарий v2 (spec Даши)

> Реализовано: 2026-03-19. Задача: `tasks/bot-scenario-v2/`. Спек: `glava-bot-spec.md`, схема: `glava-userflow-v2.html`.

### State Machine бота

```
no_project → draft → payment_pending → paid
→ narrators_setup → collecting_interview_1 → processing_interview_1
→ awaiting_interview_2 → collecting_interview_2 → assembling
→ book_ready → revision_N → revision_processing → book_updated → finalized
                                                 ↘ refund_requested
```

| Состояние | Описание | Экран |
|-----------|---------|-------|
| `no_project` | Новый пользователь | → 1.1 |
| `draft` | Заполняет данные (персонаж, email) | → 2.1–3.1 |
| `payment_pending` | Ожидает оплаты | → 4.2 |
| `paid` | Оплачено, настройка нарраторов | → 6.1 |
| `narrators_setup` | Добавляет рассказчиков | 6.1 |
| `collecting_interview_1` | Загружает первое интервью + фото | 8.1–8.4 |
| `processing_interview_1` | AI обрабатывает первое интервью | 8.5 |
| `awaiting_interview_2` | Показаны AI-вопросы, ждёт решения | 8.6 |
| `collecting_interview_2` | Загружает второе интервью | 9.1 |
| `assembling` | AI собирает книгу (Phase A) | 10.1 |
| `book_ready` | Книга v1 готова | 10.2 |
| `revision_1/2/3` | Пользователь пишет правку | 11.1 |
| `revision_processing` | AI вносит правки (Phase B) | 11.2 |
| `book_updated` | Обновлённая книга готова | 11.3 |
| `finalized` | Книга зафиксирована | 14.1 |
| `refund_requested` | Запрошен возврат средств | 15.2 |

### Ключевые правила

- **Нарраторы** (`narrators` JSONB в `draft_orders`) — люди, которые рассказывают историю персонажа. Отдельно от персонажа (hero).
- **Один персонаж** на заказ: `character_name` + `character_relation`.
- **Двухинтервьюная модель**: первое интервью → AI-вопросы (8.6) → опциональное второе → сборка.
- **3 круга правок**: `revision_count` ≤ 3. После 3-го кнопка «Ещё комментарий» скрыта.
- **Debounce 3 минуты**: несколько сообщений подряд собираются в `pending_revision` → отправляются одним блоком через `revision_deadline`.
- **Фото двух типов**: `photo_type = 'photo' | 'document'` — хранится в таблице `photos`.
- **bot_state** хранится в `draft_orders.bot_state` — первичный источник маршрутизации для `/start`.

### Новые функции `db_draft.py`

| Функция | Назначение |
|---------|-----------|
| `get_bot_state(telegram_id)` | Текущее состояние пользователя |
| `set_bot_state(draft_id, state)` | Установить состояние |
| `add_narrator(draft_id, name, relation)` | Добавить нарратора |
| `remove_narrator(draft_id, narrator_id)` | Удалить нарратора |
| `get_narrators(draft_id)` | Список нарраторов |
| `increment_revision_count(draft_id)` | +1 к счётчику правок |
| `set_pending_revision(draft_id, text, minutes=3)` | Сохранить правку с debounce |
| `get_pending_revision(draft_id)` | `(text, is_ready)` — готова ли к отправке |
| `clear_pending_revision(draft_id)` | Очистить после отправки |

### Управление текстами бота (для Даши)

Все тексты экранов хранятся в таблице `prompts` (ключ `bot_<screen_key>`).  
Редактирование: **admin.glava.family/dasha/bot_messages** — 55 ключей, сгруппированных по номерам экранов.  
Живая карта флоу: **admin.glava.family/dasha/bot_flow** — все экраны 1.1…15.2 с текстами из БД и ссылками «↗ редактировать».

### Команда `/versions`

Новая команда — список всех версий книги. Запрашивает `/api/book-context/<telegram_id>`, показывает inline-кнопки «📄 Открыть» и «↩️ Откатить» для каждой версии.
"""

content = content.replace(
    insert_marker,
    insert_marker + bot_v2_section
)

path.write_text(content, encoding="utf-8")
print("OK")
