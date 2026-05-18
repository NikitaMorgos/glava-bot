# Задача 044d-2: Render bug — остаточный дубль перед «Личные данные» и malformed override-строки

**Статус:** `new`
**Номер:** 044d-2
**Автор:** Опус (роль архитектор+продакт)
**Дата создания:** 2026-05-18
**Тип:** `cco-скрипт`
**Sprint:** v63
**Связано:** task 044d (Render bug `?: ?` initial); v62a verified: 044d PASS по check (`?: ?` ушло), но Никитин live review v62a поднял остаточный дубль «много текста перед Личные данные» + malformed override entry для Нинваны

---

## Контекст

В v62a `karakulina_v62_text_FULL_final.md` task 044d **формально** PASS (no `?: ?`), но Никитин live review показал две остаточные проблемы:

### 1. Дубль перед «### Личные данные»

```markdown
### Дополнительный текст ch_01

### Личные данные

**Полное имя:** Каракулина Валентина Ивановна (девичья фамилия Рудая)
```

Между Семьёй и Личными данными вставлен empty `### Дополнительный текст ch_01` заголовок. Это **остаток** старой логики, когда build_gate1 рендерил `ch_01.content` markdown под этим заголовком — но теперь structured paspart, дубль не нужен.

### 2. Malformed override-entry для Нинваны

```markdown
- **Подруга"** — "знакомая\  _(врач, авторитет [from pin-list required_persons])_
```

Эта строка — render override entry для Нинваны Полсачевой, где label/value прорываются через json escape. Должно быть **skip полностью** (Нинвана `in_bio_data_family: false`), но render всё равно пишет malformed строку.

**Корень обеих проблем:** `build_gate1_full_text.py` render logic недостаточно строг — оставляет remnant headers и не filterует override entries 100%.

---

## Universality check

- [x] Промпт — n/a
- [x] Subject-specific — n/a (логика render generic)
- [x] Алгоритм generic — для любого subject: skip if `in_bio_data_family == false` или value empty/null/special chars
- [x] Subject-replacement test — для Корольковой/Дмитриева override entries в pin-list тоже могут быть; алгоритм работает без правок ✅

---

## Спек

### Что нужно изменить

**`scripts/build_gate1_full_text.py`** — два узких fix:

### 1. Удалить empty `### Дополнительный текст ch_01` heading

После рендера структурированной паспортички (`bio_data.family / awards / timeline / etc.`), если `ch_01.content` пуст или содержит только декоративные пустые heading — **не рендерить** дополнительный блок:

```python
def render_ch01_additional_content(book, paspart_rendered: bool) -> str:
    """Render ch_01.content only if there's actual non-paspart content.

    If paspart was already rendered via structured fields,
    and ch_01.content is empty/whitespace/only-headings → skip block entirely.
    """
    content = book.chapters.ch_01.content or ""
    # Remove markdown headings to check if there's actual text
    text_only = re.sub(r'^#+\s+.*$', '', content, flags=re.MULTILINE).strip()
    if paspart_rendered and not text_only:
        return ""
    return f"\n### Дополнительный текст ch_01\n\n{content}\n"
```

### 2. Strict skip для override entries

Усилить filter в render loop bio_data.family:

```python
def should_skip_family_entry(entry: dict) -> bool:
    """Skip entry if it's an override marker or malformed."""
    if entry.get("in_bio_data_family") is False:
        return True
    if entry.get("label") in (None, "", "?"):
        return True
    if entry.get("value") in (None, "", "?"):
        return True
    # Detect malformed escape artifacts
    label = entry.get("label", "")
    value = entry.get("value", "")
    if '\\' in label or '\\' in value:  # unescaped JSON in render
        return True
    if '"' in label or '"' in value:  # quotation marks leaked
        return True
    return False
```

Применить в `_render_family_section` before each entry.

### 3. (Опционально) `from pin-list required_persons` cleanup

Если note содержит `[from pin-list required_persons]` (artifact от task 044b) — strip эту suffix перед render (это internal metadata, не для пользователя):

```python
def clean_note_for_render(note: str) -> str:
    return re.sub(r'\s*\[from pin-list required_persons\]\s*', '', note).strip()
```

### Какой результат ожидается

В v63 text_FULL.md:
- ✅ После `#### Семья` блока сразу идёт `### Личные данные` (без `### Дополнительный текст ch_01` empty header)
- ✅ Нинвана Полсачева **отсутствует** в bio_data.family render (override skipped)
- ✅ Notes без `[from pin-list required_persons]` artifact

### Как проверить

1. **Unit-тесты** `tests/test_build_gate1_render.py` (extend):
   - `should_skip_family_entry({"in_bio_data_family": False})` → True
   - `should_skip_family_entry({"label": "Подруга\"", "value": "знакомая\\"})` → True (malformed)
   - `should_skip_family_entry({"label": "Мать", "value": "Полина"})` → False
   - `render_ch01_additional_content` with empty content + paspart rendered → returns empty string
   - `clean_note_for_render` removes `[from pin-list required_persons]`

2. **Integration** на v62a:
   - Загрузить v62a `book_FINAL_stage3` + Нинвана override + Polly note with `[from pin-list...]`
   - Прогнать `build_gate1_full_text` → output **без** Нинваны line, **без** dup heading, notes clean

3. **Verified-on-run** v63:
   - Открыть `karakulina_v63_text_FULL_final.md` — между `#### Семья` и `### Личные данные` **нет** empty headers
   - В family section **нет** строк типа `**Подруга"** — "знакомая\`
   - Notes без `[from pin-list ...]` suffix

---

## Ограничения

- [ ] **Не менять** структуру `book_FINAL_stage3.json` — только render
- [ ] **Idempotent** — повторный render не меняет output
- [ ] **Generic algorithm** — skip rules применимы к любому subject
- [ ] **Не enforce-удаление persons из fact_map** — только filter render layer

---

## Dev Review

**Статус:** ожидает

**[TECH]** — pre-answer от Опуса:
- `from pin-list required_persons` artifact: проверить откуда appendится (task 044b force-add) и либо чистить там, либо в render — render проще
- Empty `### Дополнительный текст ch_01` heading — возможно appendится в `ch_01.content` LE/GW, см. `preserve_chapter_structural_fields`; safe чистить на render layer
- Malformed quote detection (`\\` или `"`) — heuristic, может дать false positive если note legitimately содержит quote; альтернатива — explicit whitelist field check

**[PRODUCT]** — нет

**Сложность:** `xs` (<1 ч)
**Риск:** `low` (render-only)

---

## Verified-on-run

**Cursor:** [после v63]
**Опус:** независимо проверит — между Семья и Личными данными нет дубль-заголовков; Нинвана не рендерится

---

## История

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-18 | `new` | Опус |
