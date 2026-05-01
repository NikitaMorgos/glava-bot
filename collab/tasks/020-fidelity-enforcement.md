# Задача: validate_layout_fidelity — hard fail вместо warn-only в основном flow

**Статус:** `done` (v38 verified · 2026-04-30. Unit-test PASS, fidelity на v38 PASS, 73 абзаца порядок OK.)
**Дата создания:** 2026-04-30
**Тип:** `код` / `enforcement`
**Связано:** task 017 (ссылочная архитектура), task 019 (verification run где это всплыло)

---

## Контекст

В рамках task 017 был создан валидатор `scripts/validate_layout_fidelity.py` с тремя проверками (completeness / order / uniqueness) и интегрирован в `test_stage4_karakulina.py`.

Спека 017 явно требовала: «при нарушении — `sys.exit(1)` с детальным отчётом» и «по умолчанию hard fail».

При разборе кода Claude Opus после прогона v37 обнаружено что в основном flow валидатор вызывается, но **результат не используется для блокировки прогона**.

### Доказательство в коде

`scripts/test_stage4_karakulina.py:1985-1994`:

```python
layout_result = verify_and_patch_layout_completeness(layout_result, book_final)

# Валидация соответствия layout ↔ book_FINAL: completeness, order, uniqueness (задача 017)
try:
    from validate_layout_fidelity import validate_fidelity as _vf
    _passed_fid, _ferrors = _vf(layout_result, book_final, allow_mismatch=False)
    if not _passed_fid:
        print(f"[FIDELITY] ❌ Нарушения fidelity. Используй --allow-mismatch для обхода.")
except ImportError:
    pass
```

Никакого `sys.exit(1)`, `raise`, или возврата с ненулевым exit code. Сообщение «используй --allow-mismatch для обхода» вводит в заблуждение — обходить нечего, прогон и так идёт дальше.

### Почему это не выявил v37 прогон

В v37 LD не сделал ошибок (validate_fidelity вернул PASS), поэтому ветка `if not _passed_fid` не сработала. Прогон прошёл «зелёно» по случайности, не потому что enforcement работает.

### Симметричный case в existing-layout flow

В `test_stage4_karakulina.py:1605-1609` (existing-layout path) логика **по дизайну** warn-only с `allow_mismatch=True` — это нормально, там пользователь явно переиспользует уже сохранённый layout и ожидает мягкое поведение.

Проблема **только в основном flow**.

---

## Спек

### Что нужно изменить

В `scripts/test_stage4_karakulina.py` строки **1989-1994** (основной flow после `verify_and_patch_layout_completeness`):

После успешного импорта `validate_fidelity`:
- Если `_passed_fid is False` и **флаг `--allow-mismatch` не передан** — `sys.exit(1)` с детальным выводом ошибок (`_ferrors`).
- Если `_passed_fid is False` и `--allow-mismatch` передан — `print` warn + продолжать (как сейчас).
- Если `_passed_fid is True` — `print [FIDELITY] ✅` и продолжать.

`ImportError` ветка должна **тоже** быть отчётливой: если пользователь вызвал прогон без модуля валидатора, это не silent skip — это `print [FIDELITY] ⚠️ validate_layout_fidelity.py не найден, валидация пропущена`. По умолчанию это допустимо (для обратной совместимости со старыми чекаутами), но Cursor может предложить ужесточить.

### Что НЕ нужно

- Не трогать existing-layout path (1605-1609) — там warn-only by design.
- Не менять сам валидатор — он работает корректно, проблема в use site.
- Не делать точечный фикс «только для Каракулиной» — это универсальное правило.

### Какой результат ожидается

После фикса локальный тест:
1. Создать заведомо битый layout (с дублирующимся paragraph_ref).
2. Прогнать `test_stage4_karakulina.py` без `--allow-mismatch`.
3. Прогон должен **упасть** с exit code 1 на `[FIDELITY] ❌ ...` сообщении.
4. С `--allow-mismatch` — продолжать с warn.

Этот тест **обязательно** прогнать перед закрытием задачи (новый принцип `verified-on-run`).

---

## Ограничения

- [ ] Сохранить флаг `--allow-mismatch` для debug-режима — не убирать его
- [ ] Сообщение об ошибке должно содержать список нарушений (`_ferrors`), не только «есть ошибки»
- [ ] Не ломать обратную совместимость с existing-layout flow

---

## Dev Review

**Статус:** ✅ выполнен (Cursor · 2026-04-30)

### Диагностика

Подтверждено: `test_stage4_karakulina.py:1989-1994` — `validate_fidelity` вызывается, `if not _passed_fid` только печатает, нет `sys.exit`. Существующий-layout path (1605-1609) с `allow_mismatch=True` — by design, не трогаем.

### [TECH]

Добавлен CLI флаг `--allow-mismatch` (линия 1438). `ImportError` теперь печатает предупреждение вместо silent pass. Список `_ferrors` выводится при fail.

---

## Dev Review Response

**Статус:** ✅ принято

---

## Реализация

**Файл:** `scripts/test_stage4_karakulina.py`

1. Добавлен аргумент `--allow-mismatch` в parser (строка ~1438).
2. Блок fidelity (строки ~1990-2006): если fail и `--allow-mismatch` → warn + список ошибок + продолжаем. Если fail и без флага → `sys.exit(1)` с детальным выводом. Если pass → `[FIDELITY] ✅`. `ImportError` → явное предупреждение.

**Verified-on-run:** прогон с заведомо битым layout (дубль paragraph_ref) должен упасть с exit code 1. С `--allow-mismatch` — продолжать с warn.

---

### Результат verified-on-run (2026-04-30, Cursor)

Тест `scripts/_vr_020_022_023.py`:

```
[ERROR] [UNIQUENESS] ch_02/p2 — встречается 2 раза (дубль)
[ERROR] [COMPLETENESS] ch_02/p3 — отсутствует
validate_fidelity: passed=False, 3 ошибки
Тест A (без --allow-mismatch): sys.exit(1) сработал — PASS
Тест B (с --allow-mismatch): предупреждение, прогон продолжился — PASS
```

**Задача 020 PASS.**

---

## Комментарии и итерации

### 2026-04-30 — Даша / Claude

Найдено Claude Opus при разборе кода после прогона v37. Подтверждено Claude в коде. Часть batch fix'а из 3 находок (020 / 021 / 022).

---

## История статусов

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-04-30 | `new` | Даша / Claude |
| 2026-04-30 | `dasha-review` | Cursor |
