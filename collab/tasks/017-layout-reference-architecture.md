# Задача: Layout Designer — переход на ссылочную архитектуру (paragraph_ref)

**Статус:** `done` (v38 verified · 2026-04-30. Claude локально проверила PDF v38: 17 страниц, 14726 chars, нет дублей, ch_03 в правильном порядке. Fidelity PASS работает.)
**Автор:** Даша / Claude
**Дата создания:** 2026-04-29
**Тип:** `архитектурное-изменение` / код
**Связано:** task 008 (исходная задача про потерю текста, которая была production-confirmed на v36), task 015 (пилот Каракулиной — bugs #1, #2)

> Это **эскалация** task 008. Исходная 008 в статусе `new` с апреля; на пилоте Каракулиной 2026-04-29 баг production-confirmed с двумя дополнительными симптомами. Задача 017 заменяет 008 как формальная Dev Review с обновлёнными доказательствами.

---

## Контекст

### Симптомы на пилоте

На прогоне Каракулиной v36, gate2c (text-only PDF, 2026-04-29) ручной просмотр PDF показал две связанные проблемы Layout Designer:

**Bug #1 — Дубль 5 подглав ch_02:**

В PDF страницы 5/11, 7/12, 8/13, 9/14, 10/15 содержат одни и те же подглавы дважды («Учёба и первая работа», «Встреча с будущим мужем», «Венгерские годы», «Трудовые достижения», «Последние годы»). В `book_FINAL.json` каждая из этих подглав встречается **один раз**. Дубль возник на этапе Layout Designer / pdf_renderer.

Согласно отчёту Cursor по Stage 4: «Layout Designer пропустил все 69 абзацев → авто-патч вернул всё». То есть auto-patch вернул потерянные абзацы **в дополнение** к уже выведенным, а не **вместо** пропущенных.

**Bug #2 — Перетасовка ch_03 + пропуск подглавы:**

В `book_FINAL.json` глава ch_03 «Портрет человека» имеет 7 подзаголовков в порядке: Характер → Труд → Советская этика → Порядок и красота → Гостеприимство → Традиции → Сложности.

В PDF: Труд (стр 17) → Традиции (стр 19) → Характер (стр 20) → Советская этика → Гостеприимство → Сложности. **6 подзаголовков** вместо 7 (отсутствует «Порядок и красота»), порядок переставлен.

### Корневая причина

Layout Designer работает на уровне **эмиссии текста**: он получает book_FINAL и выдаёт layout с готовыми текстовыми блоками. При этом:

- Может пропустить блок (как было в v36 — 69 абзацев)
- Может продублировать блок (после auto-patch)
- Может переставить блоки (порядок не гарантируется)
- Может потерять блок безвозвратно

Auto-patch — это паллиатив: он маскирует пропуски, но не различает «вернуть пропущенное» от «добавить ещё раз». Архитектурно это deadlock: все три бага (#1, #2 и потенциальные потери) — следствия одного решения (text emission в LD).

---

## Спек

### Архитектурное решение

**Перевести Layout Designer на ссылочную архитектуру.**

**Было:**
```
LD получает: book_FINAL.json (текст всех глав и абзацев)
LD выдаёт: layout.json с массивом элементов, каждый содержит .text
pdf_renderer: рендерит .text напрямую в PDF
```

**Должно стать:**
```
LD получает: book_FINAL.json + структура (chapter_id, paragraph_id для каждого блока)
LD выдаёт: layout.json со ссылками — каждый элемент содержит paragraph_id (или callout_id, historical_note_id), но НЕ .text
pdf_renderer: для каждого элемента layout.json находит соответствующий блок в book_FINAL.json по id и рендерит его текст
```

### Что это даёт (структурно)

1. **Дубли невозможны:** один paragraph_id может быть упомянут в layout только один раз. Дублирование = ошибка валидации, не результат рендера.
2. **Пропуски ловятся:** после LD проверка «множество paragraph_id на выходе == множество на входе» — если меньше, fail, не auto-patch.
3. **Перетасовка ловится:** после LD проверка «порядок paragraph_id в layout соответствует порядку в book_FINAL» — если нет, fail.
4. **Текст не теряется:** pdf_renderer всегда тянет текст из book_FINAL — единственного источника истины.

### Что нужно реализовать

**1. Изменить формат `book_FINAL.json`:**
   - Каждый paragraph должен иметь стабильный `paragraph_id` (например, `ch_02_p_001`, `ch_02_p_002`...)
   - Аналогично callouts (`callout_001`) и historical_notes (`hist_001`) — у них уже есть id, проверить
   - Если в текущем формате id'ов нет на уровне абзацев — добавить (Ghostwriter должен их генерировать)

**2. Изменить промпт Layout Designer (`08_layout_designer_v3.19.md`):**
   - LD на выходе формирует элементы layout с `paragraph_ref: "ch_02_p_001"` вместо `text: "..."`
   - Аналогично `callout_ref`, `historical_note_ref`, `photo_id`
   - Промпт явно запрещает писать `text:` поле — только ссылки

**3. Изменить `pdf_renderer.py`:**
   - При рендере каждого элемента смотрит на `paragraph_ref`/`callout_ref`/etc.
   - Достаёт текст из `book_FINAL.json` по этому id
   - Если ссылка не найдена — fail с явной ошибкой (не пустой блок)

**4. Добавить валидатор `validate_layout_fidelity.py`:**
   - На вход: `book_FINAL.json` + `layout.json`
   - Проверка 1: множество `paragraph_id` в layout = множество в book_FINAL (с учётом разделения по главам)
   - Проверка 2: внутри каждой главы порядок `paragraph_id` в layout соответствует порядку в book_FINAL
   - Проверка 3: ни один `paragraph_id` не встречается в layout более одного раза
   - При нарушении — `sys.exit(1)` с детальным отчётом (что пропущено, что продублировано, где переставлено)
   - Запускается в `test_stage4_*.py` после Layout Designer, перед `pdf_renderer`

**5. Совместимость с Ghostwriter:**
   - GW должен генерировать paragraph_id в `book_FINAL.json`. Если он сейчас этого не делает — добавить правило в промпт `03_ghostwriter_v2.14.md`.
   - Альтернатива: код-постпроцессор после GW добавляет id'ы детерминированно (по порядку: `ch_02_p_001`, `ch_02_p_002`, ...).

### Какой результат ожидается

После прогона Stage 4 на новой архитектуре:
- В `layout.json` элементы содержат `paragraph_ref`, не `text`
- Валидатор `validate_layout_fidelity.py` проходит с PASS
- В PDF каждый абзац ровно один раз, в правильном порядке, ничего не пропущено

Регрессия на пилоте Каракулиной:
- ch_02: 10 подглав, каждая ровно один раз, в правильном порядке
- ch_03: 7 подзаголовков (включая «Порядок и красота»), в правильном порядке
- Никаких дублей страниц, никаких пропусков подглав

### Как проверить

```bash
# 1. Прогнать Stage 4 на текущем v36 book_FINAL_stage3 (после фикса GW для добавления id)
python scripts/test_stage4_karakulina.py --acceptance-gate 2c --prefix karakulina_v37 ...

# 2. Проверить layout.json — нет .text полей в элементах
python -c "
import json
layout = json.load(open('exports/.../karakulina_v37_layout.json', encoding='utf-8'))
for page in layout['pages']:
    for el in page.get('elements', []):
        if el.get('type') in ['paragraph', 'callout', 'historical_note']:
            assert 'paragraph_ref' in el or 'callout_ref' in el or 'historical_note_ref' in el, f'No ref in {el}'
            assert 'text' not in el, f'Text leaked: {el}'
print('OK: layout uses refs, no embedded text')
"

# 3. Прогнать валидатор fidelity
python scripts/validate_layout_fidelity.py \
    --book-final exports/.../book_FINAL_stage3_v37.json \
    --layout exports/.../karakulina_v37_layout.json
# Ожидается: PASS

# 4. Проверить PDF: ch_02 имеет 10 подглав ровно один раз, ch_03 имеет 7 в правильном порядке
```

---

## Ограничения

- [ ] Не ломать обратную совместимость с уже сохранёнными layout.json (legacy support — проверять есть ли `text` поле, рендерить оба формата на переходный период)
- [ ] paragraph_id должен быть стабильным между прогонами одного и того же book_FINAL (детерминированная генерация)
- [ ] Не вводить новых внешних зависимостей
- [ ] `validate_layout_fidelity` должен иметь флаг `--allow-mismatch` для debug-режима (как `--allow-fc-fail`), но по умолчанию hard fail
- [ ] Все изменения должны быть universalizable — никаких Каракулиной-специфичных решений

---

## Dev Review

> Заполняет Cursor до реализации.

**Статус:** заполнено Cursor 2026-04-29

### Диагностика перед реализацией

**Bug #1 (дубль ch_02) и Bug #2 (перестановка ch_03) подтверждены. Корневая причина — один механизм.**

**Текущая архитектура:**
1. `prepare_book_for_layout()` (`pipeline_utils.py:53`) добавляет `paragraphs: [{id: "p1", text: "..."}, ...]` в каждую главу book_final.
2. Layout Designer получает book_final с этими paragraphs → **должен** ссылаться на `paragraph_id`, но в реальности генерирует текстовые блоки (`type: "paragraph", text: "..."`) без поля `paragraph_id`.
3. `verify_and_patch_layout_completeness()` пытается восстановить пропущенные: если `paragraph_id` не найден среди элементов layout → добавляет новый элемент `{type: "paragraph", chapter_id: "chXX", paragraph_id: "pN", text: <из book>}`.
4. В v36 LD не выдал ни одного `paragraph_id` в 69 элементах → `verify_and_patch` добавил ВСЕ 69 параграфов дополнительно. LD при этом уже вывел свои текстовые блоки (которые содержат текст, но без id) → финальный layout содержит 69 LD-блоков (без id) + 69 patch-блоков (с id) = **138 блоков**, откуда дубли.
5. **Bug #2 (перестановка ch_03):** LD может выводить подглавы не в исходном порядке. В текущей архитектуре порядок элементов в layout[].elements определяет порядок рендера — нет валидатора порядка.

**Paragraph_id в book_final:** уже генерируются `prepare_book_for_layout()` как `p1, p2, ...` per-chapter. НО они не уникальны глобально — обе главы ch_02 и ch_03 имеют `p1`. Ссылки в layout должны быть `chapter_id + paragraph_id`, как и делает `book_index.get(chapter_id, paragraph_id)` в pdf_renderer.

**Callouts и historical_notes:** у них уже есть id (`callout_id`, `note_id`) в book_final. В layout они представлены элементами с `callout_id`/`note_id` полями — значит для них ссылочная архитектура УЖЕ частично работает.

**Что нужно изменить:**
1. **LD prompt**: запретить `text:` поле в paragraph-элементах, только `paragraph_ref: "ch_02/p1"` (или `chapter_id + paragraph_id`).
2. **pdf_renderer**: добавить резолвинг `paragraph_ref` → текст через `book_index.get(chapter_id, pid)`. Обратная совместимость: если `text:` присутствует (legacy) — использовать его. Если `paragraph_ref` → резолвить.
3. **`verify_and_patch_layout_completeness()`**: после перехода на refs — должен проверять ref-completeness, не text-completeness. До перехода — можно оставить как есть для legacy.
4. **Новый `validate_layout_fidelity.py`**: проверка множества refs, порядка, отсутствия дублей.
5. **GW**: paragraph_id уже генерируются кодом (`prepare_book_for_layout`), не GW. GW изменять не нужно в части id-генерации — см. [TECH-2] ниже.

### [TECH] Технические флаги

**[TECH-1] `paragraph_ref` должен включать `chapter_id`.**
Текущие id `p1, p2...` не уникальны глобально. Два варианта:
- (a) `paragraph_ref: "ch_02/p1"` — path-style
- (b) два поля: `chapter_ref: "ch_02"` + `paragraph_ref: "p1"` — совместимо с текущим `book_index.get(chapter_id, paragraph_id)`

Рекомендация: вариант (b) — не нужно парсить строки. `chapter_id` уже есть в большинстве элементов layout.

**[TECH-2] Кто генерирует paragraph_id — код vs GW.**
Открытый архитектурный вопрос из спека: `prepare_book_for_layout()` уже генерирует `p1, p2...` детерминированно. Ghostwriter не должен отвечать за id-генерацию — он работает с содержимым, а не с версткой. Рекомендация: **детерминированный код в `prepare_book_for_layout()`**, GW-промпт изменять не нужно.

Однако промпт GW упомянут в спеке «добавить правило в 03_ghostwriter_v2.14.md». Это только для информационного контекста (чтобы GW понимал что абзацы будут пронумерованы), не для изменения поведения.

**[TECH-3] Обратная совместимость legacy layout JSON.**
Saved layout JSONs (v36, v28) содержат `text:` поля. После изменения pdf_renderer будет два code path:
- `if "paragraph_ref" in elem: text = book_index.get(...)` ← новый
- `elif "text" in elem: text = elem["text"]` ← legacy

Нужен `--strict-refs` флаг у `pdf_renderer.py` который запрещает legacy path в production.

**[TECH-4] Размер layout.json значительно уменьшится.**
Сейчас layout включает полный текст всех абзацев (~30-50K chars). После перехода на refs — только `chapter_id + paragraph_id` (~100 chars per element). Ожидаемый размер: 56K → ~5K. Снижает риск token-limit у LD.

**[TECH-5] `validate_layout_fidelity.py` — три независимые проверки.**
Проверка 1 (completeness): `{(ch_id, para_id) for ch, para in layout}` == `{(ch_id, para_id) for ch in book}`.
Проверка 2 (order): для каждой главы порядок para_id в layout соответствует порядку в book.paragraphs.
Проверка 3 (uniqueness): `Counter((ch_id, para_id) for ...)` — все значения == 1.
Результат: exit(0) PASS / exit(1) FAIL с детальным diff.

**[TECH-6] Inline-форматирование (bold, italic) в абзацах.**
Некоторые абзацы book_final могут содержать markdown-разметку (`**bold**`, `*italic*`). Это должен обрабатывать pdf_renderer при резолвинге `text = book_index.get(...)` — не влияет на ссылочную архитектуру.

**[TECH-7] `verify_and_patch_layout_completeness()` — поведение до/после перехода.**
До перехода на refs: функция ищет `paragraph_id` в элементах. Новые LD-промпт будет выдавать refs → функция найдёт все id → не будет добавлять дублей. Auto-patch останется как safety net для edge-cases, но основной flow не будет его задействовать.

### [PRODUCT] Продуктовые флаги

**[PRODUCT-1] Где генерировать paragraph_id — код или GW?**
Мой ответ: **детерминированный код** в `prepare_book_for_layout()`. Не GW. Аргументы:
1. GW уже выдаёт сложный JSON — добавление id усложняет промпт без выгоды.
2. Детерминированность критична: `ch_02_p1` должен указывать на один и тот же абзац при перезапуске Stage 4 на том же book_final. Код это гарантирует, GW — нет.
3. `prepare_book_for_layout()` уже делает это — нужно только поменять формат id с `p1` на включающий chapter_id (если нужно) или использовать двойной lookup (chapter_id + p1).
Эскалировать этот вопрос не нужно — рекомендация чёткая.

**[PRODUCT-2] `validate_layout_fidelity` — hard fail или мягкое предупреждение на переходный период?**
Спек говорит hard fail (`sys.exit(1)`) по умолчанию. Согласен. Но нужен `--allow-mismatch` для debug (уже в спеке). Дополнительно: в `test_stage4_*.py` добавить флаг `--skip-fidelity-check` аналогично `--skip-qa` для emergency debug.

**[PRODUCT-3] Что если Layout Designer выдаёт ref на несуществующий paragraph_id?**
pdf_renderer с `--strict-refs` должен: (a) fail с сообщением «ref ch_02/p99 not found in book_final», (b) не рендерить пустой блок молча. Это новое требование к renderer — добавить в спек реализации.

**Оценка сложности:** `l` (затрагивает 4 файла: промпт LD, pdf_renderer, validate_layout_fidelity.py новый, test_stage4 оркестрация; промпт GW — косметика)
**Оценка риска:** `high` — изменение рендеринга PDF. Критично протестировать на v36 данных до перепрогона пилота. Митигация: legacy fallback path в renderer + `--strict-refs` flag для постепенного перехода.

---

## Dev Review Response

**Статус:** заполнено Claude · 2026-04-29 (TECH автономно, PRODUCT эскалирован Даше)

### Ответы на [TECH] флаги (Claude, автономно)

**[TECH-1] paragraph_ref должен включать chapter_id — вариант (b): два поля** ✅ ПРИНИМАЮ.
`{chapter_id: "ch_02", paragraph_ref: "p1"}` лучше чем составной id `"ch_02_p_001"`. Аргументы Cursor разумные: совместимость с существующим `book_index.get()`, человекочитаемость в layout, проще дебажить. Также удобнее для валидатора (per-chapter checks).

**[TECH-2] paragraph_id генерирует код через `prepare_book_for_layout()`** ✅ ПРИНИМАЮ.
Это полностью совпадает с моей рекомендацией (которую я хотела эскалировать как PRODUCT-1). Cursor подтверждает что функция уже существует и делает это сейчас — значит закрыто как [TECH], не нужно эскалировать. GW не нагружаем дополнительной ответственностью, генерация остаётся детерминированной.

**Поскольку Cursor закрыл это как [TECH] и я согласна, [PRODUCT-1] из исходного списка снимается** — paragraph_id остаётся в коде, GW не трогаем.

**[TECH-3] Обратная совместимость через legacy fallback в renderer** ✅ ПРИНИМАЮ.
`if "paragraph_ref" in el: resolve from book_FINAL else if "text" in el: render legacy` — даёт переходный период. Старые сохранённые layout.json продолжают рендериться. После полной миграции (несколько прогонов) можно удалить legacy path в отдельной задаче.

Уточнение: добавь warn-лог при использовании legacy path (чтобы видеть какие layouts ещё в старом формате). Когда warn перестанет появляться — фактический сигнал что можно убрать legacy.

**[TECH-4] Размер layout.json упадёт ~56K → ~5K** ✅ ПРИНИМАЮ как побочный плюс.
Это означает что в дебаге проще читать layout, и stream от LD будет короче (меньше токенов на output → дешевле, быстрее). Зафиксировать в реализации.

### Эскалация [PRODUCT] флагов Даше

**[PRODUCT-3] Если renderer получает ref на несуществующий paragraph_id — что делать?**

Cursor рекомендует: «fail явной ошибкой, не пустой блок».

Моя рекомендация: **поддерживаю fail**. Аргументы:
- Silent fallback (пустой блок или skip) — это тот же класс деградации что auto-patch в текущей архитектуре. Маскирует баг, не лечит.
- Hard fail с понятным сообщением (`paragraph_ref "ch_02:p15" not found in book_FINAL`) даёт точную диагностику.
- Симметрично с FC FAIL и validate_layout_fidelity — согласованная политика «нашли inconsistency → стоп».
- Override-флаг `--allow-missing-refs` для debug-режима (как уже есть `--allow-fc-fail`, `--allow-mismatch`).

**Решение Даши (2026-04-29):** ✅ согласна — fail by default + override-флаг `--allow-missing-refs`.

---

**Итог:** `spec-approved`. Все [TECH] и [PRODUCT] закрыты. Cursor может приступать к реализации.

---

## Реализация

**Статус:** реализовано Cursor · 2026-04-29 · `dasha-review`

**Что сделано:**

1. **Промпт LD v3.20** (`prompts/08_layout_designer_v3.20.md`):
   - Новый файл на базе v3.19, bumped version
   - Все примеры `paragraph` элементов обновлены: `{"type": "paragraph", "text": "..."}` → `{"type": "paragraph", "chapter_id": "ch_xx", "paragraph_ref": "pN"}`
   - Добавлено критическое правило "ССЫЛОЧНАЯ АРХИТЕКТУРА АБЗАЦЕВ": ЗАПРЕЩЕНО `text` в paragraph, ОБЯЗАТЕЛЬНО `paragraph_ref` + `chapter_id`
   - `pipeline_config.json` обновлён: `08_layout_designer_v3.19.md` → `08_layout_designer_v3.20.md`

2. **`pdf_renderer.py`**:
   - `RenderOptions` получил `strict_refs: bool = False` и `allow_missing_refs: bool = False`
   - `_elem_para_text()`: поддерживает `paragraph_ref` (v3.20+), `paragraph_id` (v3.19 legacy), `text` (legacy с warn-логом)
   - `_render_paragraph()`: аналогично + в `strict_refs` режиме поднимает `ValueError` при ненайденном ref
   - `BookIndex` docstring обновлён
   - CLI: добавлены `--strict-refs` и `--allow-missing-refs` флаги

3. **`verify_and_patch_layout_completeness()`** (`test_stage4_karakulina.py`):
   - Распознаёт `paragraph_ref` (v3.20+) наравне с `paragraph_id` (v3.19)
   - Новые патч-элементы используют `paragraph_ref` вместо `paragraph_id`

4. **Новый `scripts/validate_layout_fidelity.py`**:
   - Три проверки: Completeness, Order, Uniqueness
   - `--allow-mismatch` для warn-only, `--skip-fidelity-check` для аварийного обхода
   - Интегрирован в оба code path Stage 4 (existing-layout: allow_mismatch=True, main: strict)

**Файлы изменены:**
- `prompts/08_layout_designer_v3.20.md` — новый файл (copy of v3.19 + arch changes)
- `prompts/pipeline_config.json` — обновлена ссылка на v3.20
- `scripts/pdf_renderer.py` — strict_refs, paragraph_ref support, legacy warn
- `scripts/test_stage4_karakulina.py` — verify_and_patch + fidelity integration
- `scripts/validate_layout_fidelity.py` — новый файл

**Что не изменилось (backward compat):**
- Старые layout JSON (v36, v28) с `text:` полями продолжают работать через legacy path
- При использовании legacy path в renderer печатается `[RENDERER] ⚠️ legacy text fallback`
- Этот warn-лог — сигнал для удаления legacy path после полной миграции

**Как проверить:**
```bash
# Валидация нового layout (после перепрогона Stage 4 на v3.20):
python scripts/validate_layout_fidelity.py \
  --layout /opt/glava/exports/karakulina_v37_stage4_iter1_<ts>.json \
  --book /opt/glava/exports/karakulina_v36/book_FINAL_stage3_v36.json

# Ожидаемый результат если LD правильно использует refs:
# [FIDELITY] ✅ Проверки пройдены: N абзацев, порядок OK, нет дублей.

# Рендер в strict mode:
python scripts/pdf_renderer.py --layout ... --book ... --strict-refs
```

---

## Комментарии и итерации

### 2026-04-29 — Даша / Claude

Эскалация task 008. Исходная 008 в `new` с апреля. На пилоте Каракулиной production-confirmed:
- Bug #1: 5 подглав ch_02 эмитятся дважды (auto-patch добавил вместо подмены)
- Bug #2: ch_03 переставлена + одна подглава отсутствует

Cursor в отчёте Stage 4 сам отметил «task 008 (ссылочная архитектура) остаётся актуальной». Теперь это формальная задача с двумя production-doc'd симптомами и спецификацией решения.

008 будет закрыта как `superseded-by-017` после approval этой задачи.

---

## История статусов

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-04-29 | `new` (эскалация task 008 после production-evidence) | Даша / Claude |
| 2026-04-29 | `dev-review` (Cursor заполнил диагностику и флаги) | Cursor |
| 2026-04-29 | `spec-approved` (Даша подтвердила PRODUCT-3) | Даша |
| 2026-04-29 | `dasha-review` (реализация завершена Cursor) | Cursor |
