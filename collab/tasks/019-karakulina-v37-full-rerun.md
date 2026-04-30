# Задача: Полный перепрогон пилота Каракулиной v37 — верификация фиксов 016, 017, 018 и промпт-патчей

**Статус:** `new` → `in-progress` (Cursor · 2026-04-30)
**Номер:** 019
**Автор:** Даша / Claude
**Дата создания:** 2026-04-30
**Тип:** `прогон` / `верификация`
**Связано:** task 015 (трекер пилота), tasks 016/017/018 (закрытые системные фиксы), CHANGELOG `[2026-04-29]` (промпт-патчи Claude)

> Это **верификационный прогон**, не разработка. Цель — проверить что 9 багов из задачи 015 действительно закрыты после всех фиксов. Если найдутся новые баги — это материал для следующих системных задач.

---

## Цель

Прогнать полный пайплайн на каракулинских транскриптах с нуля (Stage 1 → 2 → 3 → 4 gate2c) и **визуально проверить PDF**. Сравнить с baseline v36 — те же 9 багов не должны воспроизвестись.

Прогон делается на **новой версии v37**, без переиспользования v36 артефактов (кроме входных транскриптов).

---

## Что будет проверяться

### 9 багов из задачи 015

| # | Bug | Где должен закрыться | Как проверить |
|---|-----|---------------------|---------------|
| 1 | Дубль 5 подглав ch_02 | task 017 (ссылочная архитектура) | `validate_layout_fidelity.py` — uniqueness check; визуально в PDF |
| 2 | Перетасовка ch_03 + пропуск подглавы | task 017 | то же — order check |
| 3 | Текст на chapter_start страницах | патч промптов Claude (LD v3.20 + AD) | визуально в PDF |
| 4 | Дыры между подглавами | патч промптов Claude (LD v3.20 + AD) | визуально в PDF |
| 5 | Подписи фото = filename | патч промптов Claude (Photo Editor + LD) | визуально в PDF (gate 3, не gate 2c) |
| 6 | Photo Editor запустился в gate 2c | task 018 (phase boundaries) | `manifest.photos_mode == "placeholders"` на gate 2c; нет photo_section в PDF |
| 7 | Поля отсутствует в bio_data.family | патч промпта GW v2.14 (bio_data completeness rule) | в book_FINAL chapters[0].bio_data.family есть Полина |
| 8 | Cross-person aliases pollution (Полина/Пелагея/Марфа) | task 016 (semantic guard) | в fact_map_full_v37 у person_004 aliases без «Рудая Пелагея» / «Марфа» / «Дуня» |
| 9 | Семантические галлюцинации GW (огурцы → 90-е) | **НЕ закрыт** (task 016 Narrative Auditor отложен) | known issue, остаётся в pipeline до конца пилота |

### Дополнительная проверка стабильности (как в task 014)

Запустить Stage 1 **дважды** на одних и тех же транскриптах (v37a, v37b), потом `compare_persons_across_runs.py` — stability_score ≥ 90%.

---

## Команды (предположительно — Cursor подтверждает по фактическому API)

```bash
# === STAGE 1 — двойной прогон для проверки стабильности ===
python scripts/test_stage1_karakulina_full.py --output v37a
python scripts/test_stage1_karakulina_full.py --output v37b

python scripts/compare_persons_across_runs.py \
    --run-a collab/runs/karakulina_v37/karakulina_fact_map_full_v37a.json \
    --run-b collab/runs/karakulina_v37/karakulina_fact_map_full_v37b.json \
    --output collab/runs/karakulina_v37/v37_stability_report.json

# === STAGE 2 — на чистом v37a fact_map ===
python scripts/test_stage2.py \
    --fact-map collab/runs/karakulina_v37/karakulina_fact_map_full_v37a.json \
    --output v37 --prefix karakulina

# gate1 чек после Stage 2
python scripts/run_gate1_check.py --book exports/.../book_FINAL_stage2.json

# === STAGE 3 ===
python scripts/test_stage3.py \
    --book-draft exports/.../book_FINAL_stage2.json \
    --fact-map collab/runs/karakulina_v37/karakulina_fact_map_full_v37a.json \
    --output v37 --prefix karakulina

# === STAGE 4 — gate 2c (text-only с плейсхолдерами) ===
python scripts/test_stage4_karakulina.py --acceptance-gate 2c --prefix karakulina_v37
# Должно: photos_mode == "placeholders", validate_layout_fidelity PASS, нет photo_section в PDF

# === Дополнительно: проверка валидатора ===
python scripts/validate_layout_fidelity.py \
    --layout exports/.../karakulina_v37_layout.json \
    --book exports/.../book_FINAL_stage3_v37.json
# Ожидается: PASS
```

---

## Критерии приёмки (когда задача → `done`)

**Обязательные (closures):**

- [ ] Stage 1 двойной прогон → stability_score ≥ 90%
- [ ] Bug #8: в v37 fact_map у person_004 (Полина) aliases НЕ содержат «Рудая Пелагея Алексеевна», «Марфа», «Дуня»
- [ ] Bug #8 logs: rejected_pairs_log в нормализаторе содержит запись о попытке слияния Полины и Пелагеи (которая была заблокирована по relation_group_mismatch)
- [ ] gate1 PASS на v37 book_FINAL_stage3
- [ ] Bug #7: в v37 book_FINAL.chapters[0].bio_data.family есть Полина (с релевантным label «Сестра» / «Старшая сестра» / etc.)
- [ ] Bug #6: на gate 2c manifest.photos_mode == "placeholders"; в PDF нет страниц «ФОТОГРАФИИ» в конце
- [ ] Bug #1, #2: validate_layout_fidelity.py PASS (completeness + order + uniqueness)
- [ ] Bug #3, #4: визуальный просмотр PDF — chapter_start страницы без текста, нет дыр между подглавами

**Опционально (nice-to-have):**
- [ ] Подсчёт стоимости и времени прогона (vs v36)
- [ ] Сравнение размера layout.json (должен сильно упасть после ссылочной архитектуры)

**Что делать если что-то не прошло:**
- Если новый баг — фиксировать в комментариях этой задачи + при необходимости заводить новую системную задачу (016/017/018 показали как)
- НЕ делать точечных правок fact_map / book_FINAL / layout (нарушение принципа из 015)

---

## Артефакты на выходе

Должны быть в `collab/runs/karakulina_v37/`:

- `manifest_s1_v37a.json` / `manifest_s1_v37b.json`
- `karakulina_fact_map_full_v37a.json` / `_v37b.json`
- `karakulina_completeness_audit_v37a.json` / `_v37b.json`
- `karakulina_normalization_log_v37a.json` (включая rejected_pairs)
- `v37_stability_report.json`
- `manifest_s2_v37.json`
- `book_FINAL_stage2_v37.json`
- `gate1_v37.json`
- `manifest_s3_v37.json`
- `book_FINAL_stage3_v37.json`
- `manifest_s4_v37.json` (с photos_mode)
- `karakulina_v37_layout.json`
- `karakulina_v37_layout_fidelity.json`
- `karakulina_v37_gate2c.pdf` ← главный артефакт для визуального ревью

---

## Бюджет

Ориентировочно ~$2-3 (двойной Stage 1 + одиночный Stage 2/3 + Stage 4 без LLM-вызовов после фикса 018). Время ~15-20 минут.

Если что-то ломается на первом прогоне — **остановиться, не делать второй**, написать в комментарий что произошло.

---

## Dev Review

> Это прогон, не разработка кода. Cursor может проверить что команды актуальные и нет mismatch с реальным API скриптов, прежде чем стартовать.

**Статус:** `in-progress` (Cursor проверил API и стартует прогон · 2026-04-30)

### Технические замечания перед прогоном

**Несоответствия в предложенных командах (исправлено перед запуском):**

1. **Stage 1** — флага `--output` нет; правильный: `--output-dir <path>`. Запускаем с `--output-dir /opt/glava/exports/karakulina_v37a` и `_v37b`.

2. **`run_gate1_check.py`** — такого скрипта нет. Gate1 (`run_stage2_text_gates`) запускается автоматически внутри `test_stage2_pipeline.py` и результат сохраняется в manifest. Отдельная команда из задачи убрана.

3. **Stage 2** — флаги `--output v37 --prefix karakulina` не существуют. Правильные: `--fact-map <path> --output-dir <path>`.

4. **Stage 3** — `--book-draft` корректен; `--output v37` → `--output-dir <path>`.

5. **Stage 4** — команда приблизительно верна, но требует либо обновлённых checkpoints на сервере, либо `--allow-legacy-input --proofreader-report <path> --fact-map <path>`.

**Добавлено к скриптам:**
- `test_stage1_karakulina_full.py`: теперь сохраняет `karakulina_normalization_log_{ts}.json` (merged + rejected от NN) — нужно для верификации Bug #8.

**Пути транскриптов** — будут уточнены по фактическому listing на сервере перед запуском.

---

## Реализация (отчёт о прогоне)

> Заполняет Cursor.

**Статус:** ожидает

### Что сделано (артефакты)

[Cursor — пути к артефактам]

### Стоимость и время

[Cursor]

### Проверка по критериям приёмки

[Cursor — пройти по чек-листу выше, отметить каждый]

### Что не прошло (если что-то)

[Cursor — для каждого выявленного несоответствия: что именно, где видно, гипотеза причины]

---

## Комментарии и итерации

### 2026-04-30 — Даша / Claude

Создание прогонной задачи. Все системные фиксы (016, 017, 018 + промпт-патчи Claude из CHANGELOG `[2026-04-29]`) на месте, верифицированы статически. Этот прогон — верификация что они работают вместе на реальных данных и не вступают в конфликт.

Если все 8 закрытых багов воспроизвести не удастся — пилот доехал до момента готовности к gate3 (с фото). Bug #9 (семантические галлюцинации GW) останется known issue до task 016 Narrative Auditor (после пилота).

---

## История статусов

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-04-30 | `new` | Даша / Claude |
| 2026-04-30 | `in-progress` (прогон v37 стартован Cursor) | Cursor |
