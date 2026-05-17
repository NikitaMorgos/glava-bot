# Задача 046b: Epilogue runner order fix — style_checks после rewrite

**Статус:** `spec-approved`
**Номер:** 046b
**Автор:** Опус (архитектор)
**Дата создания:** 2026-05-17
**Тип:** `cco-скрипт`
**Batch:** v60 sprint (patch to 046)

---

## Контекст

В v59 `style_checks.json` содержит ошибки для фраз из epilogue, которые были **удалены** `enforce_epilogue_stop_phrases` (task 046). Причина — порядок в Stage 3 runner:

1. Style checks (task 043) → флагирует стоп-фразы ✅ правильно
2. Epilogue rewrite (task 046) → удаляет стоп-фразы
3. Но style_checks уже сохранён с ошибками — они «дублируют» удалённые фразы

**Проблема:** verified-on-run смотрит на `style_checks.json` и видит ошибки для текста, которого уже нет в финальной книге.

## Universality check

1. ✅ Промпт не меняется — только порядок в runner
2. ✅ Generic для любого subject
3. ✅ Алгоритм: переставить вызовы
4. ✅ Subject-replacement test: для Корольковой работает без правок ✅

---

## Спек

**В `scripts/test_stage3.py` поменять порядок:**

**БЫЛО:**
```
# style_checks (task 043) ← строки ~815-838
# epilogue_rewrite (task 046) ← строки ~872-882
```

**СТАЛО:**
```
# epilogue_rewrite (task 046) ← ПЕРВЫМ
# style_checks (task 043) ← ПОСЛЕ rewrite — читает уже clean text
# narrative_stop_phrases (task 043b) ← ПОСЛЕ rewrite
```

После перестановки `style_checks.json` будет содержать только ошибки в **финальном тексте**, без артефактов удалённых предложений.

---

## Verified-on-run критерий

«style_checks.json errors соответствует cleaned text — нет ошибок на удалённых фразах»

Конкретно: открыть `style_checks.json` → посчитать epilogue_stop_phrases.errors → проверить что те же фразы отсутствуют в `book_FINAL_stage3.json` epilogue.

---

## Dev Review

**[TECH]** — нет флагов. Простая перестановка блоков.
**[PRODUCT]** — нет.
**Сложность:** `xs`
**Риск:** `low`

---

## История

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-17 | `spec-approved` | Опус |
