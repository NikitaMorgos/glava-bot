# Задача: Подзаголовки `## / ###` как структурный элемент, а не markdown-строка

**Статус:** `pending-run-verification` (реализация готова, ждёт прогон для PDF-верификации)
**Номер:** 025
**Автор:** Даша / Claude
**Дата создания:** 2026-04-30
**Тип:** `архитектурное-изменение` / код + промпт
**Связано:** 015 (новый bug, найденный в v38), 017 (ссылочная архитектура layout)

---

## Контекст

При визуальной проверке PDF v38 обнаружено что подзаголовки внутри глав рендерятся **буквально с символами `###`**:

> ### Авоська из зонтика
> ### Почерк с отрицательным наклоном
> ## Детство и сиротство
> ## Характер, выкованный жизнью

То есть в PDF выводится `### Авоська из зонтика` как обычная текстовая строка в потоке абзацев, не как стилизованный подзаголовок (жирный/увеличенный кегль).

### Корневая причина

Ghostwriter при формировании `chapter.content` или `chapter.paragraphs[].text` эмитит подразделы в **markdown-стиле**: `## Заголовок` или `### Заголовок` как часть строки текста параграфа.

В book_FINAL это попадает как обычный paragraph:
```json
{"id": "ch_02_p_004", "text": "## Детство и сиротство\n\nВалентина родилась..."}
```
или как отдельный paragraph только с заголовком:
```json
{"id": "ch_02_p_003", "text": "## Детство и сиротство"}
```

Layout Designer (после 017) формирует `paragraph_ref`. pdf_renderer резолвит и рендерит через `_render_paragraph` стандартным styles `body_text`. **Никакого markdown-парсинга нет.** Символы `##` / `###` выводятся буквально.

### Архитектурный пробел

У нас есть типы элементов:
- `paragraph` — обычный текст
- `callout` — выноска
- `historical_note` — историч. справка
- `chapter_title` / `chapter_start` — заголовок главы
- `bio_data` — структурный блок

**Нет типа `heading` / `subheading`** для подразделов внутри главы.

Подразделы — это не выноски и не главы, это промежуточный уровень иерархии. В прежней архитектуре (до 017) LLM выкручивался markdown-маркерами; pdf_renderer на каком-то этапе мог их парсить. После 017 markdown-маркеры выходят буквально.

## Системное решение

Ввести новый тип элемента **`heading`** с уровнем (`level: 2` для `##`, `level: 3` для `###`):

### 1. book_FINAL.json

```json
{
  "chapter_id": "ch_02",
  "paragraphs": [
    {"id": "p_003", "type": "heading", "level": 2, "text": "Детство и сиротство"},
    {"id": "p_004", "type": "paragraph", "text": "Валентина родилась 17 декабря..."},
    ...
  ]
}
```

Каждый heading получает свой стабильный id (так же как paragraph), может быть упомянут в layout через ref.

### 2. Ghostwriter (промпт `03_ghostwriter_v2.14.md`)

Добавить правило: подразделы внутри главы эмитить как **отдельные paragraph-объекты** с `type: "heading"` и `level: 2/3`, НЕ как `## текст` / `### текст` внутри text поля.

Если GW по привычке всё-таки выдаст `### Заголовок` строкой — добавить **post-processor** (код, не промпт) который найдёт такие строки в paragraphs и преобразует их в `heading` элементы. Это safety net на случай LLM-нестабильности.

### 3. Layout Designer (промпт `08_layout_designer_v3.20.md`)

Поддержать новый тип в page_plan / layout: `{"type": "heading", "heading_ref": "p_003", "chapter_id": "ch_02"}`.

В правилах пагинации: heading с keepWithNext=True (заголовок остаётся с текстом следующим за ним).

### 4. pdf_renderer.py

Новый метод `_render_heading(elem, level)`:
- Резолвит `heading_ref` через book_FINAL (как paragraph_ref)
- Применяет стиль `subheading_h2` или `subheading_h3` в зависимости от level
- Стили: больший кегль (PT Sans, ~14-16pt для h2, ~12-14pt для h3), **жирный**, отступ сверху больше, снизу меньше (keepWithNext)

### 5. Совместимость

- Legacy fallback: если в book_FINAL встречается paragraph с text начинающимся на `## ` или `### ` — auto-detect heading на этапе чтения, преобразовать. Лог: `[BOOK-NORMALIZE] auto-detected heading: "Детство и сиротство" → heading.level=2`. Этот fallback должен предупредить, потому что это сигнал что GW не следует новому правилу.

### Какой результат ожидается

После фикса:
- В PDF v39+ подзаголовки выводятся **стилизованными** (жирный, увеличенный кегль, без символов `##` / `###`)
- В book_FINAL.json элементы heading имеют отдельный type, не зашиты в text
- pdf_renderer корректно различает heading и paragraph

**Verified-on-run:**
1. Сгенерировать тестовый book_FINAL с heading элементами + один legacy paragraph с `### Заголовок` строкой.
2. Прогнать pdf_renderer.
3. PDF: оба варианта рендерятся корректно (стилизованные заголовки), legacy путь даёт warn-лог.
4. Symbols `##` / `###` в финальном PDF отсутствуют.

---

## Ограничения

- [ ] Не сломать существующие book_FINAL без heading-элементов (legacy fallback)
- [ ] Не вводить markdown-парсер целиком — нам нужны только заголовки. Другой markdown (bold, italic, lists) — отдельная задача.
- [ ] Сохранить ссылочную архитектуру (heading тоже через ref, не inline text)

---

## Dev Review

**Статус:** выполнено Cursor

### [TECH] Технические флаги

**Post-processor размещён в `prepare_book_for_layout()`** (pipeline_utils.py) — правильное место: единая точка нормализации book_FINAL перед передачей в Layout Designer и pdf_renderer. Это означает что и LD, и renderer видят уже нормализованные данные.

**BookIndex** обновлён для хранения `{"text": ..., "type": ...}` вместо строки. Метод `get()` возвращает text (обратная совместимость). Новый метод `get_type()` возвращает тип элемента.

**`prepare_book_for_layout()`** — обновлён: параграф с текстом `^#{2,3}\s+(.+)$` конвертируется в `{"id": "pN", "type": "subheading", "text": "..."}` с warn-логом `[BOOK-NORMALIZE]`.

### [PRODUCT-1/2] Решения Даши

✅ A (auto-convert + warn) — реализовано
✅ Один уровень `subheading` без level — реализовано (`##` и `###` → один тип)

---

## Реализация (Cursor, 2026-05-01)

### Изменения

**`pipeline_utils.py`** — `prepare_book_for_layout()`:
- Regex `^#{2,3}\s+(.+)$` конвертирует `## text` и `### text` строки в `{"id": "pN", "type": "subheading", "text": "..."}`
- Лог: `[BOOK-NORMALIZE] auto-detected subheading in ch_XX/pN: "текст" (legacy ## / ### → subheading)`
- Обычные параграфы — `{"id": "pN", "text": "..."}` (без поля type, default = "paragraph")

**`scripts/pdf_renderer.py`** — `BookIndex`:
- `_index` теперь хранит `{pid: {"text": ..., "type": ...}}` вместо `{pid: text}`
- `.get(ch_id, pid)` возвращает text (обратная совместимость сохранена)
- Новый `.get_type(ch_id, pid)` → "subheading" / "paragraph"

**`scripts/pdf_renderer.py`** — новый метод `_render_subheading(c, elem, y)`:
- Поддерживает `subheading_ref`, `paragraph_ref`, `paragraph_id` → lookup через BookIndex
- Рендерит через PT Sans Bold (section_size), один стиль без level
- Inline text fallback для legacy

**`scripts/pdf_renderer.py`** — `_render_elements()`:
- Добавлен case `subheading` и `section_header` → `_render_subheading()`

**`scripts/pdf_renderer.py`** — `_render_paragraph()`:
- Обновлён для обработки `### ` prefix (ранее только `## `)
- При резолвинге через BookIndex: если `get_type()` == "subheading" → автоматически рендерит как subheading

**`scripts/validate_layout_fidelity.py`** — `_get_para_ref()`:
- Добавлена поддержка `subheading_ref`

**`scripts/validate_layout_fidelity.py`** — `_collect_layout_refs()`:
- Фильтр изменён: `type in ("paragraph", "subheading", "section_header")` вместо `type == "paragraph"`

**`scripts/test_stage4_karakulina.py`** — `verify_and_patch_layout_completeness()`:
- Сбор layout_tuples: добавлены типы `subheading`, `section_header`
- Добавлена `book_para_types` dict для отслеживания типов элементов книги
- Патч пропущенных элементов: subheading → `{"type": "subheading", "subheading_ref": pid}` вместо paragraph

**`prompts/08_layout_designer_v3.21.md`** (новый файл, копия v3.20 + изменения):
- Добавлено критическое правило: подзаголовки как `{"type": "subheading", "subheading_ref": "pN", "chapter_id": "ch_XX"}`
- Примеры правильного и неправильного формата

**`prompts/pipeline_config.json`**:
- `layout_designer.prompt_file`: `08_layout_designer_v3.20.md` → `08_layout_designer_v3.21.md`

### Тестирование (локально)

`scripts/_test_025_026_local.py` — 3 теста для 025, все PASS:
- `test_025_subheading_normalization` — `## ` и `### ` конвертируются в subheading, обычные параграфы остаются
- `test_025_no_false_conversion` — `#` в середине строки не конвертируется
- `test_025_book_index_type` — BookIndex.get_type() возвращает правильный тип

### Verified-on-run

⏳ Требует прогона Stage 4 (gate 2a/2b/2c) с book_FINAL содержащим legacy `##`/`###`.
Команда: прогон Stage 4 с текущим v37 или новым v40 book_FINAL.
Ожидаемый результат: `[BOOK-NORMALIZE]` в логе, PDF без символов `##`/`###`.

---

## История статусов

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-04-30 | `new` | Даша / Claude (новый bug найден визуально на v38) |
| 2026-05-01 | `in-progress` → `pending-run-verification` | Cursor |
