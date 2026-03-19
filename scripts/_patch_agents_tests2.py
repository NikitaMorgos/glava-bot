"""Обновляет AGENTS.md: фиксирует финальное состояние задачи bot-tests-panel."""
import pathlib

path = pathlib.Path("AGENTS.md")
content = path.read_text(encoding="utf-8")

# 1. Обновляем запись задачи — добавляем уточнение про json-report
old = "| **tasks/bot-tests-panel/** | ✅ Выполнено (2026-03-19). Авто-тесты v2 (TC-28…TC-44) + панель запуска в админке `/dasha/bot_tests`. |"
new = "| **tasks/bot-tests-panel/** | ✅ Выполнено (2026-03-19). Авто-тесты v2 (TC-28…TC-44) + панель `/dasha/bot_tests`; вывод через pytest-json-report, история в БД. |"
content = content.replace(old, new)

# 2. Обновляем запись про requirements-dev.txt
old2 = "- **Зависимости:** `requirements.txt`, для тестов — `pytest`, `pytest-asyncio` (см. `requirements-dev.txt`)."
new2 = "- **Зависимости:** `requirements.txt`, для тестов — `pytest`, `pytest-asyncio`, `pytest-json-report` (см. `requirements-dev.txt`)."
content = content.replace(old2, new2)

# 3. Добавляем команду запуска тестов с json-report
old3 = "**Тесты (локально):**\n```bash\npytest tests/ -v\n# или с отчётом\npython scripts/run_test_report.py\n```\nТесты не требуют реальных ключей и БД (моки). Протокол и периодичность — `docs/TESTING.md`."
new3 = """**Тесты (локально):**
```bash
pytest tests/ -v
# или с отчётом
python scripts/run_test_report.py
# v2 тесты с json-отчётом
pytest tests/test_bot_flows_v2.py -v --json-report --json-report-file=report.json
```
Тесты не требуют реальных ключей и БД (моки). Протокол и периодичность — `docs/TESTING.md`.

**Тесты через admin-панель (Даша):**
Раздел `/dasha/bot_tests` — кнопки «▶ Тесты v2» и «▶▶ Все тесты», таблица ✅/❌, history."""
content = content.replace(old3, new3)

path.write_text(content, encoding="utf-8")
print("OK")
