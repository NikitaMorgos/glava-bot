# Задача 048b: Chronology grandchildren — warning grandchild_before_inferred_birth

**Статус:** `spec-approved`
**Номер:** 048b
**Автор:** Опус
**Дата создания:** 2026-05-17
**Тип:** `cco-скрипт`
**Batch:** v60 sprint (extension of 048)

---

## Контекст

Task 048 ввёл `validate_chronological_consistency`. Однако он не проверяет **внуков** — у внуков в fact_map обычно нет `birth_year`. В v59 GW может упоминать «внучку Дашу» в контексте событий 1973 года (хотя её мать Татьяна родилась в 1956 и Даша физически не могла родиться раньше ~1975-1980).

**Новый тип предупреждения:** `grandchild_before_inferred_birth` — внук/внучка упоминается рядом с годом который предшествует вероятному году рождения.

**Логика вывода минимального года:**
- найти родителя (дочь/сын) внука/внучки из fact_map
- взять `birth_year` родителя
- добавить 15 лет → `min_grandchild_birth`
- если внук/внучка упоминается в абзаце с годом < min_grandchild_birth → WARNING

## Universality check

1. ✅ Generic алгоритм — работает для любого subject с fact_map.persons
2. ✅ Минимальный возраст 15 лет — biologically universal constant
3. ✅ Алгоритм не привязан к конкретным именам
4. ✅ Subject-replacement test ✅

---

## Спек

**В `pipeline_utils.py`, функция `validate_chronological_consistency`** — добавить блок:

```python
# Grandchild check — infer min birth year from parent
grandchild_persons = [p for p in fact_map.get("persons", [])
                      if "внук" in (p.get("relation_to_subject") or "").lower()
                      and not p.get("birth_year")]
for gc in grandchild_persons:
    gc_name = gc.get("name", "").lower()
    # find parent: child of subject whose birth year is known
    parent_birth = None
    for p in fact_map.get("persons", []):
        rel = (p.get("relation_to_subject") or "").lower()
        if ("сын" in rel or "дочь" in rel) and p.get("birth_year"):
            parent_birth = int(p["birth_year"])
            break  # использовать первого найденного child
    if parent_birth is None:
        continue
    min_gc_birth = parent_birth + 15
    # scan book for mentions near early years
    for ch in book.get("chapters", []):
        ...  # аналогично существующей логике
        if gc_name and gc_name in para_lower and para_years and min(para_years) < min_gc_birth:
            issues.append({
                "type": "grandchild_before_inferred_birth",
                "person_name": gc.get("name", ""),
                "inferred_min_birth": min_gc_birth,
                "event_year": min(para_years),
                "severity": "warning",
                "snippet": para[:200],
            })
```

---

## Verified-on-run критерий

«chronology_check содержит flag для «1973 + внучка Даша» (warning grandchild_before_inferred_birth)»

---

## Dev Review

**[TECH]** — нет флагов. Добавление нового блока в существующую функцию.
**[PRODUCT]** — нет.
**Сложность:** `s`
**Риск:** `low`

---

## История

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-17 | `spec-approved` | Опус |
