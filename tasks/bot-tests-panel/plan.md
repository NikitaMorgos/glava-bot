# Plan: bot-tests-panel

**Цель:** покрыть тестами все ветки бот-сценария v2 и дать Даше панель запуска тестов в админке.

## Компоненты

### 1. tests/test_bot_flows_v2.py — TC-28…TC-41
Тесты на pytest с моками db/db_draft/storage. Покрывают:
- /start при разных bot_state
- нарраторы: добавить, удалить, продолжить
- загрузка материалов → collecting_interview_1
- awaiting_interview_2: вопросы, пропуск, 2-е интервью
- сборка книги (assembling)
- правки: debounce, лимит
- финализация, возврат

### 2. admin/db_admin.py — таблица test_runs + функции
- `save_test_run(results, summary)` — сохраняет run в БД
- `get_test_runs(limit=10)` — список последних run'ов

### 3. scripts/migrate_test_runs.py — миграция
- CREATE TABLE test_runs

### 4. admin/blueprints/dasha.py — маршруты
- GET  /dasha/bot_tests    — страница панели
- POST /dasha/bot_tests/run — запуск pytest, возврат JSON

### 5. admin/templates/dasha/bot_tests.html — UI
- Кнопка «▶ Запустить все тесты»
- Таблица результатов (TC, статус, время, traceback)
- Сводка (N/M), история запусков, фильтр «только упавшие»

## Затронутые файлы
- `tests/test_bot_flows_v2.py` (новый)
- `admin/db_admin.py` (добавить функции)
- `scripts/migrate_test_runs.py` (новый)
- `admin/blueprints/dasha.py` (маршруты)
- `admin/templates/dasha/bot_tests.html` (новый)
- `AGENTS.md` / `AGENTS.pdf` (обновить)
