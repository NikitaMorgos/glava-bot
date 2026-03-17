# Finance Admin — статус задачи

| Поле | Значение |
|------|----------|
| **Задача** | Раздел «Финансы» в панели управления |
| **Создана** | 2026-03-17 |
| **Завершена** | 2026-03-17 |
| **Статус** | ✅ Выполнено и задеплоено |

---

## Решение

Раздел «Финансы» доступен всем ролям (dev / dasha / lena). Новый пользователь не нужен.

| Компонент | Где |
|-----------|-----|
| Учёт расходов | `/finance/expenses` — таблица + форма + справочники |
| P&L отчёт | `/finance/pnl` — сводная таблица по месяцам |
| Статьи расходов | Справочник, редактируется инлайн на странице расходов |
| Инициаторы | Справочник, редактируется инлайн на странице расходов |

---

## Прогресс

| Этап | Статус |
|------|--------|
| `scripts/migrate_finance.py` — 3 таблицы | ✅ |
| `admin/db_finance.py` — SQL-функции | ✅ |
| `admin/blueprints/finance.py` — routes | ✅ |
| Шаблоны: expenses, expense_edit, pnl | ✅ |
| `admin/app.py` — регистрация blueprint | ✅ |
| `admin/templates/base.html` — сайдбар | ✅ |
| Деплой на сервер | ✅ |
| Столбцы периодичность + поведение | ✅ |
| Столбец название (свободный ввод) | ✅ |
| Форма в одну строку, справочники внизу | ✅ |
| Единый доступ для всех ролей (dev/dasha/lena) | ✅ |
| Выручка из заказов в P&L | ⏳ следующая версия |

---

## Деплой (нужно выполнить)

```bash
# Локально
git add scripts/migrate_finance.py admin/db_finance.py \
        admin/blueprints/finance.py admin/app.py \
        admin/templates/base.html \
        admin/templates/finance/
git commit -m "feat: раздел Финансы в админке (расходы + P&L)"
git push origin main

# На сервере
cd /opt/glava && git pull origin main
python scripts/migrate_finance.py
sudo systemctl restart glava-admin
```

### Известная проблема при деплое

После `systemctl restart glava-admin` gunicorn-воркер не запускался — причина: старые фоновые процессы gunicorn удерживали порты (в т.ч. 5003 от тестов). Симптом: `[Errno 98] Address already in use`.
**Лечение:** `pkill -f gunicorn` → `sudo systemctl restart glava-admin` → curl возвращает `302`.

### Проверка

- https://admin.glava.family → любой логин → слева появились «💰 Расходы» и «📊 P&L» ✅
