# Задача 041b: Stage 1 CA — обязательная подача pin-list events (фикс реализации task 041)

**Статус:** `new`
**Номер:** 041b
**Автор:** Опус (роль архитектор+продакт)
**Дата создания:** 2026-05-17
**Тип:** `cco-скрипт` + Stage 1 runner config
**Batch:** 2-fix (после v58 verified)
**Связано:** task 035, task 041; **diagnostic v58**: CA auto_enrich пропустил огурцы/шубу/ложечки которые были в v56

---

## Контекст

Diagnostic v58 fact_map выявил: CA `auto_enrich.timeline` содержит **только 10 events** (vs v56: 12). Пропущены **огурцы**, **шуба→пианино**, **мельхиоровые ложечки** — все они в v56 были как `event_auto_*` и попали в book. В v58 они **отсутствуют в fact_map** → GW не мог развернуть.

**Корень:** Stage 1 runner не подал в CA pin-list events (через `--known-episodes` или `--prev-fact-map`). CA свободно выбирал что extract → пропустил TR2-эпизоды.

Парсер pin-list (task 041) — **работает корректно**. Markers извлекаются, GW input должен получать pin-list. Но если **в fact_map нет огурцов**, GW не может развернуть, как бы pin-list не настаивал.

Это **fix Stage 1 runner config**, не парсер.

---

## Спек

### Что нужно изменить

**1. `scripts/test_stage1_karakulina_full.py`**:
- Добавить обязательный параметр `--known-episodes` или (если не передан) автоматически прочитать `collab/context/known_episodes_<subject>.md`
- Передать в Completeness Auditor через `previous_run_fact_map_or_known_episodes` (как описано в `pipeline_utils.py:1040`)
- Pin-list events из `episodes[]` секции pin-list — обязательно проверить как gap в `log_only_gaps` или auto_enrich

**2. `scripts/test_stage1_<any_subject>_full.py`** (если есть/будет):
- Тот же flow — подставляется subject_id из manifest, читается `known_episodes_<subject>.md`

**3. Verify в Stage 1 manifest output**:
- В `<run>_stage1_full_run_manifest.json` зафиксировать поле `pin_list_used: <path>` + `pin_list_episodes_count`
- На пустой pin-list — warning в manifest

### Какой результат ожидается

В v59 Stage 1 manifest:
- `pin_list_used: "collab/context/known_episodes_karakulina.md"`
- `pin_list_episodes_count: 30+`

В v59 fact_map.timeline через auto_enrich:
- ✅ event_auto про огурцы (восстановлен из pin-list)
- ✅ event_auto про шубу → пианино (с указанием года 1962 из pin-list, не «1990» как v56 CA выдумывал)
- ✅ event_auto про мельхиоровые ложечки
- ✅ event_auto про шарлотку, карты/домино, грибы/ягоды (если в TR есть)

CA `was_in_pin_list` флаг проставляется корректно для всех pin-list эпизодов.

### Как проверить

1. **Unit-тест** `tests/test_stage1_pin_list_required.py`:
   - Runner без `--known-episodes` → автозагрузка из конфига
   - Runner с pin-list → CA получает его как input
   - Pin-list events с маркерами в TR → попадают в auto_enrich.timeline
   - Pin-list events с маркерами **не в TR** → в `log_only_gaps.missing_events` с reason

2. **Integration** на v58 transcripts:
   - Запустить Stage 1 с обязательным pin-list
   - Проверить fact_map.timeline ≥15 events (vs v58: 41 total, но многие fact-extracted без auto_enrich)
   - Огурцы / шуба / ложечки — в auto_enrich

3. **Verified-on-run** v59:
   - Открыть `karakulina_v59_stage1_full_run_manifest.json` → `pin_list_used` указан
   - Открыть `karakulina_v59_fact_map_full.json` → присутствуют event_auto про огурцы (id, title, source_quote)

---

## Ограничения

- [ ] НЕ менять промпт CA (это task 038b отдельно)
- [ ] Если subject не имеет `known_episodes_<subject>.md` файла → warning, не fail
- [ ] Universal: pin-list per subject, без hardcoded Каракулиной
- [ ] Idempotent

---

## Dev Review

**Статус:** ожидает

**[TECH]** — пред-резолв: pin-list пишется generic для любого subject через `collab/context/known_episodes_<subject>.md` — Stage 1 runner ищет файл по subject_id из manifest.

**[PRODUCT]** — нет.

**Сложность:** `xs` (<1 ч)
**Риск:** `low`

---

## История

| Дата | Статус | Кто |
|---|---|---|
| 2026-05-17 | `new` | Опус |
