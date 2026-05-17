# Задача 045b: Timeline anchors — парсить markdown ch_01.content (JSON array часто пуст)

**Статус:** `new`
**Номер:** 045b
**Автор:** Опус (роль архитектор+продакт)
**Дата создания:** 2026-05-17
**Тип:** `cco-скрипт`
**Batch:** 2-fix
**Связано:** task 045 (timeline anchors validate/enforce); diagnostic v58: `bio_data.timeline` JSON array = 0 entries, но в text 7 разделённых периодов

---

## Контекст

v58 `bio_data.timeline` array в JSON **пуст** (0 entries). Но в `ch_01.content` (markdown) есть **7 разделённых периодов** ✅:
- 1920–1933. Детство и сиротство
- 1938–1940. Медицинское образование
- 1941–1945. Военная служба
- 1946–1962. Семья и переезды
- 1962–1994. Работа и зрелость
- 1978–1996. Вдовство
- 2005. Последние годы

Скрипт task 045 `validate_timeline_anchors` смотрит **только в JSON array** → 0/7 found → false negative.

**Корень:** GW v2.19 пишет timeline как markdown в `content`, а не в structured `timeline[]` array. Скрипт нужно расширить — парсить markdown.

---

## Спек

### Что нужно изменить

**1. `validate_timeline_anchors` расширить:**

```python
def validate_timeline_anchors(book, anchors_config) -> dict:
    # 1. Попробовать JSON array bio_data.timeline (как раньше)
    # 2. Если пуст или меньше min_periods — fallback на парсинг ch_01.content
    # 3. Markdown парсинг: regex r"\*\*(\d{4}(?:–\d{4})?)\.?\s+([^*]+)\*\*"  
    #    извлекает блоки **YYYY-YYYY. Title**
    # 4. Для каждого извлечённого periodа — match по title_keywords из anchors_config
```

**2. `enforce_timeline_anchors`** — аналогично fallback на markdown:
- Если merges (склейка периодов) обнаружены в markdown → auto-split markdown (regex replace)
- Если отсутствуют anchors → flag, не auto-create

**3. Bonus (необязательно сейчас, но обсудить):**
- GW v2.20 промпт-патч: ОБЯЗАТЕЛЬНО заполнять `bio_data.timeline[]` array **параллельно** с markdown content (single source of truth). Это backlog, не блокер сейчас.

### Какой результат ожидается

В v59 `<run>_timeline_anchors.json`:
- `anchors_found.length`: 7 (или ≥6 если 1 anchor merged but split ОК)
- `anchors_missing.length`: 0
- `merges.length`: 0 (если v59 не склеит периоды)
- `total_periods_found`: 7
- `period_count_ok`: true

### Как проверить

1. **Unit-тесты** `tests/test_timeline_anchors_markdown.py`:
   - Markdown с 7 периодами в `**YYYY.Title**` формате → 7 found
   - Markdown с склейкой «1938-1945. Учёба и война» → merge detected, auto-split
   - JSON array содержит периоды → используется JSON
   - JSON array пуст, markdown пуст → 0 found, anchors_missing all 7

2. **Integration** на v58 v58c book_FINAL_stage3:
   - Прогнать `validate_timeline_anchors` → должно быть 7/7 found (markdown parsing работает)

3. **Verified-on-run** v59:
   - Открыть `<run>_timeline_anchors.json` → 7/7 found, merges=0

---

## Ограничения

- [ ] НЕ менять промпт GW (markdown→JSON sync — backlog)
- [ ] Anchors config per subject (как уже было)
- [ ] Idempotent

---

## Dev Review

**Статус:** ожидает

**[TECH]** — пред-резолв: regex на markdown bold patterns достаточно надёжен для типовых форматов; если subject имеет другой стиль — anchors_config расширяется per subject.

**[PRODUCT]** — нет.

**Сложность:** `s` (1-3 ч)
**Риск:** `low`

---

## История

| Дата | Статус | Кто |
|---|---|---|
| 2026-05-17 | `new` | Опус |
