# Статус: bot-scenario-v2

**Дата начала:** 2026-03-19  
**Дата завершения:** 2026-03-19  
**Источник:** glava-bot-spec.md v2, glava-userflow-v2.html  
**Агент:** A (бэкенд)

| Шаг | Статус | Комментарий |
|-----|--------|-------------|
| 1. Структура задачи | ✅ | `tasks/bot-scenario-v2/plan.md`, `status.md` |
| 2. DB migration | ✅ | `scripts/migrate_bot_v2.py` — narrators, bot_state, revision_count, photo_type, interview_round |
| 3. db_draft.py | ✅ | `get_bot_state`, `set_bot_state`, `add_narrator`, `remove_narrator`, `get_narrators`, `increment_revision_count`, `set_pending_revision`, `get_pending_revision`, `clear_pending_revision` |
| 4. Сообщения | ✅ | `prepay/messages.py` — 34 новых константы, `bot_messages.py` — fallback map расширен |
| 5. Клавиатуры | ✅ | `prepay/keyboards.py` — kb_narrators, kb_interview_guide, kb_upload_photos, kb_book_ready, kb_versions_list, kb_refund_reason |
| 6. main.py | ✅ | State machine v2: 17 состояний, двухинтервьюная модель, 3 круга правок, /versions, debounce, refund |
| 7. Admin panel | ✅ | `admin/db_admin.py` — 17 новых состояний; `admin/blueprints/dasha.py` — 55 ключей; `admin/templates/dasha/bot_flow.html` — все экраны 1.1–15.2 |
| 8. Деплой | ✅ | git push → `ops.sh deploy` → migrate_bot_v2.py → seed_bot_messages_v2.py |
| 9. AGENTS.md + PDF | ✅ | Обновлено 2026-03-19 |

## Итог

Полностью реализован новый бот-сценарий v2 по постановке Даши:
- Персонаж + нарраторы (JSONB)
- Двухинтервьюный флоу (с AI-вопросами между интервью)
- 3 круга правок с debounce 3 мин
- Финализация и возврат средств
- Команда `/versions`
- Все тексты управляются из админки (`/dasha/bot_messages`)
- Живая карта флоу (`/dasha/bot_flow`) — экраны 1.1–15.2
