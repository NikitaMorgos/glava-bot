# Задача 049g: LE preserve writing_notes — поле теряется при Stage 3 post-process

**Статус:** `new`
**Номер:** 049g
**Автор:** Опус
**Дата создания:** 2026-05-19
**Тип:** `cco-скрипт` (Stage 3 flow fix)
**Sprint:** v65 (bugfix v64)
**Связано:** task 049e v64 (GW ПРАВИЛО 13 + writing_notes proof); v64 verify revealed bug

---

## Контекст

В v64 GW v2.23 при revision pass **записал** `writing_notes.revision_applied: "..."` в `book_REVISED_*.json`. Но в `book_FINAL_stage3_*.json` (после LE + post-processing) — **`writing_notes = {}`** (пусто).

Это **bug в Stage 3 flow** — LE либо `preserve_chapter_structural_fields`, либо какой-то другой post-processing скрипт **удаляет/перезаписывает** поле `writing_notes` на пустое.

**Эффект:** `revision_diff_audit.json` ищет `writing_notes.rule13_revision_applied` (per ПРАВИЛО 13 spec), не находит → отчитывает `applied=[]`, `skipped=[{reason: "not_in_writing_notes"}]`. Хотя revision реально произошёл (paragraph p_02_011 переписан).

Это **scriptовый bug**, не GW bug. GW делает правильно, дальнейший pipeline poteрял.

---

## Pre-sprint checklist

- [x] Stocktake актуален
- [x] Critical reading артефактов — открыты v64 book_REVISED + book_FINAL_stage3 + revision_diff_audit
- [x] Universality — n/a (scripted)
- [x] Защита подключена к лечению — да, fix flow
- [x] Прогон раздельный — bugfix
- [x] Класс багов — «структурное поле теряется в post-process» (generic)
- [x] Скрипт-first — да

---

## Спек

### 1. Diagnostic — где теряется writing_notes

Нужно проследить поток book_REVISED → ... → book_FINAL_stage3:

```
Stage 2 revision pass → book_REVISED.json (writing_notes есть ✅)
   ↓
LE processing (Stage 3 input) → book_after_LE.json (writing_notes?)
   ↓
preserve_chapter_structural_fields(book_after_LE, book_REVISED)
   ↓
другие post-process (gazeteer, persona_notes, relation_overrides, bio_data_format, ...)
   ↓
book_FINAL_stage3.json (writing_notes = {}) ❌
```

**Гипотеза 1:** LE prompt просит вернуть полный book со всеми полями, но игнорирует `writing_notes` (не описано в LE output schema). LE возвращает `book` без `writing_notes` → шаг loss.

**Гипотеза 2:** `preserve_chapter_structural_fields` восстанавливает только chapters.bio_data, не root-level `writing_notes`. Если LE убрал — preserve не восстанавливает.

**Гипотеза 3:** один из post-process скриптов делает `book["writing_notes"] = {}` или dict copy без writing_notes.

### 2. Fix — независимо от гипотезы

Добавить **explicit preservation** root-level `writing_notes` через все Stage 3 шаги:

```python
def preserve_root_level_metadata(book_processed, book_pre_processing):
    """Восстановить root-level metadata fields если post-processing удалил.

    Fields to preserve (root level book):
    - writing_notes (GW proof of attention)
    - facts_used (если есть)
    - revision_log (history)
    - любые другие root-level non-chapter metadata
    """
    metadata_fields = ["writing_notes", "facts_used", "revision_log", "metadata"]
    for field in metadata_fields:
        if field in book_pre_processing and (
            field not in book_processed
            or not book_processed[field]
            or book_processed[field] == {}
        ):
            book_processed[field] = book_pre_processing[field]
            print(f"[preserve_root_level_metadata] Restored '{field}' from pre-LE snapshot")
    return book_processed
```

Применить **в Stage 3 runner** (`scripts/test_stage3.py`):
- Сохранить snapshot book pre-LE (`book_REVISED.json` или эквивалент)
- После всех post-process (gazeteer, persona_notes, etc.) — вызвать `preserve_root_level_metadata(book_final, book_pre_le)`

### 3. (Опционально) LE prompt hint

Если diagnostic выявит что LE prompt активно «забывает» writing_notes — добавить в LE prompt одну строку (минимум, не правило):

> «Output schema: book содержит все поля input book — chapters, callouts, historical_notes, **writing_notes** (если есть), facts_used. Не удалять, не очищать.»

**Не добавлять как новое правило LE** — это просто preservation note. LE и так должен сохранять структуру, это уточнение.

Если же scripted preservation (выше) достаточен — LE prompt **не трогаем** (per принцип скрипт-first).

### 4. Тесты

`tests/test_preserve_writing_notes.py`:
- Test: book pre-LE имеет `writing_notes={"rule13_revision_applied":[...]}`. book post-LE имеет `writing_notes={}`. После `preserve_root_level_metadata` — `writing_notes` восстановлен.
- Test: book pre-LE имеет `writing_notes={"x":1}`. book post-LE имеет `writing_notes={"y":2}`. После preserve — оставляем post-LE (не перезаписываем непустое).
- Test: ничего не теряется в chapters, callouts, historical_notes — preserve работает только с root metadata.

---

## Universality check

- [x] Промпт — n/a (либо optional LE hint, без subject-specific)
- [x] Subject-specific — n/a
- [x] Generic — preservation любых root metadata для любого subject
- [x] Subject-replacement test — работает без правок ✅

---

## Ограничения

- [ ] Только root-level metadata, не chapter content
- [ ] Idempotent
- [ ] Не перезаписывать непустые post-LE значения
- [ ] Лог восстановления для diagnostic
- [ ] LE prompt change — только если scripted preservation недостаточен (fallback)

---

## Dev Review

**Статус:** ожидает

**[TECH]** — pre-answer от Опуса:
- Diagnostic шаг (1 час) — где именно теряется. Возможно достаточно посмотреть Stage 3 runner shape логи
- Scripted preservation — primary defense
- LE prompt — fallback если diagnostic покажет LE как source
- Apply в `scripts/test_stage3.py` либо в `_v64_stage3_final.py` (нужно проверить актуальный runner)

**[PRODUCT]** — нет

**Сложность:** `xs` (<1 ч diagnostic + script fix + tests)
**Риск:** `low` (preserve only, не меняет существующую логику post-process)

---

## Verified-on-run v65

**Cursor:** [после v65]
**Опус:** независимо проверит `book_FINAL_stage3.json` — `writing_notes` непуст, содержит `rule13_revision_applied` либо аналог из GW v2.24 schema.

---

## История

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-19 | `new` | Опус |
