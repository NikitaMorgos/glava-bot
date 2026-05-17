# Задача 049b: GW v2.20 verify — manifest Stage 2 ghostwriter_version

**Статус:** `spec-approved`
**Номер:** 049b
**Автор:** Опус
**Дата создания:** 2026-05-17
**Тип:** `cco-скрипт`
**Batch:** v60 sprint (patch to 049)

---

## Контекст

GW v2.20 введён в Batch 2-fix. `pipeline_config.json` уже содержит `"prompt_file": "03_ghostwriter_v2.20.md"`. Однако manifest Stage 2 не содержит явного поля `ghostwriter_version` для быстрой проверки.

В v59 нужно верифицировать что manifest Stage 2 явно показывает `ghostwriter_version: v2.20` — без него ПРАВИЛА 6-8 (discourse markers, subject_age, min depth) неизвестно активированы ли.

## Universality check

1. ✅ Изменение generic — извлекает версию из prompt_file имени
2. ✅ Subject-independent
3. ✅ Алгоритм: regex из prompt_file name
4. ✅ Subject-replacement test ✅

---

## Спек

**В `scripts/test_stage2_pipeline.py`**, в вызове `save_run_manifest`, добавить в `notes`:

```python
notes={
    ...,
    "ghostwriter_version": _extract_prompt_version(cfg.get("ghostwriter", {}).get("prompt_file", "")),
    "completeness_auditor_version": _extract_prompt_version(cfg.get("completeness_auditor", {}).get("prompt_file", "")),
}
```

**Вспомогательная функция** (можно в test_stage2_pipeline.py или в pipeline_utils.py):

```python
def _extract_prompt_version(prompt_file: str) -> str:
    """Извлекает версию из имени файла промпта: '03_ghostwriter_v2.20.md' → 'v2.20'"""
    import re
    m = re.search(r'(v\d+\.\d+)', prompt_file or "")
    return m.group(1) if m else prompt_file
```

---

## Verified-on-run критерий

«manifest Stage 2 показывает ghostwriter_version: v2.20»

Конкретно: открыть `karakulina_stage2_run_manifest_*.json` → поле `notes.ghostwriter_version` == «v2.20».

---

## Dev Review

**[TECH]** — нет флагов.
**[PRODUCT]** — нет.
**Сложность:** `xs`
**Риск:** `low`

---

## История

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-17 | `spec-approved` | Опус |
