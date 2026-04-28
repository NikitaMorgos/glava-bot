# Промо-коды GLAVA — план работ

## Постановка задачи

Лена (маркетинг) запросила систему промо-кодов:
- Применяются в Telegram-боте при оформлении заказа
- Управление в разделе `/lena/promo` на `admin.glava.family`
- Параметры: срок действия, номинал (% или фиксированная сумма), тип (общий / персональный)
- Персональные коды: автоматически через 48ч после регистрации, скидка 15%, срок 24ч, уведомление через бот

## Архитектура

```
flowchart TD
    subgraph bot [Telegram Bot]
        B1[Сводка заказа] --> B2[Кнопка: Ввести промо-код]
        B2 --> B3[Валидация кода]
        B3 -->|ok| B4[Пересчёт цены]
        B3 -->|error| B5[Сообщение об ошибке]
        B4 --> B6[Оплата со скидкой]
        Sched[JobQueue, каждый час] --> Sched2[Пользователи ~48ч без персон. промо]
        Sched2 --> Sched3[generate_personal_promo + sendMessage]
    end
    subgraph db [PostgreSQL]
        PC[promo_codes]
        PU[promo_usages]
        DO[draft_orders + promo_code_id + discount_amount]
    end
    subgraph admin [admin.glava.family /lena/promo]
        A1[Список + статистика] --> A2[Создать код]
        A1 --> A3[Деактивировать]
        A1 --> A4[Экспорт CSV]
        A1 --> A5[История применений]
    end
```

## Этапы

### 1. Миграция БД
- Создать таблицы `promo_codes`, `promo_usages`
- Добавить колонки `promo_code_id`, `discount_amount` в `draft_orders`
- Скрипт: `scripts/migrate_promo.py`

### 2. Модуль `db_promo.py`
Общий DB-модуль, используется и ботом, и админкой:
- `validate_promo(code, user_id)` — полная валидация
- `apply_promo(draft_id, promo_id, user_id, discount)` — применение
- `remove_promo_from_draft(draft_id)` — отмена
- `generate_personal_promo(user_id)` — генерация
- `get_users_needing_personal_promo()` — выборка для планировщика
- `mark_promo_sent(promo_id)` — фиксация отправки
- `get_promo_by_draft(draft_id)` — для отображения в summary

### 3. Телеграм-бот
- Кнопка «🎟 Ввести промо-код» в `kb_order_summary()`
- Обработчики: `promo_enter`, `promo_cancel`, `promo_remove`
- Состояние `awaiting_promo` в `_handle_prepay_text`
- Обновлённый `_build_summary_msg` — показывает скидку
- Оплата проходит по итоговой цене (`get_final_price`)
- Планировщик `_send_personal_promos` — каждый час через JobQueue

### 4. Админка
- Маршруты `/lena/promo/*` в `admin/blueprints/lena.py`
- DB-функции в `admin/db_admin.py`
- Шаблоны: `promos.html`, `promo_new.html`, `promo_usages.html`
- Ссылка в навигации `base.html`

### 5. Документация
- Инструкция для Лены (`docs/PROMO_LENA.md`)
- Инструкция для пользователя бота (`docs/PROMO_USER.md`)
- PDF (`docs/PROMO_CODES.pdf`)

## Параметры персонального промо (config.py)

```python
PERSONAL_PROMO_DELAY_HOURS = 48   # через сколько часов после регистрации
PERSONAL_PROMO_DISCOUNT_PERCENT = 15  # скидка %
PERSONAL_PROMO_VALID_HOURS = 24   # срок действия после отправки
```

## Багфиксы после релиза (2026-03-30)

- [x] `validate_promo`: тип `personal` с `assigned_user_id IS NULL` (код из админки) — не блокировать пользователя.
- [x] `promo_enter` / применение промо: разрешить при `payment_pending`; при изменении скидки — сбросить платёж и вернуть к сводке заказа.

## Что не входит в текущую итерацию

- Email-уведомления (откладываем)
- Интеграция с glava.family (форма заказа не построена)
- Управление параметрами 48ч/15%/24ч через UI
