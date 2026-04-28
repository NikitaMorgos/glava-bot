# Рекомендации по доработке — Stage 4 (прогон 2026-04-02)

---

## Архитектурная позиция (зафиксирована)

Верстальщик работает по **Варианту B**: возвращает структурированный JSON
(`pages[]`) с реальным текстом и инструкциями, фиксированный скрипт читает этот
JSON и рендерит PDF.

Это правильная архитектура. Промпт v3 уже содержит Правила 10 и 11
(читать из файлов, Linux-шрифты). Возвращаться к Варианту A (LLM генерирует код)
**не нужно**.

---

## Корневой баг: `build_karakulina_pdf.py` игнорирует инструкции верстальщика

Верстальщик возвращает подробный `pages[]`. Пример из реального прогона:

```json
{
  "page_number": 6,
  "type": "text_with_photo",
  "elements": [
    { "type": "paragraph", "text": "Партийность: член ВКП(б)..." },
    { "type": "photo", "photo_id": "photo_017", "layout": "wrap_right", "caption": "До войны" },
    { "type": "callout", "text": "..." }
  ]
}
```

`build_karakulina_pdf.py` не читает этот JSON. Он открывает `proofreader_report`
напрямую и выкладывает все главы подряд + все фото по порядку. Решения
верстальщика (какое фото на какой странице, wrap_right/wrap_left, callout
в середине главы) полностью игнорируются.

---

## 1. Задача разработчика: написать `pdf_renderer.py`

**Файл:** `scripts/pdf_renderer.py` (или `glava/pdf_renderer.py`)

**Вход:** `layout_result.json` (выход верстальщика — `pages[]` + `style_guide`)

**Выход:** `book.pdf`

Рендерер должен обходить `pages[]` и для каждой страницы вызывать
соответствующий рендер-метод:

```
pages[] от верстальщика
    ↓
pdf_renderer.py (фиксированный код, не LLM)
    ├── type=cover               → обложка по cover_composition
    ├── type=blank               → пустая страница / форзац
    ├── type=toc                 → оглавление (двухпроходный рендеринг)
    ├── type=chapter_start       → разворот с заголовком главы
    ├── type=full_page_photo     → фото на всю страницу
    ├── type=text_with_photo     → текст + фото (wrap_left / wrap_right)
    ├── type=text_only           → текст без фото
    ├── element: callout         → оформленный блок-выноска
    ├── element: historical_note → тёмный инвертированный блок
    └── element: photo           → фото по layout-инструкции
         ↓
    book.pdf
```

Шрифты, стили, отступы — берутся из `style_guide` (возвращает верстальщик)
и/или из фиксированных констант в коде. Не от LLM, не генерируются заново.

**Интеграция в `test_stage4_karakulina.py`:** шаг 2.5 вместо
`build_karakulina_pdf.py` вызывать `pdf_renderer.py --layout layout_result.json`.

---

## 2. Синхронизировать `pipeline_config.json`

**Файл:** `prompts/pipeline_config.json` в репозитории

**Проблема:** на сервере `layout_designer` указывает на `08_layout_designer_v3.md`,
`interview_architect` на `11_interview_architect_v4.md`. Локальный конфиг
всё ещё указывает на v1.

**Действие:**

```bash
ssh glava "cat /opt/glava/prompts/pipeline_config.json"
```

Обновить локальный `pipeline_config.json` под серверные версии промптов.

---

## 3. Добавить `--existing-page-plan` в тестовый скрипт

**Файл:** `scripts/test_stage4_karakulina.py`

**Проблема:** при каждом перезапуске арт-директор тратит ~54с и токены заново.
Если `page_plan` уже есть — нужно уметь его переиспользовать.

**Действие:** добавить флаг по аналогии с `--use-existing-cover`:

```bash
python test_stage4_karakulina.py \
  --use-existing-cover exports/...call2.json \
  --existing-page-plan exports/karakulina_stage4_page_plan_*.json
```

---

## 4. QA: проверять что текст из `book_final` попал в `pages[]`

**Файл:** `09_qa_layout_v1.md`

**Сейчас:** QA проверяет структуру `page_map` (типы страниц, наличие фото).
Это структурная проверка — без PDF.

**Улучшение:** верстальщик v3 кладёт реальные тексты в `pages[].elements[].text`.
QA может проверить, что:
- все `chapter_id` из `book_final.chapters` присутствуют в `pages[]`
- ни одна глава не потеряна и не обрезана
- все `callout.id` из `book_final.callouts` размещены

Это позволит находить ошибки типа «верстальщик потерял главу 4» ещё до сборки PDF.

---

## 5. Что уже сделано (не требует действий)

| Что | Где |
|-----|-----|
| DEFAULT_FACT_MAP → v5 — Interview Architect теперь запускается | `test_stage4_karakulina.py` |
| validate_layout_output принимает `pages[]` и `layout_instructions.pages[]` | `test_stage4_karakulina.py` |
| Шаг 2.5: автосборка PDF через subprocess | `test_stage4_karakulina.py` |
| pdf_path передаётся в QA | `test_stage4_karakulina.py` |
| Флаг `--use-existing-cover` / `--existing-portrait` | `test_stage4_karakulina.py` |
| Правила 10 и 11 в промпте v1 (на случай fallback) | `08_layout_designer_v1.md` |
| Правила 10 и 11 уже были в промпте v3 | `08_layout_designer_v3.md` |

---

## Сводная таблица приоритетов

| # | Кто | Файл | Что сделать | Приоритет |
|---|-----|------|-------------|-----------|
| 1 | Разработчик | `scripts/pdf_renderer.py` (новый) | Написать рендерер `pages[]` → PDF | 🔴 Высокий |
| 2 | Разработчик | `prompts/pipeline_config.json` | Синхронизировать с серверными версиями v3/v4 | 🟡 Средний |
| 3 | Разработчик | `test_stage4_karakulina.py` | Добавить `--existing-page-plan` | 🟡 Средний |
| 4 | Даша | `09_qa_layout_v1.md` | Добавить проверку completeness текста из book_final | 🟢 Низкий |
