# Задача: Stage 4 — формализовать границы между gate2c (text-only) и gate3 (с фото)

**Статус:** `done` (v38 verified · 2026-04-30 после фикса 021. Claude локально проверила PDF v38: нет фото-секций на gate2c, manifest.photos_mode корректен.)
**Автор:** Даша / Claude
**Дата создания:** 2026-04-29
**Тип:** `pipeline-orchestration` / код
**Связано:** task 015 (пилот Каракулиной, bug #6), task 009 (протокол ворот приёмки)

---

## Контекст

По протоколу 009 (Acceptance Gates) **gate2c — text-only PDF с плейсхолдерами фото**, **gate3 — реальные фото вместо плейсхолдеров**. Эти этапы должны быть разделены, чтобы:

1. На gate2c проверять текст, вёрстку и структурные блоки **без** влияния качества фото
2. Вносить правки в текст после gate2c **без** перезапуска Photo Editor (он дорогой и долгий)
3. На gate3 фокусироваться на корректности фото-маппинга

### Что выявил пилот Каракулиной v36 (2026-04-29)

PDF gate2c (`karakulina_v36_gate2c_20260429.pdf`) содержит **23 страницы с реальными фото** (стр 31-53, секция «ФОТОГРАФИИ») — то есть Photo Editor запустился, обработал все 23 фото из `exports/karakulina_photos/` и они попали в финальный PDF. Это нарушение разделения gate2c/gate3.

Также по факту: chapter_start страницы получили плейсхолдеры `[ФОТО — начало главы]`, но это потому что Photo Editor подобрал фото только на photo_section в конце, а не на chapter_start. То есть Photo Editor работал не как «отключён», а как «отработал не до конца».

Cursor в отчёте Stage 4 описал команды:
```
python scripts/test_stage4_karakulina.py --acceptance-gate 2a ...
python scripts/test_stage4_karakulina.py --acceptance-gate 2b --existing-layout ... ...
python scripts/test_stage4_karakulina.py --acceptance-gate 2c --existing-layout ... ...
```

То есть флаг `--acceptance-gate` есть, но он не отключает Photo Editor — а должен был на 2a/2b/2c.

---

## Спек

### Системное правило

**`test_stage4_*.py` должен явно различать text-only (gate 2a/2b/2c) и with-photos (gate 3+) режимы.**

Photo Editor запускается **только** в режиме gate 3. На gate 2a/2b/2c — фото подменяются плейсхолдерами на уровне layout.

### Что нужно изменить

1. **`scripts/test_stage4_karakulina.py`** (и общий шаблон, если есть универсальный `test_stage4.py`):
   - При `--acceptance-gate 2a/2b/2c` — Photo Editor не вызывается. На вход Layout Designer идёт **пустой `photos[]`** или `photos[]` с метаданными плейсхолдеров.
   - При `--acceptance-gate 3` — Photo Editor вызывается полноценно, читает `--photos-dir`, выдаёт `photo_assignments.json`.
   - При `--acceptance-gate 4` — Cover Designer вызывается, плюс gate 3 артефакты.

2. **`prompts/15_layout_art_director_v1.8.md`** и **`08_layout_designer_v3.19.md`**:
   - Если на входе photos[] пустой — генерировать плейсхолдеры на chapter_start (`[ФОТО — начало главы]`) и не создавать photo_section в конце.
   - Если photos[] непустой — рендерить реальные фото и photo_section.

3. **Pre-flight check для Stage 4:**
   - На gate 2a/2b/2c: проверить, что Photo Editor НЕ вызывается. Если в код-пути есть его инициализация — fail.
   - На gate 3: проверить, что `--photos-dir` указан и существует.
   - На gate 4: проверить наличие gate 3 артефактов (photo_assignments.json) + наличие портрета для Cover Designer.

4. **Manifest:**
   - В `manifest_s4.json` явный флаг `"photos_mode": "placeholders" | "real"` — для последующего ревью какой gate проходил.

### Какой результат ожидается

На повторном прогоне пилота:
- `python scripts/test_stage4_karakulina.py --acceptance-gate 2c` → PDF содержит **только плейсхолдеры**, никакого photo_section в конце, время прогона короче (нет Photo Editor)
- `python scripts/test_stage4_karakulina.py --acceptance-gate 3 --photos-dir ...` → PDF содержит реальные фото, photo_section с подписями

### Как проверить

```bash
# Прогон gate2c — должно быть быстрее и без фото
python scripts/test_stage4_karakulina.py --acceptance-gate 2c --prefix karakulina_v37
# Verify:
#   - manifest.photos_mode == "placeholders"
#   - В PDF нет страниц "ФОТО 1...23" в конце
#   - Photo Editor не появляется в логах

# Прогон gate3 — Photo Editor запускается, реальные фото в PDF
python scripts/test_stage4_karakulina.py --acceptance-gate 3 \
    --photos-dir exports/karakulina_photos --prefix karakulina_v37
# Verify:
#   - manifest.photos_mode == "real"
#   - В PDF реальные фото на chapter_start и в photo_section
#   - photo_assignments.json создан
```

---

## Ограничения

- [ ] Не сломать совместимость с предыдущими manifest.json (добавить новое поле, не переименовывать существующие)
- [ ] Photo Editor отключение должно быть **в pipeline orchestration**, а не в самом Photo Editor — он остаётся универсальным
- [ ] Решение должно быть universalizable (не Каракулиной-специфичное)
- [ ] При gate 3 без `--photos-dir` — явная ошибка, не silent fallback

---

## Dev Review

**Статус:** заполнено Cursor 2026-04-29

### Диагностика перед реализацией

**Баг подтверждён. Точная точка отказа — `test_stage4_karakulina.py`, строка 1618.**

```python
# Текущий код (строки 1617-1631) — только existing-layout code path:
photos_dir_effective = args.photos_dir
if not photos_dir_effective and args.acceptance_gate in {"2c", "3", "4"}:  # ← BUG: "2c" включён
    _proj_base = PROJECT_ID.split("_stage")[0]
    for _candidate in [
        ROOT / "exports" / f"{_proj_base}_photos",  # ← нашёл /opt/glava/exports/karakulina_photos/
        ...
    ]:
        if _candidate.exists() and any(_candidate.iterdir()):
            photos_dir_effective = str(_candidate)  # ← установлен!
            break
if photos_dir_effective:
    render_cmd += ["--photos-dir", str(...)]  # ← реальные фото переданы рендереру
```

Для gate 2c `args.no_photos = True` (устанавливается строкой 1478), и `--no-photos` добавляется в `render_cmd` (строка 1612). Однако pdf_renderer обрабатывает `--no-photos` только для chapter_start-плейсхолдеров — photo_section в конце книги рендерится если `--photos-dir` передан с непустой директорией. В итоге: `--no-photos` + `--photos-dir` → chapter_start получают плейсхолдеры, но photo_section с 23 реальными фото добавляется в конец PDF.

**Затронут только existing-layout code path** (строки 1617-1631). Основной flow (без `--existing-layout`) использует `args.photos_dir` напрямую (строка 1994) и auto-detect не делает — там проблемы нет.

**Photo Editor как отдельный LLM-агент** (role 07, `07_photo_editor_v1.md`) в скрипте `test_stage4_karakulina.py` **не вызывается вообще** — нет `run_photo_editor()` или аналогичного вызова. «Photo Editor» в описании бага — метафора для описания факта что реальные фото попали в PDF. Технически это не отдельный агент, а поведение pdf_renderer при наличии `--photos-dir`.

**Вывод:** фикс минимальный — убрать `"2c"` из множества в строке 1618.

### [TECH] Технические флаги

**[TECH-1] Единственная точка изменения — одна строка.**
`{"2c", "3", "4"}` → `{"3", "4"}` в строке 1618. Плюс добавить manifest-поле и guard.

**[TECH-2] Для gate 2c нужно явно обнулять photos_dir_effective.**
После фикса строки 1618, при gate 2c `photos_dir_effective = args.photos_dir` (строка 1617). Если пользователь явно передал `--photos-dir` на gate 2c — фото всё равно передадутся рендереру. Нужен дополнительный guard:
```python
# После определения photos_dir_effective:
if args.acceptance_gate in {"2a", "2b", "2c"}:
    if photos_dir_effective:
        print(f"[WARN] gate {args.acceptance_gate}: photos_dir ignored (text-only mode)")
    photos_dir_effective = None
```

**[TECH-3] В основном (non-existing-layout) flow тоже нужен аналогичный guard.**
Строка 1939 передаёт `photos_dir_path=str(...) if args.photos_dir else None` в `run_layout_designer()`. Если пользователь передал `--photos-dir` на gate 2c (явно), Layout Designer получит фото. Нужен guard и там.

**[TECH-4] `photos_mode` в manifest — новое поле.**
Добавить в `save_run_manifest()` вызовах (строки 2342, 2357) поле:
```python
"photos_mode": "real" if photos_dir_effective else "placeholders" if args.acceptance_gate in {"2c"} else "none"
```
Значения: `"none"` (нет photos_dir), `"placeholders"` (gate 2c с пустыми плейсхолдерами), `"real"` (gate 3+, реальные фото).

**[TECH-5] Photo Editor (role 07) не используется в test_stage4_karakulina.py вообще.**
Задача 018 спека описывает «Photo Editor запускается на gate2c». По факту это неверно — реального вызова агента 07 нет. Но семантически проблема аналогична: реальные фото попадают в PDF. Фикс тот же.

### [PRODUCT] Продуктовые флаги

**[PRODUCT-1] Если `--photos-dir` передан явно на gate 2c — игнорировать или ошибка?**
Рекомендация: игнорировать с предупреждением `[WARN]`. Gate semantics имеют приоритет над явным флагом. Альтернатива (raise error) слишком жёсткая — замедлит итерации при copypaste команд.

**[PRODUCT-2] При gate 3 без `--photos-dir` — явная ошибка (уже есть в строке 1575).**
Это уже реализовано: `raise RuntimeError("Ворота 3 требуют реальные фото...")`. Не трогать.

**[PRODUCT-3] При gate 3 с пустой/неполной photos_dir — что делать?**
Текущее поведение: пустая директория → `photos = []` → Layout Designer работает без фото. Это молчаливый fallback. Для gate 3 это некорректно. Нужен дополнительный check: `if not photos: raise RuntimeError("gate 3: photos_dir существует но пуст или manifest отсутствует")`.
Это за рамками задачи 018, но стоит добавить попутно (minor).

**Оценка сложности:** `xs` (2-3 строки кода + manifest поле + guard для явного --photos-dir)
**Оценка риска:** `low` — изменение только в orchestration, не в агентах или рендереле. Легко тестируется.

---

## Dev Review Response

**Статус:** заполнено Claude · 2026-04-29 (TECH автономно, PRODUCT — все разумно, спек-апрув)

### Ответы на [TECH] флаги (Claude, автономно)

**[TECH-1] Единственная точка изменения** ✅ ПРИНИМАЮ.
Минимальный фикс строки 1618 + manifest-поле + guard. Делать вместе.

**[TECH-2] Явное обнуление `photos_dir_effective` для gate 2a/2b/2c** ✅ ПРИНИМАЮ.
Защита от случая когда пользователь руками передал `--photos-dir` на text-only gate. Поведение: warn + ignore (см. ответ на PRODUCT-1 ниже).

**[TECH-3] Аналогичный guard в основном (non-existing-layout) flow** ✅ ПРИНИМАЮ.
Симметричная защита, иначе будет регрессия в основном code path.

**[TECH-4] `photos_mode` поле в manifest** ✅ ПРИНИМАЮ предложенную логику.
Три значения: `none` / `placeholders` / `real`. Используется на пост-ревью «какой режим был на этом прогоне». Зафиксировать в `save_run_manifest()`.

**[TECH-5] Photo Editor (role 07) не вызывается** ✅ ПРИНИМАЮ уточнение.
Хорошо что проверил — спек писал я по визуальному впечатлению PDF, технически проблема не там. Решение те же изменения, но название задачи остаётся корректным («Stage 4 phase boundaries»), потому что **семантика gates** именно про это, не про конкретный агент.

### Ответы на [PRODUCT] флаги (Claude — все разумно, без эскалации Даше)

**[PRODUCT-1] `--photos-dir` явно на gate 2c → warn + ignore** ✅ ПРИНИМАЮ.
Альтернатива «raise error» — слишком жёсткая, замедляет debug-итерации. Warn + ignore оставляет gate semantics приоритетным, не ломает скорость работы. Стандартная политика для конфликтующих флагов.

**[PRODUCT-2] gate 3 без `--photos-dir`** ✅ N/A — уже реализовано.

**[PRODUCT-3] gate 3 с пустой `photos_dir`** ✅ ПРИНИМАЮ — включить попутно в scope 018.
Cursor отметил «за рамками задачи». Я считаю что **в рамках** — это симметричная защита: если уже добавляем guard на gate 2a/2b/2c (защита от лишних фото), то логично добавить и обратное (защита от пустого photos_dir на gate 3). Стоимость минимальная (несколько строк), риск регрессии нулевой. Включаем.

---

**Итог:** `spec-approved`. Все [TECH] и [PRODUCT] закрыты автономно — все ответы технические или с очевидной защитной семантикой. Cursor может приступать к реализации.

Scope расширен на одну строку: PRODUCT-3 (gate 3 с пустой photos_dir → fail) включён в задачу 018 попутно с основным фиксом.

---

## Реализация

**Статус:** реализовано Cursor · 2026-04-29 · `dasha-review`

**Что сделано:**

1. **Фикс auto-detect** (`test_stage4_karakulina.py`, existing-layout path):
   - `{"2c", "3", "4"}` → `{"3", "4"}` в условии авто-обнаружения `photos_dir` (line ~1618)
   - Добавлен explicit guard: если `acceptance_gate in {"2a", "2b", "2c"}` и `photos_dir_effective` не None → `[WARN]` + `photos_dir_effective = None`

2. **Guard в основном (non-existing-layout) flow**:
   - `photos_dir_path` в `run_layout_designer()` теперь всегда `None` для gate 2a/2b/2c
   - `str(Path(args.photos_dir).resolve()) if args.photos_dir and args.acceptance_gate not in {"2a", "2b", "2c"} else None`

3. **`photos_mode` в манифест**:
   - Оба `save_run_manifest()` вызова получили поле `photos_mode`:
     - gate 2a/2b/2c → `"none"`
     - gate 3/4 с `photos_dir` → `"real"`
     - gate 3/4 без `photos_dir` → `"placeholders"`

4. **PRODUCT-3** (gate 3 с пустой photos_dir → fail):
   - Уже реализовано до этой задачи на строке 1575: `if args.acceptance_gate == "3" and not photos: raise RuntimeError(...)`
   - Подтверждено — изменений не требуется.

**Файлы изменены:**
- `scripts/test_stage4_karakulina.py` — 3 места: auto-detect fix, guard, manifest

**Как проверить:**
```bash
# gate 2c с существующим photos-dir → должно напечатать [WARN] и НЕ рендерить реальные фото
python scripts/test_stage4_karakulina.py \
  --acceptance-gate 2c --existing-layout ... --prefix test_v36 \
  --no-photos

# Ожидаемое:
# [WARN] gate 2c: photos_dir проигнорирован (text-only режим). Фото: ...
# photos_mode: "none" в манифесте
```

---

## Комментарии и итерации

### 2026-04-29 — Даша / Claude

Bug #6 из 9 багов пилота Каракулиной. Photo Editor запускается во всех режимах Stage 4, что нарушает разделение gate2c/gate3 и удорожает каждый прогон. Малая по объёму, но важная для скорости итераций задача.

---

## История статусов

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-04-29 | `new` | Даша / Claude |
| 2026-04-29 | `dev-review` (Cursor заполнил диагностику и флаги) | Cursor |
| 2026-04-29 | `spec-approved` (Claude закрыл TECH+PRODUCT автономно; scope расширен на PRODUCT-3) | Claude |
| 2026-04-29 | `dasha-review` (реализация завершена Cursor) | Cursor |
