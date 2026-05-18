# Задача 052d: Contributors раздел — упростить до «ФИО + родство», убрать роли интервью

**Статус:** `new`
**Номер:** 052d
**Автор:** Опус (роль архитектор+продакт)
**Дата создания:** 2026-05-18
**Тип:** `cco-скрипт` + pin-list edit
**Sprint:** v63
**Связано:** task 052 / 052c (Contributors section, Class 16); Никитин v62a feedback (impl) — убрать «основной рассказчик / со-интервьюер / участник интервью», только ФИО+родство

---

## Контекст

В v62a `karakulina_v62_text_FULL_final.md` финальный раздел:

```markdown
---

## Кто работал над этой Главой

- **Каракулина-Маргось-Кужба Татьяна Дмитриевна** — дочь, основной рассказчик
- **Маргось Никита Владимирович** — внук, со-интервьюер
- **Маргось Даша Владимировна** — внучка, участник интервью
- **Кужба Олег [отчество требует уточнения]** — второй муж дочери (отчим внуков), дал реплики
```

Никитин feedback: **упростить до ФИО + родство**, без указания роли в интервью:

```markdown
## Кто работал над этой Главой

- **Каракулина-Маргось-Кужба Татьяна Дмитриевна** — дочь
- **Маргось Никита Владимирович** — внук
- **Маргось Даша Владимировна** — внучка
- **Кужба Олег [отчество требует уточнения]** — второй муж дочери
```

Аргументация Никиты: раздел сообщает **кто работал** над книгой; продакт-решение — не детализировать роли (рассказчик/интервьюер/реплики). Все contributors — соавторы биографии, иерархия ролей лишняя.

**Класс:** узкий конкретный fix (render-only), также **продактовое упрощение** Contributors раздела.

---

## Universality check

- [x] Промпт — n/a (post-process render)
- [x] Subject-specific — n/a (формат generic; список contributors per subject в pin-list)
- [x] Алгоритм generic — render только `full_name + relation_to_subject` поля; `interview_role` + `notes` исключаются
- [x] Subject-replacement test — для Корольковой Contributors раздел через pin-list читается тот же шаблон ✅

---

## Спек

### Что нужно изменить

### 1. Render functions

В `scripts/build_gate1_full_text.py` — `append_contributors_section`:

```python
def append_contributors_section(text: str, contributors: list[dict]) -> str:
    """Append Contributors section using ONLY full_name + relation_to_subject.

    Each contributor record may have additional fields (interview_role, notes,
    transcript_appearance), but these are NOT rendered — render uses ONLY:
    - full_name: canonical name
    - relation_to_subject: kinship to the book's subject

    Если contributors пуст или None — return text unchanged.
    """
    if not contributors:
        return text
    lines = ["", "---", "", "## Кто работал над этой Главой", ""]
    for c in contributors:
        full_name = c.get("full_name", "").strip()
        relation = c.get("relation_to_subject", "").strip()
        if not full_name or not relation:
            continue
        lines.append(f"- **{full_name}** — {relation}")
    return text.rstrip() + "\n" + "\n".join(lines) + "\n"
```

### 2. Pin-list parser — keep all fields but render only 2

`parse_pin_list_from_markdown` уже парсит Contributors таблицу со всеми 5 полями (`contributor_id, full_name, relation_to_subject, interview_role, notes`). НЕ менять parser — оставить структуру для возможного future use (например, в Никитин справочный анализ TR coverage). Render layer **выбирает** только `full_name + relation_to_subject`.

### 3. (Опционально) pin-list edit

`known_episodes_karakulina.md` v5 — Contributors section без изменений (поля parser продолжают читаться). Опционально можно добавить hint в шапке секции:

```markdown
## Contributors

> Render в финальной книге использует только ФИО + relation_to_subject.
> Поля interview_role и notes — для внутренней атрибуции (кто что говорил
> в TR1/TR2 при сверке), в книгу не попадают.
```

### Какой результат ожидается

В v63 `karakulina_v63_text_FULL.md` финал:

```markdown
---

## Кто работал над этой Главой

- **Каракулина-Маргось-Кужба Татьяна Дмитриевна** — дочь
- **Маргось Никита Владимирович** — внук
- **Маргось Даша Владимировна** — внучка
- **Кужба Олег [отчество требует уточнения]** — второй муж дочери
```

Без «основной рассказчик», «со-интервьюер», «участник интервью», «дал реплики».

### Как проверить

1. **Unit-тесты** `tests/test_contributors_render.py`:
   - 1 contributor с full_name + relation_to_subject + interview_role → render shows только name + relation
   - Contributors=[] → return text без изменений (no section appended)
   - Contributor без full_name или relation → skip (no malformed entry)
   - Idempotent

2. **Integration** на v62a artifacts:
   - Загрузить pin-list Contributors → render → проверить отсутствие «рассказчик/интервьюер/реплики»

3. **Verified-on-run** v63:
   - Открыть `karakulina_v63_text_FULL.md` last section — 4 строки, каждая `**ФИО** — родство`, без role suffix

---

## Ограничения

- [ ] **Render-only** — pin-list parser не меняется (interview_role/notes остаются в data)
- [ ] **Idempotent** render
- [ ] **Generic** для любого subject
- [ ] **Skip malformed entries** (без full_name или relation)

---

## Dev Review

**Статус:** ожидает

**[TECH]** — pre-answer от Опуса:
- Сохранение всех полей в data + selective render — гибкость для будущих use cases
- Edge case: если relation_to_subject содержит запятую («дочь, основной рассказчик»), parser должен правильно разрезать таблицу markdown по `|` (already supported)

**[PRODUCT]** — нет (Никитино продактовое решение — render simplified)

**Сложность:** `xs` (<1 ч)
**Риск:** `low`

---

## Verified-on-run

**Cursor:** [после v63]
**Опус:** независимо проверит финальные строки text_FULL.md

---

## История

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-18 | `new` | Опус |
