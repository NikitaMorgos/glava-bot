# Prompt Release Ritual

Ритуал для стабильных итераций с Дашей:

1. **Один релиз = один change-set**
   - Меняем только один prompt `prompts/*.md` за итерацию.
   - Обязательно обновляем `prompts/pipeline_config.json`.

2. **Перед approve обязательно**
   - Прогоняем:
     - `python scripts/check_prompt_release.py`
     - `python scripts/run_regression_suite.py --project karakulina --stage <stage>`
   - Если любой из них fail — checkpoint не approve.

3. **Протокол итерации**
   - Изменить 1 агента.
   - Прогнать regression suite.
   - Сравнить diff-артефакты (`run_manifest`, `*_text_gates_*.json`, `*_qa_*.json`).
   - Только после этого approve.

4. **Аварийный обход (временный)**
   - Допустим только осознанно: `checkpoint_save.py approve ... --skip-regression`.
   - Причина обхода фиксируется в задаче/логах.
