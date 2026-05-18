# Задача 052: Contributors section (Класс 16 — новое продуктовое нововведение)

**Статус:** `new`
**Номер:** 052
**Автор:** Опус (роль архитектор+продакт)
**Дата создания:** 2026-05-17
**Тип:** конфиг + `cco-скрипт` + минор `промпт` GW
**Batch:** v60 sprint
**Связано:** stocktake 2026-05-17 — **новый Класс 16** (contributors section); Никитин продуктовый запрос v59

---

## Контекст

**Никитино продуктовое нововведение:** в конце каждой книги-биографии — служебный раздел **«Кто работал над этой Главой»** со списком людей, чьи воспоминания/реплики попали в книгу.

Для Каракулиной (из intervieuw transcripts):
- **Татьяна Каракулина (Маргось-Кужба)** — дочь, основной рассказчик
- **Никита Маргось** — внук, со-интервьюер
- **Даша Маргось** — внучка (если её реплики были)
- **Олег Кужба** — второй муж Татьяны (Никита подтвердил «его реплики тоже были»)

Универсально для всех биографий — каждая книга имеет contributors (родственники/друзья субъекта, чьи воспоминания записаны).

## Universality check

- [x] Промпт — universal с placeholder `[contributors]`
- [x] Subject-specific — список contributors в pin-list per subject (`known_episodes_<subject>.md` раздел Contributors)
- [x] Алгоритм generic — построение section из pin-list config
- [x] Subject-replacement test — для Корольковой свой список contributors, тот же mechanism ✅

---

## Спек

### Что нужно изменить / создать

**1. Расширить `known_episodes_<subject>.md`** — новый раздел `Contributors`:

```markdown
## Contributors (для служебного раздела книги)

| contributor_id | full_name | relation_to_subject | intervieuw_role | notes |
|---|---|---|---|---|
| c_001 | Каракулина-Маргось-Кужба Татьяна Дмитриевна | дочь | основной рассказчик | TR1 + TR2 |
| c_002 | Маргось Никита Владимирович | внук | со-интервьюер | TR2 |
| c_003 | Маргось Даша Владимировна | внучка | со-интервьюер | TR2 (если реплики были) |
| c_004 | Кужба Олег [отчество] | второй муж дочери (отчим внуков) | дал реплики | TR2 |
```

Парсер pin-list (existing `parse_pin_list_from_markdown`) — добавляет `contributors` секцию в output.

**2. Функция `add_contributors_section(book, contributors_config) -> book`** в `pipeline_utils.py`:

После всех validators в Stage 3:
- Создать в book новое поле `book.contributors_section` (или `book.appendix.contributors`)
- Содержит structured list:
  ```json
  {
    "title": "Кто работал над этой Главой",
    "intro_text": "В создании этой книги-биографии участвовали следующие люди:",
    "contributors": [
      {
        "full_name": "Каракулина-Маргось-Кужба Татьяна Дмитриевна",
        "relation": "дочь",
        "role": "основной рассказчик"
      },
      ...
    ]
  }
  ```

**3. `build_gate1_full_text.py`** — render этого раздела в конце text_FULL.md:

```markdown
---

## Кто работал над этой Главой

В создании этой книги-биографии участвовали:

- **Каракулина-Маргось-Кужба Татьяна Дмитриевна** — дочь, основной рассказчик
- **Маргось Никита Владимирович** — внук, со-интервьюер
- **Маргось Даша Владимировна** — внучка
- **Кужба Олег [отчество]** — второй муж дочери

---
```

**4. Опциональный минорный GW промпт-патч ПРАВИЛО 10 (universal):**

```
### ПРАВИЛО 10 — CONTRIBUTORS SECTION (universal)

В fact_map.subject.contributors указаны люди, со слов которых записаны воспоминания (interview rapporteurs).

GW в Stage 2 НЕ генерирует contributors section — это **автоматически добавляется в Stage 3** из fact_map.subject.contributors.

GW обязан в нарративе **сохранять** упоминания каждого contributor хотя бы 1-2 раза (через discourse markers per ПРАВИЛО 6) — это создаёт ощущение что книга — collective memory семьи.
```

Этот промпт universal, через placeholder `[contributors]`.

**5. Интеграция в Stage 3 runner**:
- После всех validators + auto_rewrite:
- `add_contributors_section(book, contributors_from_pin_list)` — финальный шаг
- В text_FULL render — после epilogue

### Какой результат ожидается

В v60 `text_FULL.md` в конце:

```markdown
## Кто работал над этой Главой

В создании этой книги-биографии участвовали:

- **Каракулина-Маргось-Кужба Татьяна Дмитриевна** — дочь, основной рассказчик
- **Маргось Никита Владимирович** — внук, со-интервьюер
- **Маргось Даша Владимировна** — внучка
- **Кужба Олег [отчество]** — второй муж дочери

---
```

### Как проверить

1. **Unit-тесты** `tests/test_contributors_section.py`:
   - Pin-list содержит 4 contributors → section имеет 4 entries
   - Если pin-list пуст — section не добавляется (graceful)
   - Парсер markdown table → corrects structured output

2. **Integration** на v59 + pin-list v3 (с contributors):
   - Добавить раздел в book → text_FULL render имеет contributors section

3. **Verified-on-run** v60:
   - text_FULL.md в конце имеет раздел «Кто работал над этой Главой»
   - 4 contributors с full_name и relation

---

## Ограничения

- [ ] Generic — contributors per subject в pin-list config
- [ ] full_name — точное (родовое окончание зависит от пола); проверка корректности — manual review
- [ ] Idempotent
- [ ] Universal

---

## Dev Review

**Статус:** ожидает
**[TECH]** — full_name + отчества — требует ручного ввода в pin-list (нет в TR обычно)
**[PRODUCT]** — нет (Никита подтвердил состав: Татьяна/Никита/Даша/Кужба)
**Сложность:** `s` (1-3 ч)
**Риск:** `low` (read-only section, не trogает narrative)

---

## История

| Дата | Статус | Кто |
|---|---|---|
| 2026-05-17 | `new` | Опус |
