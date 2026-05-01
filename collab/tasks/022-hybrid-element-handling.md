# Задача: verify_and_patch_layout_completeness — корректная обработка hybrid элементов + фикс счётчика

**Статус:** `done` (v38 verified · 2026-04-30. Unit-test PASS — hybrid без флага → exit 1, с флагом → warn. На v38 hybrid не возникал.)
**Номер:** 022
**Автор:** Даша / Claude (на основе разбора Opus)
**Дата создания:** 2026-04-30
**Тип:** `код` / `safety-net`
**Связано:** task 017 (ссылочная архитектура), task 019 (verification run где это всплыло)

---

## Контекст

В рамках task 017 был добавлен auto-patch механизм `verify_and_patch_layout_completeness` в `test_stage4_karakulina.py`, который восстанавливает пропущенные параграфы. Изначально (до 017) он добавлял `paragraph_id` поле, после 017 — `paragraph_ref`.

При разборе кода Claude Opus после v37 прогона выявлено два дефекта:

### Дефект A: Hybrid loop возвращает баг #1 (дубль)

`scripts/test_stage4_karakulina.py:1304`:

```python
pid = el.get("paragraph_ref", "") or el.get("paragraph_id", "")
```

Если LD v3.20 деградирует и эмитит **hybrid элемент** — например `{type: "paragraph", text: "...", chapter_id: "ch_02"}` без `paragraph_ref` и без `paragraph_id` (но с inline `text`):

1. Auto-patch не находит pid (оба поля пустые) → элемент НЕ попадает в `layout_tuples`
2. Считает `(ch_02, p_007)` отсутствующим → дописывает `{paragraph_ref: "p_007", chapter_id: "ch_02"}` на ту же страницу
3. pdf_renderer резолвит ref через `book_FINAL` → выводит тот же текст ещё раз
4. На странице получаем **legacy text + ref-text** — дубль абзаца

То есть возвращается тот же класс багов что в v36 (5 продублированных подглав ch_02), только теперь LD выдаёт текст напрямую, а патч — через ref. Auto-patch как safety net работает корректно **только если LD полностью уходит на refs**. Хотя бы один частичный hybrid-элемент → регрессия #1.

### Дефект B: Счётчик после патча обманывает (читает `paragraph_id`)

`scripts/test_stage4_karakulina.py:1372-1377`:

```python
total_after = len({
    (page.get("chapter_id", "") or el.get("chapter_id", ""), el["paragraph_id"])
    for page in pages
    for el in page.get("elements", [])
    if el.get("paragraph_id")
})
print(f"[LAYOUT-VERIFY] ✅ После патча: {total_after}/{len(all_book_tuples)} абзацев в layout")
```

Использует `el["paragraph_id"]` без чтения `paragraph_ref`. После миграции на v3.20 (где патч-элементы используют `paragraph_ref`) этот счётчик **всегда будет 0** или сильно занижен. Лог показывает «После патча: 0/N» при реально успешном патче — обманывает оператора.

### Почему это не выявил v37 прогон

В v37 LD выдал чистый v3.20-вывод (все элементы с `paragraph_ref`), без hybrid'ов. Поэтому:
- Дефект A не сработал (auto-patch не нашёл «пропусков» которые на самом деле есть в hybrid форме)
- Дефект B показал `0/58` после патча, но прогон прошёл потому что валидатор fidelity (с другим механизмом подсчёта) сказал PASS

То есть оба дефекта были скрыты конкретными условиями v37. Любая итерация с деградацией LD приведёт к проявлению A.

---

## Спек

### Что нужно изменить

**Дефект A — обнаружение hybrid элементов:**

В `verify_and_patch_layout_completeness` добавить детектирование hybrid:

1. Собирая `layout_tuples` (строки 1297-1307), считать «hybrid» элемент с `text` но без `paragraph_ref`/`paragraph_id` как **уже присутствующий в layout** (в каком-то качестве). Поведение на выбор:
   - **(a) hard fail** — вызвать `sys.exit(1)` с сообщением «LD выдал hybrid element без ref/id; book_FINAL сломан или v3.20 не enforce'ится». Это раннее обнаружение проблемы.
   - **(b) warn + skip** — вывести `[LAYOUT-VERIFY] ⚠️ hybrid element обнаружен, layout не v3.20-чистый`. Не дописывать дубль. Прогон продолжается.

   Cursor рекомендует: **hard fail** в production, как часть `verified-on-run` дисциплины. Hybrid элемент — это сигнал что LD регрессировал, лучше остановиться чем выдать подозрительный PDF.

2. Альтернатива: учитывать hybrid элементы в `layout_tuples` через резолвинг `text` обратно к `paragraph_id` через book_FINAL (поиск по точному совпадению text). Слишком хрупко, не делать без явного запроса.

**Дефект B — счётчик после патча:**

Заменить:
```python
if el.get("paragraph_id")
```
на:
```python
if el.get("paragraph_ref") or el.get("paragraph_id")
```

И в выражении ключа аналогично:
```python
el.get("paragraph_ref") or el.get("paragraph_id")
```

### Что НЕ нужно

- Не убирать legacy fallback на `paragraph_id` (legacy support из task 017)
- Не править сам валидатор fidelity — он работает корректно

### Какой результат ожидается

**Verified-on-run сценарий A:**

1. Создать тестовый layout с hybrid элементом: `{type: "paragraph", text: "...", chapter_id: "ch_02"}` (без ref).
2. Прогнать `verify_and_patch_layout_completeness` локально.
3. Если выбран hard fail (a): прогон падает с `sys.exit(1)`.
4. Если warn+skip (b): прогон продолжается с предупреждением, дубль НЕ добавляется.

**Verified-on-run сценарий B:**

1. Создать layout v3.20 с пропущенными параграфами (требующими патча).
2. Прогнать функцию.
3. Лог должен показать корректное `[LAYOUT-VERIFY] ✅ После патча: N/N` (где N — реальное число), не `0/N`.

---

## Ограничения

- [ ] Сохранить legacy support — старые layouts с `paragraph_id` должны работать
- [ ] Сохранить новый формат — v3.20 с `paragraph_ref` должен работать
- [ ] Никаких изменений в самих агентах — только в auto-patch механизме

---

## Dev Review

**Статус:** ✅ выполнен (Cursor · 2026-04-30)

### Диагностика

**Дефект A** (строки 1304, 1302-1307): confirmed. Hybrid элемент (text без ref/id) — не попадает в `layout_tuples` → считается missing → патч добавляет ref → рендерер выводит оба варианта → дубль.

**Дефект B** (строки 1372-1377): confirmed. `el["paragraph_id"]` — KeyError если поля нет, или всегда 0 после миграции на `paragraph_ref`. Итог "0/N абзацев" — misleading.

### [TECH]

Добавлен CLI флаг `--allow-hybrid` (debug) — симметрично `--allow-mismatch` и `--allow-fc-fail`. Hybrid detection добавлен в loop коллекции `layout_tuples`, до patch-логики, что гарантирует early fail перед любыми изменениями layout.

---

## Dev Review Response

**Статус:** ✅ принято

---

## Реализация

**Файл:** `scripts/test_stage4_karakulina.py`

1. **Сигнатура** `verify_and_patch_layout_completeness` — добавлен `allow_hybrid: bool = False`.
2. **Дефект A** — в loop сбора `layout_tuples`: если `type=="paragraph"` И `text` непустой И нет `pid` → добавляем в `hybrid_elements` (описание). После loop: если `hybrid_elements` → hard fail с `sys.exit(1)` или warn (if `allow_hybrid`).
3. **Дефект B** — счётчик после патча: заменён `el["paragraph_id"]` на `el.get("paragraph_ref") or el.get("paragraph_id")`. Теперь корректно считает v3.20 элементы.
4. **Вызовы** (строки 1632 и 2017): оба обновлены с `allow_hybrid=args.allow_hybrid`.
5. **Парсер**: добавлен `--allow-hybrid` аргумент.

---

### Результат verified-on-run (2026-04-30, Cursor)

Тест `scripts/_vr_020_022_023.py`:

```
Тест A — hybrid без --allow-hybrid:
  [LAYOUT-VERIFY] ❌ Обнаружены hybrid элементы (inline text без paragraph_ref): 1 шт.
    ch_02: text='Второй абзац....'
  → sys.exit(1) — PASS

Тест B — hybrid с --allow-hybrid:
  [LAYOUT-VERIFY] ⚠️ Обнаружены hybrid элементы... --allow-hybrid задан — продолжаем
  → Функция вернула результат, не упала — PASS

Тест C — счётчик:
  [LAYOUT-VERIFY] ✅ После патча: 2/2 абзацев в layout
  → (не "0/2") — PASS
```

**Задача 022 PASS.**

---

## Комментарии и итерации

### 2026-04-30 — Даша / Claude

Найдено Claude Opus при разборе кода после прогона v37. Часть batch fix'а из 3 находок (020 / 021 / 022).

---

## История статусов

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-04-30 | `new` | Даша / Claude |
| 2026-04-30 | `dasha-review` | Cursor |
