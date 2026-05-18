# Задача 051: Temporal place naming (Класс 15 — новый)

**Статус:** `new`
**Номер:** 051
**Автор:** Опус (роль архитектор+продакт)
**Дата создания:** 2026-05-17
**Тип:** конфиг + `cco-скрипт`
**Batch:** v60 sprint
**Связано:** stocktake 2026-05-17 — **новый Класс 15**; Никитин feedback v59 «Тверь в 50-е годы должна называться Калинин»

---

## Контекст

**Класс 15 — Temporal place naming** (universal):

В v59 нарративе:
- «В **1950-е годы** семья жила в **Калинине** в коммунальной квартире» ✅ correct (Калинин было до 1990)
- «В **1956 году** в **Твери** родилась дочь Татьяна» ❌ incorrect (в 1956 город назывался Калинин, не Тверь — переименован в 1990)
- В паспортичке «**Дочь:** Татьяна (родилась в **1956 году в Твери**)» ❌ Тверь не существовала как имя в 1956

Многие советские города переименовали в 1990-91:
- Калинин → Тверь (1990)
- Ленинград → Санкт-Петербург (1991)
- Свердловск → Екатеринбург (1991)
- Куйбышев → Самара (1991)
- Горький → Нижний Новгород (1990)
- Брежнев → Набережные Челны (1988)
- Андропов → Рыбинск (1989)
- Орджоникидзе → Владикавказ (1990)

**Универсально для биографий советских людей.**

## Universality check

- [x] Промпт — categorical (не упоминает Калинин/Тверь конкретно)
- [x] Subject-specific — temporal_place_names в gazeteer per subject (для Каракулины список городов где она жила/упомянуты)
- [x] Алгоритм generic — для любого subject с советским/постсоветским periodом
- [x] Subject-replacement test — для Корольковой Куйбышев/Самара переключение работает идентично ✅

---

## Спек

### Что нужно изменить / создать

**1. Расширить `gazeteer_<subject>.json` новым полем `temporal_place_names`:**

```json
{
  "subject_id": "karakulina",
  "topo_corrections": { ... },  // existing task 040
  "topo_types": { ... },         // existing
  "temporal_place_names": [
    {
      "canonical_modern": "Тверь",
      "historical_alternates": [
        {"name": "Калинин", "period_start": 1931, "period_end": 1990}
      ]
    },
    {
      "canonical_modern": "Санкт-Петербург",
      "historical_alternates": [
        {"name": "Ленинград", "period_start": 1924, "period_end": 1991},
        {"name": "Петроград", "period_start": 1914, "period_end": 1924}
      ]
    }
    // ... другие per subject
  ]
}
```

**2. Функция `validate_temporal_place_naming(book, fact_map, gazeteer) -> report`** в `pipeline_utils.py`:

Алгоритм:
1. Для каждого `paragraph` в book chapters:
   - Извлечь years (regex `\b(19|20)\d{2}\b`) и year ranges
   - Извлечь place names (из `gazeteer.temporal_place_names[].canonical_modern` + `.historical_alternates[].name`)
   - Для каждой пары (year, place):
     - Если place = canonical_modern, но year в period_start..period_end → **flag** `should_use_historical_name`
     - Если place = historical_alternate, но year > period_end → flag `should_use_canonical`
     - Если place = historical_alternate и year в period → PASS

2. Возвращает issues с suggestions:
   ```json
   {
     "type": "should_use_historical_name",
     "current_name": "Тверь",
     "should_be": "Калинин",
     "year_context": "1956",
     "snippet": "В 1956 году в Твери родилась дочь Татьяна",
     "severity": "warning"
   }
   ```

**3. Функция `enforce_temporal_place_naming(book, gazeteer) -> book`**:

Опциональный auto-fix для **safe** случаев:
- В narrative ch_02 (биография) — auto-rewrite только если year явно в pre-rename period
- В паспортичке (ch_01) — auto-rewrite (формальная зона, точность важна)
- В epilogue — НЕ auto-rewrite (часто общий контекст)
- В исторических notes (`***...***`) — НЕ trigger (current name OK)

**4. Минорный промпт-патч GW v2.20 ПРАВИЛО 9 (universal):**

```
### ПРАВИЛО 9 — TEMPORAL PLACE NAMING (universal)

В fact_map.temporal_place_names указаны исторические имена городов с периодами.
Когда нарративно описываешь событие в году N с городом C:
- Используй **исторически корректное** имя C для года N
- Например: если событие 1956 года произошло в городе который позже переименовали — используй имя 1956 года, не современное
- При этом современное имя — допустимо в скобках для clarity: «в Калинине (ныне Тверь)»
```

**5. Интеграция в Stage 3 runner**:
- После `normalize_book_topo` (task 040) — `enforce_temporal_place_naming` (auto-fix safe cases)
- После — `validate_temporal_place_naming` (check remaining)

### Какой результат ожидается

В v60:
- Паспортичка: «Татьяна (родилась в 1956 году в Калинине)»
- Нарратив ch_02 1950-е: «В 1956 году в Калинине родилась дочь Татьяна»
- Нарратив ch_02 события 1996+: «переехала с детьми в центр Твери» (correct, post-1990)
- Epilogue: «советская медсестра в Калинине» (correct, period reference)

### Как проверить

1. **Unit-тесты** `tests/test_temporal_place_naming.py`:
   - «1956 + Тверь» → flag (период 1931-1990 = Калинин)
   - «1990 + Тверь» → PASS (boundary case)
   - «1995 + Калинин» → flag (нужно Тверь)
   - «1985 + Ленинград» → PASS
   - «2000 + Ленинград» → flag (нужно СПб)

2. **Integration** на v59 text:
   - Найти все «Тверь» в контексте 1956, 1962, 1970 → flag
   - Auto-fix в паспортичке Татьяны: «в Твери» → «в Калинине»

3. **Verified-on-run** v60:
   - grep по «Твер» в контексте «195[0-9]\|196[0-9]\|197[0-9]\|198[0-9]» → minimal hits
   - paspart Татьяны имеет «Калинин», не «Тверь»

---

## Ограничения

- [ ] Generic algorithm; данные per subject в gazeteer
- [ ] Boundary cases (год переименования) — allow both forms
- [ ] Promочный промпт-патч — без subject-specific примеров (placeholders)
- [ ] Idempotent
- [ ] Universal

---

## Dev Review

**Статус:** ожидает
**[TECH]** — год переименования (1990 для Калинина) — допускаем оба варианта в граничный год; конфигурируется в gazeteer
**[PRODUCT]** — нет (Никита подтвердил необходимость)
**Сложность:** `s` (1-3 ч)
**Риск:** `low`

---

## История

| Дата | Статус | Кто |
|---|---|---|
| 2026-05-17 | `new` | Опус |
