# v65c sprint — Точечный fix к v65 (дотянуть до PASS Ворот 1)

**Статус:** `new`
**Sprint ID:** v65c (минор, не отдельный sprint plan — узкий fix)
**Автор:** Опус
**Дата создания:** 2026-05-19
**Триггер:** v65 verify (`runs/karakulina-v65-artifacts` @ `8d3dda7`) — НЕ PASS Ворот 1 (−295 chars Total + 3 content blockers); Никитино go на Option A («v65c точечный fix»)
**Связано:** v65 verified-on-run; не trog v66 universality plan

---

## Pre-sprint checklist

- [x] **Stocktake актуален** — `stocktake-2026-05-18-v60-v63.md` + universality-audit-2026-05-19 актуальны
- [x] **Critical reading артефактов v65** выполнено — открыт text_FULL.md, validators_check.json, посчитан build_gate1 Total = 19 705 (НЕ 24 111 file_size!)
- [x] **Universality построчно** — этот sprint scripted+pin-list edit, без prompt-bumps; universality preserved
- [x] **Защита подключена к лечению** — да, hints передаются через revision pass который уже работает
- [x] **Прогон раздельный (Правило 7)** — v65c = ОДИН revision pass + Stage 3 на текущем revised v65 book, не retry Stage 1+2. Узкий bugfix известного эффекта → combined OK
- [x] **Класс багов, не симптом** — Капошвара (Class 1 entity drift recurring), баба Аня (Class 5 regression recurring), дача year (year_direction mechanism bug)
- [x] **Скрипт-first** — pin-list edit + revision hints, никаких prompt-bumps

---

## Контекст

v65 verified: 19 705 / 20 000 chars build_gate1 Total (−295). 3 real content blockers + 4 validator pattern false negatives.

**v65c — узкий fix**, не новый sprint:
- НЕ retry Stage 1+2 (Stage 1+2 outputs OK)
- Используем **текущий revised book** (`karakulina_book_FINAL_1779175986_revised.json`)
- Запускаем ОДИН дополнительный revision pass GW v2.24 с 3-4 точечными hints + Stage 3 + build_gate1

**Validator pattern bugs (false negatives)** — НЕ исправляем в v65c. Они НЕ блокируют PASS (real content OK). Закроем в v66a/b/c universality sprint вместе с другими validator updates.

---

## Универсальность принципов (verification)

- ✅ Лес/деревья: 3 точечных fixes на 3 разных class regressions (Class 1 + Class 5 + year_direction mechanism)
- ✅ Универсальность: pin-list edit Каракулино-specific (правильно), но **mechanism** universal (entity_substitution, narrative_required, year_direction)
- ✅ Класс багов: Капошвара = Class 1 recurring; баба Аня = Class 5 narrative_required; дача = year_direction enforcement
- ✅ Скрипт-first: scripted hints + pin-list edit, NO prompt change
- ✅ Логирование: после v65c verify → run_registry v6 секция `## v65c`
- ✅ Медленные шаги: 1 revision pass + Stage 3, минимум change
- ✅ НЕ экономим: $1-2 за дополнительный revision pass + Stage 3 (acceptable per Правило 7 для узкого fix)

---

## 3 точечных fixes для v65c

### Fix 1 — Капошвара улица → площадь (Class 1 entity drift, recurring 3-й sprint)

**Проблема:** v65 text lines 173, 239, 245 — «на улицу Капошвара» (3 раза). Pin-list v6 ep_028 правильно говорит «площадь Капошвара». validate_entity_substitution либо не подключён к revision_hints, либо не имеет pattern.

**Fix:** в revision_hints добавить explicit hint:
```yaml
hint_id: c_001
validator: entity_substitution
category: place_misnaming_kaposhvara
chapter_ids: [ch_02, ch_03, ch_04, epilogue]
severity: error
snippets:
  - "на улицу Капошвара"  # line 173, 239, 245
  - "улицу Капошвара"
  - "улиц[а-я]+ Капошвар"
suggestion: "Заменить 'улица Капошвара' → 'площадь Капошвара' (TR2 + pin-list ep_028 явно указывает площадь). Это Class 1 named entity drift, recurring 3 sprints."
must_apply: true
```

Также добавить в `narrative_stop_phrases.json` v8 либо в `entity_substitution_<subject>.json` (если создан в v66b) — pattern `улиц\w+\s+Капошвар` → error + auto-replacement suggestion.

### Fix 2 — Баба Аня в narrative ch_03 (Class 5 narrative_required regression, recurring 3-й sprint)

**Проблема:** Pin-list v6 relation_overrides отмечает баба Аня как `narrative_required: true`. В v65 narrative — 0 mentions «Баба Аня» / «французская бабушка». Required_episodes_coverage validator должен это flag'ить — но баба Аня не в `episodes`, она в `relation_overrides` (через task 044i mechanism). Mechanism `narrative_required_persons` либо не реализован, либо hint не сгенерирован.

**Fix:** в revision_hints добавить explicit hint:
```yaml
hint_id: c_002
validator: narrative_required_persons
category: required_person_missing
chapter_id: ch_03
severity: error
snippet: null  # chapter-level
suggestion: "Добавить упоминание 'Баба Аня' в ch_03 как «французская бабушка» comparison (TR2 эпизод сравнения свекрови рассказчика с другими бабушками). Pin-list v6 relation_overrides помечает её narrative_required: true. См. эпизод TR2: 'сравнить отношения бабы Ани, да, к тебе'."
must_apply: true
```

NB: chapter-level hint, audit_revision_diff может flag как unauthorized_change (известный bug v65) — в v65c **поднять threshold до 30** для этого прогона; audit fix → v66.

### Fix 3 — Дача год: «1990-е» → «до 1990-х» (year_direction mechanism enforcement)

**Проблема:** v65 lines 241, 356 — «В 1990-е годы семья продала дачу». Pin-list v6 ep_029 имеет `year_direction: before_1990s` + `year_hint: "НЕ ПИСАТЬ '1990-е'"`. GW проигнорировал.

**Fix:** в revision_hints добавить:
```yaml
hint_id: c_003
validator: pin_list_year_direction_drift  # новый validator либо через narrative_stop_phrases
category: year_direction_violation
chapter_ids: [ch_03, ch_04]
severity: error
snippets:
  - "В 1990-е годы семья продала дачу"
  - "Когда в 1990-е годы семья продала дачу"
suggestion: "ep_029 'Продажа дачи' помечено в pin-list v6 как 'before_1990s' (Никитин уточнение — раньше). НЕ ПИСАТЬ '1990-е годы'. Заменить на: 'В 1980-е семья продала дачу' либо 'Семья продала дачу — до этого Валентина любила там возиться' (без attribution года). Сохранить sentence про тётю Машу + сожаление."
must_apply: true
```

### Fix 4 (опционально, если depth low) — развернуть pin-list depth ep_003/011/016/024

**Проблема:** Pin-list depth 4 errors:
- ep_003 призыв 1941: 1 sentence (нужно ≥3)
- ep_011 операция желудок 1960: 2 sentences
- ep_016 поликлиника: 1 sentence
- ep_024 огурцы Молдавия: 2 sentences

**Fix:** в revision_hints добавить hint per episode (если в текущем revision pass хочешь развернуть):
```yaml
hint_id: c_004 (один общий либо c_004..c_007)
validator: pin_list_depth
category: pin_list_event_below_min_depth
chapter_id: ch_02 (либо ch_04 для ep_024)
severity: error
suggestion: "Развернуть pin-list events ep_003/011/016/024 до ≥3 sentences per ПРАВИЛО 12. Не дублировать существующий narrative — добавить деталь из source_quote либо historical context."
must_apply: true
```

Это **возможно прибавит +500-800 chars** → close gap до 20K target.

---

## Реализация

### Какие файлы trog

1. **Создать** `scripts/_v65c_revision_pass.py` (или extend `_v65_revision_pass.py`):
   - Загрузить `karakulina_book_FINAL_1779175986_revised.json` (текущий revised book)
   - Сформировать 3-4 hints (Fix 1+2+3, опционально +4)
   - Передать в GW v2.24 second revision pass
   - Output: `karakulina_book_FINAL_v65c_revised.json`

2. **Audit threshold** — поднять до 30 для этого прогона (chapter-level hints) либо отметить known limitation. v66a fix proper.

3. **Stage 3 на v65c revised book** — LE + Proofreader + post-processing + preserve_writing_notes (049g) + final validators + build_gate1.

4. **Push артефактов** в **существующую** ветку `runs/karakulina-v65-artifacts` (новый commit поверх `8d3dda7`).

### Что НЕ trog

- ❌ Stage 1 + Stage 2 (используем existing outputs)
- ❌ GW v2.24 prompt (используем existing — это revision pass второй, не новый bump)
- ❌ Validator pattern bugs (закроется в v66 universality, не блокер для PASS)
- ❌ Audit_revision_diff fix (v66 backlog, threshold workaround для v65c)
- ❌ Любые новые правила или новые validators
- ❌ Pin-list v7 changes (existing v6 уже OK для этих hints)

---

## Targets для v65c

После revision pass + Stage 3:

| Metric | v65 | v65c target |
|--------|-----|-------------|
| Total chars build_gate1 | 19 705 | **≥ 20 000** |
| Капошвара | улица (3 mentions) | площадь (3 mentions) |
| Баба Аня в ch_03 | ❌ missing | ✅ present как «французская бабушка» |
| Дача year | «1990-е» (2 mentions) | без «1990-е» либо «до 1990-х» |
| Pin-list depth errors | 4 | ≤ 2 (acceptable improvement) |
| Chronology errors | 0 | 0 (не regress) |
| writing_notes.rule13 preserved | ✅ | ✅ |
| Все validators v65 PASS (real content) | mixed | при PASS все real OK |

---

## Risk + mitigation

**Risk A:** Revision pass v65c добавит unauthorized changes → STOP audit. **Mitigation:** threshold up до 30 + chapter-level hint flag.

**Risk B:** GW v2.24 revision pass не закроет один из 3 fixes (например игнорирует hint). **Mitigation:** must_apply=true для всех 3 + после verify Опус откроет text_FULL.md и проверит каждый. Если 1 из 3 не закрылся — v65d узкий fix либо tag RP-1 на v65c.

**Risk C:** Depth fix (4) не сработает. **Mitigation:** опционально — если revision GW короткий, депth ep_003/011/016/024 могут остаться. Acceptable для PASS если Total ≥ 20K (через Fix 4 либо через депth other paths).

---

## Финансово v65c

**$1-2 один revision pass + Stage 3** (без Stage 1+2 retry). Чистый bugfix.

---

## Когда v65c готов

1. Verified-on-run от Курсора + push артефактов в `runs/karakulina-v65-artifacts` (commit поверх `8d3dda7`)
2. **Опус откроет text_FULL.md независимо** — verify все 3 fixes + Total ≥ 20K + Капошвара = площадь + баба Аня present + дача без 1990-е
3. **Опус обновит run_registry v6** секцией `## v65c`
4. Если PASS Ворот 1 (все 3 fixes + Total ≥ 20K) → **tag RP-1** → v66a universality refactor sprint
5. Если 1+ fix не закрылся → решение Никиты (v65d либо tag RP-1 с known issue)

---

## История

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-19 | `new` | Опус |
