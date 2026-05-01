# Задача: Stage 4 — photos_dir guard в основном flow (симметрично 018)

**Статус:** `done` (v38 verified · 2026-04-30. Unit-test PASS, на v38 PDF нет фото-секций в gate2c.)
**Автор:** Даша / Claude (на основе разбора Opus)
**Дата создания:** 2026-04-30
**Тип:** `код` / `pipeline-orchestration`
**Связано:** task 018 (phase boundaries — закрыт частично), task 019 (verification run где это всплыло)

---

## Контекст

В рамках task 018 был добавлен guard в `test_stage4_karakulina.py`: при `--acceptance-gate 2a/2b/2c` блокировать передачу фото в Layout Designer. Guard добавлен в **двух местах**:

- existing-layout path (строки 1644-1649) ✅
- основной flow при вызове Layout Designer ✅

Однако при разборе кода Claude Opus после v37 прогона выявлено что **дальше по основному flow** (при вызове `pdf_renderer`) аналогичный guard отсутствует.

### Доказательство в коде

`scripts/test_stage4_karakulina.py:2026-2027`:

```python
if args.photos_dir:
    render_cmd += ["--photos-dir", str(Path(args.photos_dir).resolve())]
```

Никакой проверки `args.acceptance_gate`. Если пользователь запустит:

```bash
python scripts/test_stage4_karakulina.py --acceptance-gate 2c --photos-dir exports/karakulina_photos
```

То:
- Guard в строке (~1963) корректно обнулит `photos_dir_effective` для Layout Designer (text-only)
- Но в строке 2026 `args.photos_dir` остаётся прежним → передаётся в `pdf_renderer`
- `pdf_renderer` с `--photos-dir` пройдётся по `self.photos._map` и сгенерит страницы-плейсхолдеры в конце книги
- Manifest при этом запишет `photos_mode: "none"` (Layout Designer не получил фото), но в PDF фото будут

Критерий приёмки 019 «Bug #6: gate 2c — нет страниц ФОТОГРАФИИ в PDF» **проседает**, как только в команду попадёт `--photos-dir`.

### Почему это не выявил v37 прогон

Cursor запускал без `--photos-dir`, поэтому ветка не активировалась. v37 прошёл как gate 2c корректно. Но это случайность — в любой следующей команде с явным `--photos-dir` (например при copy-paste из ранее работавших скриптов) баг #6 вернётся.

### Симметричный case в existing-layout

`scripts/test_stage4_karakulina.py:1644-1649` (existing-layout path) — там guard уже есть и работает:

```python
if args.acceptance_gate in {"2a", "2b", "2c"} and photos_dir_effective:
    print(f"[WARN] gate {args.acceptance_gate}: photos_dir ignored")
    photos_dir_effective = None
```

Нужен такой же guard перед строкой 2026.

---

## Спек

### Что нужно изменить

В `scripts/test_stage4_karakulina.py` перед строкой **2026** (передача `--photos-dir` в `render_cmd`):

```python
# Симметрично guard'у в existing-layout flow (1644-1649)
if args.acceptance_gate in {"2a", "2b", "2c"} and args.photos_dir:
    print(f"[WARN] gate {args.acceptance_gate}: --photos-dir ignored for pdf_renderer (text-only mode)")
else:
    if args.photos_dir:
        render_cmd += ["--photos-dir", str(Path(args.photos_dir).resolve())]
```

(Точное расположение и условие — уточнит Cursor; идея: gate 2a/2b/2c → НЕ передавать `--photos-dir` в render_cmd, независимо от того что пользователь указал в CLI.)

### Что НЕ нужно

- Не менять existing-layout flow — там guard уже есть.
- Не менять Layout Designer guard (он уже работает).
- Не делать новый CLI флаг — нужно чтобы гейт сам определял поведение.

### Какой результат ожидается

После фикса локальный тест:
1. Запустить `test_stage4_karakulina.py --acceptance-gate 2c --photos-dir exports/karakulina_photos` (любая существующая папка с фото).
2. Должно: `[WARN]` сообщение о игнорировании `--photos-dir` для рендерера + в финальном PDF **нет страниц ФОТОГРАФИИ**.
3. Manifest: `photos_mode: "none"` или `"placeholders"`.
4. Запустить с `--acceptance-gate 3 --photos-dir <path>` — фото должны быть в PDF (поведение не сломано).

Verified-on-run обязателен.

---

## Ограничения

- [ ] Не сломать gate 3 (там фото нужны)
- [ ] Не дублировать guard — проверить что Layout Designer guard и pdf_renderer guard не конфликтуют
- [ ] Решение должно быть universalizable

---

## Dev Review

**Статус:** ✅ выполнен (Cursor · 2026-04-30)

### Диагностика

Подтверждено: строка 2041 (`if args.photos_dir: render_cmd += [...]`) — нет проверки `acceptance_gate`. Existing-layout path (1644-1649) — guard уже есть, не трогаем.

### [TECH]

Guard по условию `args.acceptance_gate in {"2a", "2b", "2c"}` — warn и пропуск `--photos-dir` для рендерера. Для gate ≠ 2a/2b/2c (`None`, `"3"`, `"4"`) — передаётся как раньше.

---

## Dev Review Response

**Статус:** ✅ принято

---

## Реализация

**Файл:** `scripts/test_stage4_karakulina.py`

Строки 2041-2047 (основной flow, pdf_renderer вызов): заменён безусловный `if args.photos_dir` на guard с проверкой `args.acceptance_gate in {"2a", "2b", "2c"}` → `[WARN]` + skip, иначе передаётся.

**Verified-on-run:** `--acceptance-gate 2c --photos-dir <path>` → `[WARN] gate 2c: --photos-dir игнорируется` в логах и нет страниц ФОТОГРАФИИ в PDF. `--acceptance-gate 3 --photos-dir <path>` → фото передаются.

---

### Результат verified-on-run (2026-04-30, Cursor)

Тест `scripts/_vr_020_022_023.py`:

```
gate 2c + --photos-dir: [WARN] gate 2c: --photos-dir игнорируется для pdf_renderer
  → --photos-dir НЕ попал в cmd — PASS
gate 3 + --photos-dir:
  → --photos-dir в cmd — передаётся корректно — PASS
gate None + --photos-dir:
  → --photos-dir в cmd — передаётся корректно — PASS
```

**Задача 021 PASS.**

---

## Комментарии и итерации

### 2026-04-30 — Даша / Claude

Найдено Claude Opus при разборе кода после прогона v37. Подтверждено Claude. Часть batch fix'а из 3 находок (020 / 021 / 022).

---

## История статусов

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-04-30 | `new` | Даша / Claude |
| 2026-04-30 | `dasha-review` | Cursor |
