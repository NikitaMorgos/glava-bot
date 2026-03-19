# Задача: Bot Scenario v2 — по постановке Даши

## Источник
- `glava-bot-spec.md` — ТЗ навигации и логики экранов v2
- `glava-userflow-v2.html` — визуальная схема

## State Machine (spec v2)

```
no_project → draft → payment_pending → paid
→ narrators_setup → collecting_interview_1
→ processing_interview_1 → awaiting_interview_2
→ collecting_interview_2 → assembling
→ book_ready → revision_N → revision_processing
→ book_updated → finalized | refund_requested
```

## Что меняется

| Слой | Файл | Изменение |
|------|------|-----------|
| БД | `scripts/migrate_bot_v2.py` | Новые поля: narrators, bot_state, revision_count, photo_type, interview_round |
| БД layer | `db_draft.py` | Функции: narrator CRUD, set_bot_state, get_bot_state, revision_count |
| Сообщения | `prepay/messages.py` | Все новые тексты экранов 6–15 |
| Клавиатуры | `prepay/keyboards.py` | Все новые inline keyboards |
| bot_messages | `bot_messages.py` | Новые ключи в _FALLBACK_MAP |
| Бот | `main.py` | Новые хендлеры: нарраторы, гид по интервью, загрузка, ревизии, финализация, возврат |
| Состояния | `admin/db_admin.py` | VALID_STATES расширены под spec v2 |
| Админ панель | `admin/blueprints/dasha.py` | Раздел управления текстами бота |
| Сид | `scripts/seed_bot_messages_v2.py` | Сид новых сообщений в БД |

## Ключевые правила spec

- 1 персонаж на заказ (один hero + один character_relation)
- Нарраторы отдельно от персонажа (кто рассказывает)
- Двухинтервьюная модель
- Максимум 3 круга правок (revision_count)
- Debounce 3 минуты перед отправкой правки в AI
- Фото двух типов: photo / document
- Блок на медиа до оплаты → «Сначала оформите заказ»
