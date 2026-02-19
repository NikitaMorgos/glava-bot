# GLAVA Bot — Pre-pay flow

Старый CJM v3 (State Machine) удалён. Используется только Pre-pay flow.

## Запуск

```bash
python main.py
```

Миграция БД (один раз): `psql -d your_db -f sql/add_draft_orders.sql`

## Текущий флоу

START → Intro (пример, цены) → Конфиг персонажей → Email → Сводка заказа → Оплата → Ожидание

См. ТЗ: Pre-pay flow.
