# Задача 044g: Bio_data.family format consistency — единый формат «Родство: Имя (note)»

**Статус:** `new`
**Номер:** 044g
**Автор:** Опус (роль архитектор+продакт)
**Дата создания:** 2026-05-18
**Тип:** `cco-скрипт`
**Sprint:** v63
**Связано:** task 044 / 044b / 044c / 044e / 044f (family hotfixes); Никитин v62a feedback #8 — формат непоследователен

---

## Контекст

В v62a `karakulina_v62_text_FULL_final.md` секция «Семья» (render):

```markdown
- **Отец** — Рудай Иван Андреевич, плотник
- **Мать** — Рудая Пелагея Алексеевна, работница колхоза  _(умерла в 1933 году)_
- **Брат** — младший брат  _(умер в детстве)_
- **Старшая сестра** — Полина  _(забрала из детдома, разные отцы с Валентиной)_
- **Бабушка** — Марфа  _(мать отца Валентины)_
- **Муж** — Каракулин Дмитрий, военный  _(умер в 1978 году)_
- **Сын** — Каракулин Валерий  _(родился в 1948 году в Вышнем Волочке)_
- **Дочь** — Татьяна Каракулина  _(родилась в 1956 году в Калинин; рассказчик интервью)_
...
- **Подруга"** — "знакомая\  _(врач, авторитет [from pin-list required_persons])_
```

Никитин feedback (#8): **формат непоследователен**:
- Некоторые записи: «Муж: Каракулин Дмитрий, военный (умер в 1978)» — relation: name+profession (note)
- Другие: «Бабушка Марфа: мать отца Валентины» — без `,` между name и note; note описательный
- Третьи: «Дочь: Татьяна Каракулина (родилась в 1956 году в Калинин)» — без склонения «Калинин»

Никитино желание — **единый формат**:
```
**Родство** — Имя_полное (note)
```

Где:
- **Родство** (label) — «Отец», «Мать», «Муж», «Бабушка», «Внук», «Племянник», и т.д.
- Имя_полное (value) — каноническое имя + (опционально) род занятий/профессия, единым полем
- (note) — дополнительная информация, выделена _курсивом_

**Класс:** Class 2 (bio_data volatility) — конкретно format normalization across entries.

---

## Universality check

- [x] Промпт — n/a (post-process)
- [x] Subject-specific — n/a (формат generic)
- [x] Алгоритм generic — применим к любому subject bio_data.family
- [x] Subject-replacement test — для Корольковой/Дмитриева формат «**Дочь** — Имя (note)» работает без правок ✅

---

## Спек

### Что нужно изменить

### 1. Канонический формат entries

В `pipeline_utils.py` — новая функция `normalize_bio_data_family_format`:

```python
def normalize_bio_data_family_format(bio_data: dict) -> dict:
    """Normalize each entry in bio_data.family to canonical format.

    Canonical schema (per entry):
    {
      "label": "Родство",       # capitalized, без двоеточия
      "value": "Имя Полное",     # canonical name (after Name Normalizer)
      "profession": "военный",   # optional, separate field (не в value)
      "note": "...",             # optional, descriptive context
      "death_year": 1978,         # optional, structured
      "birth_year": 1948,        # optional, structured
      "birth_place": "Калинин",  # optional
    }
    """
    for entry in bio_data.get("family", []):
        # 1. Strip trailing punctuation from label
        entry["label"] = entry["label"].strip().rstrip(":.,").capitalize()

        # 2. If value contains «, профессия» — split into value + profession
        m = re.match(r'^(?P<name>[^,]+),\s*(?P<prof>.+)$', entry.get("value", ""))
        if m and entry.get("profession") is None:
            entry["value"] = m.group("name").strip()
            entry["profession"] = m.group("prof").strip()

        # 3. Apply gazeteer to birth_place / location fields (case)
        # (uses existing normalize_topo logic)
    return bio_data
```

### 2. Render layer — единый template

В `scripts/build_gate1_full_text.py` — единый render template:

```python
def render_family_entry(entry: dict) -> str:
    """Render entry as: **Родство** — Имя_полное (note), case-correct."""
    label = entry.get("label", "").strip()
    value = entry.get("value", "").strip()
    profession = entry.get("profession", "").strip()
    note = entry.get("note", "").strip()

    # Assemble value: "Имя, профессия"
    value_full = value
    if profession:
        value_full = f"{value}, {profession}"

    # Assemble note from structured fields if note empty
    note_parts = []
    if entry.get("death_year"):
        note_parts.append(f"умер{('ла' if is_female(label) else '')} в {entry['death_year']} году")
    if entry.get("birth_year") and entry.get("birth_place"):
        note_parts.append(
            f"родил{('ась' if is_female(label) else 'ся')} "
            f"в {entry['birth_year']} году в {entry['birth_place']}"
        )
    if note:
        note_parts.append(note)
    note_str = "; ".join(note_parts)

    line = f"- **{label}** — {value_full}"
    if note_str:
        line += f"  _({note_str})_"
    return line
```

Where `is_female(label)` checks if label in {Мать, Дочь, Сестра, Бабушка, Внучка, Тётя, Племянница, Свекровь, Золовка, Невестка, ...}.

### 3. Birth place declension (case fix)

В normalize step — `normalize_birth_place_case` — для «в Калинин» → «в Калинине» (locative case). Использовать существующий gazeteer + simple rules для русских имён мест (`-a/-я → -e`, consonant → consonant + `e`).

Подключить уже существующий gazeteer морфологию (task 040b) — у него уже есть локативные формы для канонических мест Каракулиной (Сафроново → Сафронове). Расширить или использовать generic rule.

### 4. Конфиг (опционально)

`bio_data_format_config.json` (generic):
```json
{
  "label_order": ["Отец", "Мать", "Брат", "Сестра", "Бабушка", "Дедушка",
                  "Муж", "Жена", "Сын", "Дочь", "Внук", "Внучка",
                  "Зять", "Сноха", "Тётя", "Дядя", "Племянник", "Племянница",
                  "Золовка", "Свекровь"],
  "female_labels": ["Мать", "Дочь", "Сестра", "Бабушка", "Внучка", "Тётя",
                    "Племянница", "Свекровь", "Золовка", "Жена", "Сноха"]
}
```

### Какой результат ожидается

В v63 `karakulina_v63_text_FULL.md` секция «Семья»:

```markdown
- **Отец** — Рудай Иван Андреевич, плотник
- **Мать** — Рудая Пелагея Алексеевна, работница колхоза  _(умерла в 1933 году)_
- **Бабушка** — Марфа  _(мать отца Валентины)_
- **Муж** — Каракулин Дмитрий, военный  _(умер в 1978 году)_
- **Сын** — Каракулин Валерий  _(родился в 1948 году в Вышнем Волочке)_
- **Дочь** — Каракулина Татьяна  _(родилась в 1956 году в Калинине; рассказчик интервью)_
```

Изменения vs v62a:
- ✅ Единый формат `**Родство** — Имя_полное (note)`
- ✅ Калинин → Калинине (locative case)
- ✅ Малфункциональная строка Нинваны убрана (task 044d-2)
- ✅ Order: parents → spouse → children → grandchildren → siblings → uncles/aunts → nephews/nieces

### Как проверить

1. **Unit-тесты** `tests/test_bio_data_format_normalization.py`:
   - Entry с `value="Иван, плотник"` → split: value=«Иван», profession=«плотник»
   - Entry female detect: label=«Мать» → is_female=True; «Дочь» → True; «Отец» → False
   - Render: female + death_year → «умерла в YYYY году»; male → «умер в YYYY году»
   - Locative: «Калинин» → «Калинине»; «Москва» → «Москве»

2. **Integration** на v62a `book_FINAL_stage3`:
   - Загрузить family entries → normalize → render
   - Все entries канонический формат

3. **Verified-on-run** v63:
   - Открыть `karakulina_v63_text_FULL.md` секция Семья — каждая строка `**X** — Y _(...)_` единого формата
   - «в Калинине» (не «в Калинин»)

---

## Ограничения

- [ ] **Не enforce** structured fields в bio_data JSON если их нет — только при render compose из существующих fields
- [ ] **Idempotent** normalize + render
- [ ] **Generic** для любого subject
- [ ] Female label detect — explicit list в config, не heuristic-only

---

## Dev Review

**Статус:** ожидает

**[TECH]** — pre-answer от Опуса:
- Locative case rule — простой (`-a/-я → -e`; consonant → `+e`; `-ово/-ино → -ове/-ине`) + gazeteer fallback. Не нужен морфологический engine для базовых случаев
- Female label detect — explicit list (не имя detection), потому что label всегда указывает gender unambiguously
- При conflict (note + structured fields) — оба объединяются через `; `

**[PRODUCT]** — нет

**Сложность:** `s` (1-3 ч)
**Риск:** `low` (render layer + normalize, не меняет downstream data)

---

## Verified-on-run

**Cursor:** [после v63]
**Опус:** независимо проверит первые 5 строк bio_data.family render

---

## История

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-18 | `new` | Опус |
