# Задача: chapter_start страницы без текста — code-level enforcement (промпт-правило не работает)

**Статус:** `pending-run-verification` (реализация готова, ждёт прогон на v38/v39 layout)
**Номер:** 024
**Автор:** Даша / Claude
**Дата создания:** 2026-04-30
**Тип:** `код` / `safety-net`
**Связано:** 015 (bug #3), v38 verification (промпт-патч Claude не сработал)

---

## Контекст

В CHANGELOG записи `[2026-04-29]` Claude применила промпт-патч в `08_layout_designer_v3.19.md` и `15_layout_art_director_v1.8.md`:

> ⛔ chapter_start: ТОЛЬКО заголовок + фото, БЕЗ ТЕКСТА:
> Страница начала главы (page_type: "chapter_start") содержит:
> — Номер и название главы (сверху)
> — Одно фото или плейсхолдер фото (снизу или по центру)
> — НИКАКОГО основного текста, абзацев, подзаголовков

При миграции на v3.20 (task 017) Cursor скопировал это правило (строки 988, 1002 в `08_layout_designer_v3.20.md`). Правило **есть** в активном промпте.

При прогоне v38 правило проигнорировано:
- стр 3 (chapter_start ch_02): после `[ФОТО]` идёт `## Детство и сиротство` + полный нарративный абзац
- стр 9 (chapter_start ch_03): после `[ФОТО]` идёт `## Характер, выкованный жизнью` + абзац
- стр 14 (chapter_start ch_04): после `[ФОТО]` идёт нарратив + `### Авоська из зонтика` + ещё абзацы

То есть LLM (Layout Designer) **видит правило в промпте, но не следует ему**. Это типичная LLM-нестабильность: жёсткие промпт-правила работают не 100% случаев. Промпт-only защиты недостаточно.

## Системное решение

**Code-level валидатор** chapter_start страниц. После Layout Designer (или внутри `verify_and_patch_layout_completeness`) проверяет:

Для каждой страницы с `type == "chapter_start"`:
- Допустимые элементы: `chapter_title`, `chapter_subtitle`, `chapter_number`, `photo`, `photo_placeholder`, декоративные.
- **Не допустимо**: `paragraph` (любой), `callout`, `historical_note`, `subheading`, `heading`.

Если на chapter_start странице есть текстовый элемент — два варианта поведения:

**(a) Hard fail.** `sys.exit(1)` — chapter_start со включённым текстом значит LD регрессировал, лучше остановить прогон.
**(b) Auto-clean.** Перенести все нелегальные элементы со страницы chapter_start на следующую страницу (создать новую если нет). Лог `[CHAPTER-START] Перенесено X элементов с chapter_start стр N на стр N+1`.

Cursor рекомендует выбрать на основе ситуации:
- **(a) hard fail для prod** (consistent with 020/022/023 enforcement principle)
- **(b) auto-clean для debug** (не блокирует пилот пока промпт-правило не доедет до 100%)

В данный момент пилот в debug-режиме. Предлагаю гибрид: auto-clean по умолчанию + hard fail при флаге `--strict-chapter-start`. Override-флаг `--allow-chapter-start-text` для случая когда autoр хочет именно с текстом.

## Спек

### Что нужно изменить

В `scripts/test_stage4_karakulina.py` после `verify_and_patch_layout_completeness` (или внутри новой функции `enforce_chapter_start_purity`):

1. Пройти по всем страницам layout.
2. Если `page.type == "chapter_start"` — проверить элементы.
3. Найти текстовые элементы (paragraph / callout / historical_note / любые с `text` или `paragraph_ref`).
4. По умолчанию **auto-clean**: переместить все такие элементы на следующую страницу (создать text-страницу если её нет, с тем же chapter_id).
5. Лог: `[CHAPTER-START] page N (ch_XX): перенесено M элементов на page N+1`.
6. CLI флаги:
   - `--strict-chapter-start` — превратить auto-clean в hard fail.
   - `--allow-chapter-start-text` — отключить enforcement (debug режим).

### Какой результат ожидается

**Verified-on-run:**

1. Прогнать на v38 layout — chapter_start страницы (3, 9, 14) должны очиститься. Текстовые элементы переезжают на стр 4, 10, 15.
2. PDF после: на chapter_start только заголовок + плейсхолдер фото.
3. Visual: открыть полученный PDF, проверить что стр 3, 9, 14 не содержат нарративного текста.

---

## Ограничения

- [ ] Не трогать существующие chapter_body / text страницы — только chapter_start
- [ ] Не сломать ch_01 и epilogue (там chapter_start без фото — это допустимо)
- [ ] Decision auto-clean vs hard fail — настраивается флагом, не hardcode
- [ ] Решение должно быть universalizable

---

## Dev Review

**Статус:** выполнено Cursor

### Диагностика

`enforce_chapter_start_purity()` добавлена в `scripts/test_stage4_karakulina.py` как отдельная функция, вызывается сразу после `verify_and_patch_layout_completeness` (в обоих местах вызова — через `--existing-layout` и в основном LLM-flow).

Конфликта с `verify_and_patch_layout_completeness` нет: функции работают на разных уровнях — verify проверяет *полноту* paragraph_refs, enforce проверяет *допустимость* элементов на chapter_start страницах. Порядок корректный: сначала добавить пропущенные элементы, потом переместить неуместные.

### [PRODUCT-1] Решение

✅ Реализован вариант A (auto-clean по умолчанию) согласно решению Даши.

---

## Реализация (Cursor, 2026-05-01)

### Изменения

**`scripts/test_stage4_karakulina.py`**:
- Добавлена функция `enforce_chapter_start_purity(layout_result, strict, allow_chapter_start_text)`
  — проверяет каждую страницу с `type == "chapter_start"`
  — нелегальные типы: `paragraph`, `callout`, `historical_note`, `subheading`, `heading`
  — по умолчанию auto-clean: переносит нелегальные элементы на следующую страницу (создаёт новую если нет)
  — перенумерует последующие страницы при создании новой
  — лог: `[CHAPTER-START] ⚠️ страница N (ch_XX): перенесено M элементов на страницу N+1`
- Добавлены CLI флаги:
  - `--strict-chapter-start` → hard fail при обнаружении нелегальных элементов
  - `--allow-chapter-start-text` → enforcement отключён (debug)
- Функция вызывается в двух местах основного flow (после `verify_and_patch_layout_completeness`)

### Тестирование (локально)

`scripts/_test_024_local.py` — 5 тестов, все PASS:
- `test_024_clean_page_untouched` — чистые страницы не трогаются
- `test_024_auto_clean_moves_text` — 2 нелегальных элемента переезжают на следующую страницу
- `test_024_creates_new_page_when_needed` — создаётся новая страница, последующие перенумеровываются
- `test_024_strict_mode_exits` — `sys.exit(1)` при strict=True
- `test_024_allow_mode_skips` — enforcement отключается при allow=True

### Verified-on-run

⏳ Требует прогона с v38 layout на сервере. Команда:
```
python scripts/test_stage4_karakulina.py \
  --existing-layout /opt/glava/exports/karakulina_v38_gate2c_layout.json \
  --acceptance-gate 2c
```
Ожидаемый результат: `[CHAPTER-START] ⚠️ страница 3 (ch_02): перенесено N элементов` — стр. 3, 9, 14 чисты.

---

## История статусов

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-04-30 | `new` | Даша / Claude (после визуального ревью v38 PDF) |
| 2026-05-01 | `in-progress` → `pending-run-verification` | Cursor |
