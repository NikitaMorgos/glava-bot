# Finance Admin — статус задачи

| Поле | Значение |
|------|----------|
| **Задача** | Раздел «Финансы» в панели управления |
| **Создана** | 2026-03-17 |
| **Статус** | 🟡 Готово к деплою |

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
| Деплой на сервер | ⏳ |
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

### Проверка

- https://admin.glava.family → любой логин → слева появились «Финансы»
- «💰 Расходы» — добавить тестовый расход, проверить фильтр по месяцу
- «📊 P&L» — должна показать строки по статьям
