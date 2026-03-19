"""Обновляет AGENTS.md: добавляет раздел про тесты v2 и панель тестов."""
import pathlib

path = pathlib.Path("AGENTS.md")
content = path.read_text(encoding="utf-8")

# 1. Обновляем таблицу задач
old_task = "| **tasks/bot-scenario-v2/** | ✅ Выполнено (2026-03-19). Бот v2 по постановке Даши: нарраторы, 2 интервью, 3 круга правок, возврат, /versions. |"
new_task = old_task + "\n| **tasks/bot-tests-panel/** | ✅ Выполнено (2026-03-19). Авто-тесты v2 (TC-28…TC-44) + панель запуска в админке `/dasha/bot_tests`. |"
content = content.replace(old_task, new_task)

# 2. Добавляем строки в таблицу ключевых путей
old_test_row = "| Автотесты бота | `tests/test_bot_flows.py` |"
new_test_row = "| Автотесты бота (pre-pay) | `tests/test_bot_flows.py` — TC-01…TC-27 |\n| **Авто-тесты бота v2** | `tests/test_bot_flows_v2.py` — TC-28…TC-44 (нарраторы, интервью, правки, финализация) |"
content = content.replace(old_test_row, new_test_row)

# 3. Обновляем секцию TESTING.md в документации
old_testing = "| **docs/TESTING.md** | Система тестирования: тест-кейсы TC-01…TC-27, протокол запуска, отчёты. |"
new_testing = "| **docs/TESTING.md** | Система тестирования: тест-кейсы TC-01…TC-27 (pre-pay) + TC-28…TC-44 (v2 сценарий), протокол запуска, отчёты. |"
content = content.replace(old_testing, new_testing)

# 4. Добавляем раздел про панель тестов в маршруты /api
old_api_health = "| GET | `/api/health` | Проверка живости сервиса |"
new_api_health = old_api_health + "\n\n### Маршруты /dasha/bot_tests\n\n| Метод | Путь | Назначение |\n|-------|------|-----------|\n| GET | `/dasha/bot_tests` | Панель авто-тестов: история, кнопки запуска |\n| POST | `/dasha/bot_tests/run` | Запустить pytest; body: `{only_v2: bool}`; возврат JSON |\n| GET | `/dasha/bot_tests/run/<id>` | Детали конкретного запуска (JSON) |"
content = content.replace(old_api_health, new_api_health)

path.write_text(content, encoding="utf-8")
print("OK")
