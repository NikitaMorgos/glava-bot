# Чек-лист задачи: Промо-коды

## БД и миграция

- [x] Создать `scripts/migrate_promo.py`
- [x] Создать таблицу `promo_codes`
- [x] Создать таблицу `promo_usages`
- [x] Добавить `promo_code_id` в `draft_orders`
- [x] Добавить `discount_amount` в `draft_orders`
- [x] Запустить миграцию на сервере

## Модуль DB

- [x] Создать `db_promo.py`
- [x] `validate_promo()` — проверка активности, срока, лимита, дубликата
- [x] `apply_promo()` — применение, лог, инкремент used_count
- [x] `remove_promo_from_draft()` — откат применения
- [x] `generate_personal_promo()` — уникальный код GLAVA-XXXXXX
- [x] `get_users_needing_personal_promo()` — окно 47–49ч
- [x] `mark_promo_sent()` — фиксация sent_at
- [x] `get_promo_by_draft()` — для summary
- [x] `calc_discount()` — расчёт скидки в копейках

## Config

- [x] `PERSONAL_PROMO_DELAY_HOURS = 48`
- [x] `PERSONAL_PROMO_DISCOUNT_PERCENT = 15`
- [x] `PERSONAL_PROMO_VALID_HOURS = 24`

## Телеграм-бот

- [x] `kb_order_summary(draft_id, promo_applied)` — кнопка промо
- [x] `kb_promo_cancel(draft_id)` — кнопка отмены ввода
- [x] Сообщения: `PROMO_ENTER_MSG`, `PROMO_SUCCESS_MSG`, `PROMO_ERROR_MSG`, `PERSONAL_PROMO_MSG`
- [x] Сообщение `ORDER_SUMMARY_PROMO_MSG` — сводка со скидкой
- [x] Обработчик `promo_enter:<draft_id>`
- [x] Обработчик `promo_cancel:<draft_id>`
- [x] Обработчик `promo_remove:<draft_id>`
- [x] Состояние `awaiting_promo` в `_handle_prepay_text`
- [x] `_build_summary_msg()` — показывает скидку в сводке
- [x] `get_final_price()` в `db_draft.py` — итоговая цена для оплаты
- [x] Планировщик `_send_personal_promos` зарегистрирован в `job_queue`
- [x] Установлен `python-telegram-bot[job-queue]`

## Админка

- [x] `get_promo_codes()` в `admin/db_admin.py`
- [x] `get_promo_code(id)` в `admin/db_admin.py`
- [x] `create_promo_code(...)` в `admin/db_admin.py`
- [x] `deactivate_promo_code(id)` в `admin/db_admin.py`
- [x] `activate_promo_code(id)` в `admin/db_admin.py`
- [x] `get_promo_usages(promo_id)` в `admin/db_admin.py`
- [x] `get_promo_stats()` в `admin/db_admin.py`
- [x] `export_promo_codes_csv()` в `admin/db_admin.py`
- [x] Маршрут `GET /lena/promo`
- [x] Маршрут `GET/POST /lena/promo/new`
- [x] Маршрут `POST /lena/promo/<id>/deactivate`
- [x] Маршрут `POST /lena/promo/<id>/activate`
- [x] Маршрут `GET /lena/promo/<id>/usages`
- [x] Маршрут `GET /lena/promo/export.csv`
- [x] Шаблон `promos.html` — список + дашборд
- [x] Шаблон `promo_new.html` — форма создания
- [x] Шаблон `promo_usages.html` — история применений
- [x] Ссылка в навигации `base.html`

## Документация

- [x] Инструкция для Лены `docs/PROMO_LENA.md`
- [x] Инструкция для пользователя `docs/PROMO_USER.md`
- [x] PDF `docs/PROMO_CODES.pdf`
- [x] Каталог задачи `task-promo-codes/`

## Деплой

- [x] Все файлы задеплоены на сервер `72.56.121.94`
- [x] `glava.service` перезапущен — бот работает
- [x] `glava-admin.service` перезапущен — админка работает
- [x] Планировщик `personal_promos` активен (APScheduler)
