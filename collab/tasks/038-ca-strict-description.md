# Задача 038: CA v1.3 — strict description = source_quote (no causal confabulation)

**Статус:** `outline` (полный spec после v57 verify)
**Номер:** 038
**Автор:** Опус
**Дата создания:** 2026-05-17
**Тип:** `промпт` (CA) + `cco-скрипт` (валидация)
**Batch:** 2 (гибрид, после Batch 1 v57)
**Связано:** [architecture-stocktake-2026-05-17.md](../context/architecture-stocktake-2026-05-17.md) Класс 1 «CA confabulation in description»

---

## Контекст (кратко)

В v56 CA event_auto_009 (огурцы) `description`:
> «Это произошло потому, что Валентина критиковала Владимира за то, что он не привозит достаточно подарков из Молдавии.»

`source_quote` того же event:
> «Однажды папаша привез чемодан огурцов в заграничном чемодане... Я выкинула, это потому что испортились.»

CA сам **выдумал** причинную связку «потому что не привозит подарков» — её нет в source_quote. GW v2.18 добросовестно переписал. Результат: в книге причина выкидывания огурцов искажена.

Аналогично — event_auto_008 (шуба→пианино) `description: 1990`, source_quote без даты, реальный год по семейному контексту 1962.

Это **Класс 1 stocktake** — CA пишет в `description` интерпретации/гипотезы которых нет в source. Универсальная проблема для всех subjects.

---

## Definition of Done

- ✅ Промпт CA v1.3: правило «description = парафраз source_quote без новых causal connectors, без новых дат, без новых атрибуций, которых нет в source».
- ✅ Скрипт post-CA `validate_description_drift(audit)`:
  - Word overlap `description` ⊂ `source_quote` ≥ X% (калибровать на v56: огурцы FAIL, легит описания PASS)
  - Запрет фраз «потому что», «это произошло так как», «из-за этого» в `description` если их нет в `source_quote`
  - Запрет новых years/dates в `description` которых нет в `source_quote`
  - Запрет имён персон в `description` которых нет в `source_quote` (или fact_map.persons[].name)
- ✅ Tests + integration на v56 артефактах: огурцы description должен FAIL валидацию, прочие — PASS
- ✅ После v57 — pinpoint events с `description_drift: true` в audit report

---

## Что финализировать после v57

- Калибровка threshold word-overlap (наблюдение на v57 для отрицательных и положительных кейсов).
- Решение: при `description_drift=true` — что делать? (a) GW игнорирует событие, (b) GW использует только source_quote, (c) CA перезапускается с дополнительной строгостью. Решение, скорее всего, (b) — на стороне Stage 2 input.

---

## История статусов

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-17 | `outline` | Опус |
