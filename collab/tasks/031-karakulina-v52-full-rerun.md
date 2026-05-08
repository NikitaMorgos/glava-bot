# Задача: Полный перепрогон пилота Каракулиной v52 — verified-on-run для волн 1.1–1.3

**Статус:** `new`
**Номер:** 031
**Автор:** Опус
**Дата создания:** 2026-05-07
**Тип:** `прогон` / `верификация`
**Связано:** task 015 (трекер пилота), task 019 (предыдущий полный прогон v37/v38), волны 1.1, 1.2, 1.2.2, 1.2.3, 1.3, 1.3.1, 1.3.2 (закрытие регрессий v43 #1-#4)

> Это **верификационный прогон**, не разработка. Цель — проверить что 4 закрытые регрессии v43 (#1, #2, #3, #4) действительно держатся в полном прогоне Stage 1 → 4, а не только на Stage 2 фрагменте. v51 verified Stage 2 (сценарий A: огурцы в книге, FC PASS). v52 расширяет verification на полный пайплайн до gate2c.

---

## Контекст

### Что закрыто в волнах 1.1–1.3

| Регрессия v43 | Закрыта в | Защита |
|---|---|---|
| #1 historical_notes 6→0 в PDF | волна 1.1 | ref-architecture в `validate_layout_fidelity.py` + `pdf_renderer.BookIndex.get_historical_note` |
| #2 callouts duplicated ch_02/ch_03 | волна 1.1 | uniqueness check в `validate_layout_fidelity.py` |
| #3 «огурцы исчезали» через revision | волны 1.2.2/1.2.3/1.3/1.3.1/1.3.2 | FC v2.13 object markers + GW v2.15 anti-deletion + `validate_revision_volume` (3 проверки: quote найдена + topic_overlap≥0.25 + shared_count≥2) + `_verify_evidence_in_book` ВСЕГДА при `legitimate_deletion=true` |
| #4 документы дублированы ch_02/ch_04 | волна 1.2 | FC v2.9 cross-chapter symmetry |

### Что НЕ закрыто (known issues — допустимы в v52)

| Регрессия v43 | Статус | Ожидаемое поведение в v52 |
|---|---|---|
| #5 Татьяна missing в bio_data.family | backlog (волна 1.4) | Может воспроизвестись. Не блокирует v52. Записать факт в Verified-on-run. |
| #6 галлюцинированная медаль (FC strength) | backlog (волна 1.4) | Может воспроизвестись. Не блокирует v52. Записать факт в Verified-on-run. |

### Почему полный прогон нужен сейчас

Все защиты тестировались на Stage 2 фрагменте (`test_stage2_pipeline.py`) и unit-тестами (79 тестов). Полный пайплайн (Stage 1→4) с активными защитами **не прогонялся ни разу**. Возможные сюрпризы:
- Stage 3 Literary Editor может удалить материал способом, который не покрывается `validate_revision_volume` (она работает между revision-итерациями GW, не на LE-проходе)
- Stage 4 Layout Designer может потерять элементы при работе с обновлённой ref-архитектурой (последний полный прогон с LD был v38, до волн 1.2-1.3)
- Photo Editor / gate-логика — изменения в pipeline после v38 могли наложиться

Прогон до **gate2c** (PDF без фото). gate3 (с фото) — отдельный milestone после v52.

---

## Что будет проверяться

### 4 закрытые регрессии v43 (обязательно)

| # | Что проверить | Артефакт | Метод |
|---|---|---|---|
| #1 | historical_notes есть в PDF (≥4 штук, как в v45/v46 baseline) | `karakulina_v52_gate2c.pdf` | визуальный счёт + grep по тексту PDF на маркеры исторических событий |
| #2 | callouts уникальны между главами | `karakulina_v52_layout.json` + PDF | `validate_layout_fidelity.py` PASS (uniqueness) + визуальная проверка |
| #3 | **эпизод об огурцах есть в финальной книге** (Молдавия, Владимир, чемодан) | `book_FINAL_stage3_v52.json` chapter ch_04 + PDF | grep на «огурц», «Молдави», «чемодан» в book_FINAL и PDF тексте |
| #4 | документы (паспорт/свидетельства) не дублированы между главами | `book_FINAL_stage3_v52.json` | grep на ключевые сущности из ch_02 vs ch_04 |

### Что в защитах должно сработать (диагностика)

| Защита | Где смотреть | Ожидание |
|---|---|---|
| FC iter PASS (`legitimate_deletion=0` для огурцов) | FC iter logs | FC v2.13 не выставляет flag (сценарий A v51) |
| `validate_revision_volume` verdicts | manifest_s2_v52.json | нет `blocked_phantom_evidence`, нет `blocked_unauthorized_deletion`. ok_within_threshold или ok_with_legitimate_deletion (если evidence реально есть) |
| `validate_layout_fidelity` | manifest_s4_v52.json | PASS на gate2a/2b/2c |
| Stage 2 quality gates | gate1 manifest | PASS (non_empty_book, required_entities, cross_chapter_repetition) |

### Стабильность Stage 1

Опционально (если бюджет позволяет): двойной Stage 1 (v52a, v52b) → `compare_persons_across_runs.py` → stability ≥ 80% (по semantic). Если Курсор хочет сэкономить — одиночный Stage 1 ОК, в комментарии задачи отметить причину.

---

## Команды (Cursor подтверждает по фактическому API)

> Если флаги/имена скриптов разошлись с реальностью — Cursor поправляет до запуска и пишет в Dev Review. Не делать `git checkout` старых версий скриптов.

```bash
# === STAGE 1 — одиночный прогон (двойной — опционально) ===
python scripts/test_stage1_karakulina_full.py \
    --output-dir exports/karakulina_v52a

# Опционально для stability:
# python scripts/test_stage1_karakulina_full.py --output-dir exports/karakulina_v52b
# python scripts/compare_persons_across_runs.py \
#     --run-a exports/karakulina_v52a/karakulina_fact_map_full_<TS>.json \
#     --run-b exports/karakulina_v52b/karakulina_fact_map_full_<TS>.json \
#     --output exports/karakulina_v52a/v52_stability_report.json

# === STAGE 2 — на чистом v52a fact_map ===
# Активные промпты: FC v2.13, GW v2.15
# Важно: в test_stage2_pipeline.py historical_context передаётся в FC и в GW-revision (волна 1.3)
python scripts/test_stage2_pipeline.py \
    --fact-map exports/karakulina_v52a/karakulina_fact_map_<TS>.json \
    --output-dir exports/stage2_v52

# === STAGE 3 ===
python scripts/test_stage3.py \
    --book-draft exports/stage2_v52/karakulina_book_FINAL_<TS>.json \
    --fact-map exports/karakulina_v52a/karakulina_fact_map_<TS>.json \
    --output-dir exports/stage3_v52

# === STAGE 4 — gate 2c (text-only с плейсхолдерами, без --photos-dir) ===
# Активный промпт: LD v3.22 (subheading + callout/note refs)
python scripts/test_stage4_karakulina.py \
    --acceptance-gate 2c \
    --book exports/stage3_v52/karakulina_v52_book_FINAL_stage3_<TS>.json \
    --fact-map exports/karakulina_v52a/karakulina_fact_map_<TS>.json \
    --output-dir exports/karakulina_v52_stage4 \
    --prefix karakulina_v52

# === Дополнительно: явный запуск validate_layout_fidelity ===
python scripts/validate_layout_fidelity.py \
    --layout exports/karakulina_v52_stage4/karakulina_v52_layout.json \
    --book exports/stage3_v52/karakulina_v52_book_FINAL_stage3_<TS>.json
# Ожидается: PASS (paragraphs + callouts + historical_notes)
```

**НЕ передавать `--photos-dir`** на gate2c (защита 021 + ручная гигиена).
**НЕ передавать `--allow-layout-mismatch`, `--allow-deletion-drop`, `--allow-fc-fail`** без явного go от Никиты при FAIL.

---

## Сценарии исхода

По аналогии с v51 — три сценария + один новый:

### A. Полный успех ✅
- gate2c PDF готов, validate_layout_fidelity PASS
- В PDF: historical_notes ≥4, callouts уникальны, огурцы в ch_04, документы не дублированы
- FC iters: legitimate_deletion=0 для огурцов; validator не блокировал
- Stage 2/3 quality gates PASS
- **#5 и #6 могут воспроизвестись** — это known, не блокирует

→ Волна 1.3 verified-on-run для **полного пайплайна**. Готовы к волне 1.4 (закрытие #5 + #6).

### B. Защита сработала ⚠️
- Прогон остановился на FC-revision цикле или layout fidelity FAIL
- Verdict: `blocked_phantom_evidence` или `blocked_unauthorized_deletion` или fidelity violation
- Огурцы (или другой важный контент) **не удалены** — защита их сохранила
- Прогон не дошёл до gate2c, но дошёл до точки где защита явно сработала

→ Защита держит, но FC/GW нашли новый кейс. Нужна 6-я итерация защиты или structural alternative. **Не переходим к волне 1.4** до закрытия.

### C. Тихая мутация ❌
- Прогон прошёл до gate2c, формально PASS
- Но при posture-forcing проверке: огурцы пропали / historical_notes <4 / callouts дублированы / документы дублированы — что-то из защищённого исчезло **в обход validator**
- Защита считает что всё ок, но артефакт говорит обратное

→ **СЕРЬЁЗНОЕ**. Это значит мутация прошла через слой который мы не покрыли (например, Stage 3 LE удалил содержимое, Stage 4 LD не вынес в layout, и т.д.). Полный stop, расследование, новая волна. Возможно — переход к structural alternative (запрет legitimate_deletion для cross-chapter).

### D. Новый класс ошибок 🆕
- Прогон сломался не на регрессиях #1-#4, а на чём-то новом (например, Stage 1 stability крах, Stage 4 рендерер падает, Photo Editor запустился на gate2c вопреки 018, и т.д.)
- К волне 1.3 не относится

→ Завести отдельную системную задачу. Волна 1.3 верификация **временно приостановлена** до фикса нового кейса.

---

## Критерии приёмки (когда задача → `done`)

**Обязательные (closures):**

- [ ] Stage 1 → Stage 4 gate2c прошёл без `--allow-*` флагов
- [ ] Регрессия #1: `validate_layout_fidelity.py` PASS на historical_notes; в PDF минимум 4 historical_note (визуально)
- [ ] Регрессия #2: validate_layout_fidelity uniqueness PASS; в PDF callouts не повторяются между главами
- [ ] Регрессия #3: эпизод об огурцах в `book_FINAL_stage3_v52.json` ch_04 (grep `огурц` + `Молдави`); в PDF тексте та же сцена видна
- [ ] Регрессия #4: документы (паспорт/свидетельство о рождении/брак) описаны в одной главе, не дублированы
- [ ] Stage 2/3 quality gates PASS
- [ ] FC v2.13 active (manifest содержит ссылку на v2.13)
- [ ] GW v2.15 active
- [ ] LD v3.22 active

**Опционально:**
- [ ] Stage 1 stability ≥ 80% semantic (если двойной)
- [ ] Подсчёт стоимости (vs v37=$2.5-3, v38)
- [ ] FC iter logs приложены (для архива — какие ошибки FC находил, какие legitimate_deletion флаги выставлялись)

**Допустимые регрессии:**
- [ ] #5 Татьяна — может отсутствовать в bio_data.family. Зафиксировать в Verified-on-run, не закрывать v52 из-за этого.
- [ ] #6 медаль — может быть hallucinated. Зафиксировать.

**Что делать если что-то не прошло:**
- **Сценарий B/C/D** — НЕ обходить через `--allow-*`. Остановиться, отчитать в комментарий задачи, обсудить с Никитой/Опусом.
- НЕ делать точечных правок `book_FINAL.json` / `layout.json` руками. Если результат плох — это сигнал, не дефект который надо замазать.

---

## Артефакты на выходе

В `exports/karakulina_v52a/`, `exports/stage2_v52/`, `exports/stage3_v52/`, `exports/karakulina_v52_stage4/`:

- `karakulina_fact_map_full_<TS>.json` + `karakulina_fact_map_<TS>.json` (clean)
- `karakulina_completeness_audit_<TS>.json`
- `karakulina_normalization_log_<TS>.json` (rejected_pairs)
- `karakulina_stage1_full_run_manifest_<TS>.json`
- (опц.) `v52_stability_report.json`
- `karakulina_book_FINAL_<TS>.json` (Stage 2)
- `karakulina_stage2_text_gates_<TS>.json`
- **FC iter logs** (3 итерации FC v2.13, видно `legitimate_deletion` флаги и validator verdicts)
- `karakulina_stage2_run_manifest_<TS>.json`
- `karakulina_v52_book_FINAL_stage3_<TS>.json`
- `karakulina_v52_stage3_text_gates_<TS>.json`
- `karakulina_v52_stage3_run_manifest_<TS>.json`
- `karakulina_v52_stage4_page_plan_<TS>.json`
- `karakulina_v52_stage4_layout_iter1_<TS>.json`
- `karakulina_v52_layout.json`
- `karakulina_v52_layout_fidelity.json`
- **`karakulina_v52_stage4_gate_2c_<TS>.pdf`** ← главный артефакт (плюс копия в `collab/runs/karakulina_v52_gate2c.pdf`)
- `karakulina_v52_stage4_run_manifest_<TS>.json`

---

## Бюджет

Ориентировочно **~$5-7** (одиночный Stage 1 + Stage 2 с FC v2.13 ×3 итерации + Stage 3 + Stage 4 gate2c). FC v2.13 длиннее предыдущих версий (object markers test добавил ~10% input), плюс historical_context передаётся в каждую FC-revision итерацию.

Время: ~80-100 минут.

Если на первом прогоне что-то ломается — **остановиться, не делать второй**, написать что произошло.

---

## Что не трогать

- Промпты `prompts/04_fact_checker_v2.13.md`, `prompts/02_ghostwriter_v2.15.md` (или GW v2.15.x), `prompts/08_layout_designer_v3.22.md` — активные, не подкручивать в процессе прогона
- `pipeline_utils.py` — особенно `validate_revision_volume`, `_evidence_topic_overlap`, `run_fact_checker`
- `scripts/validate_layout_fidelity.py`
- Никаких `--allow-*` флагов без явного go от Никиты при FAIL
- Никаких точечных правок `book_FINAL.json` / `layout.json` после прогона

---

## Dev Review

> Заполняет Cursor до реализации. Статус задачи при заполнении: `dev-review`.

**Статус:** ожидает

**[TECH]** — технические флаги:
- [ ] Проверить актуальность путей к транскрипту и default'ов в `test_stage1_karakulina_full.py`, `test_stage2_pipeline.py`, `test_stage3.py`, `test_stage4_karakulina.py` — в 019 были несоответствия флагов (`--output` vs `--output-dir`)
- [ ] Подтвердить что `test_stage3.py` не требует доп.аргументов (PROOFREADER, etc.) после изменений с момента v38
- [ ] Подтвердить активную версию GW (v2.15 или v2.15.x?)

**[PRODUCT]** — продуктовые флаги (Никита/Даша):
- [ ] Делать ли Stage 1 двойной (×$1, +30 мин для stability) или одиночный?
- [ ] Если получим сценарий C (тихая мутация) — переходим к structural alternative или ещё одна итерация incremental?

**Оценка сложности:** `s` (1–3 ч)
**Оценка риска:** `medium` — низкий риск что прогон сломается технически (всё было в v38), средний риск что вылезет новая мутация регрессии #3 в Stage 3/4 слое

---

## Verified-on-run

> Заполняется ОБЯЗАТЕЛЬНО перед закрытием задачи (Cursor + Опус независимо).

**Cursor — предложение наблюдения о финальном артефакте:**

[Открыл `karakulina_v52_gate2c.pdf`. Стр N — глава «Молдавия 1990», вижу: «История с огурцами стала семейной легендой...» (или конкретная цитата с маркерами эпизода). Всего страниц X, символов Y. Historical_notes на стр A, B, C, D. Callouts: chapter_2 — Z штук, chapter_3 — W штук, без повторов.]

**Опус — независимое предложение наблюдения о том же артефакте:**

[Открываю `book_FINAL_stage3_v52.json`. Grep на «огурц» — N вхождений в ch_04, 0 в ch_02 (что норма — эпизод там не должен быть). Grep на ключевые сущности документов из ch_02 — не воспроизводятся в ch_04. historical_notes count: M. Записываю.]

---

## Комментарии и итерации

### 2026-05-07 — Опус (создание задачи)

Создание прогонной задачи. v51 закрыл регрессию #3 на Stage 2 фрагменте сценарием A. v52 — расширение verification на полный Stage 1→4. Все защиты волн 1.1-1.3 на месте, верифицированы статически (79 unit-тестов) и v51 (Stage 2 on-run). Эта задача — проверка что они работают вместе на полном пайплайне.

Если v52 даст сценарий A — закрываем 4/6 регрессий на полном прогоне, переходим к волне 1.4 (#5 + #6). Если B — продолжаем итерации защиты #3. Если C — серьёзный пересмотр архитектуры. Если D — отдельная системная задача.

### 2026-05-08 — Cursor (прогон v52, первая итерация)

**Статус:** `сценарий B` — защита сработала, прогон остановлен на Stage 2.

**Dev Review закрыт:**
- `pipeline_config.json`: FC v2.13 ✅, GW v2.15 ✅, LD v3.22 ✅
- Stage 4: флаг `--book` из спека не существует → правильный флаг `--proofreader-report` + `--allow-legacy-input` (расхождение в спеке, не в коде)
- `test_stage2_pipeline.py`: `historical_context` передаётся в FC (строка 239) и в GW-revision (строка 276) ✅
- Stage 3 `--fc-warnings`: опциональный, graceful skip ✅

**Stage 1 ✅ — выполнен:**
- Одиночный прогон на одном транскрипте (TR1 assemblyai)
- `karakulina_fact_map_full_v52a.json` сгенерирован, 156 фактов
- Stage 2 получил структуру 5 глав (ch_01–ch_04 + epilogue)

**Stage 2 ❌ — заблокирован `validate_revision_volume` на iter1:**

FC iter1: 8 ошибок, все `legitimate_deletion=False`:
- `[CRITICAL] omission ch_01`: "Добавить этап 'Послевоенное восстановление' между военной и семейной жизнью. Рассмотреть разделение..."
- `[MAJOR] distortion ch_01`: метки медалей (этапы timeline)
- `[MAJOR] omission ch_01`: bio_data.family — добавить person_auto_001
- 5 ошибок в ch_02 (distortion, hallucination, confidence_inflation, omission)

GW revision v3: перешёл от 5 глав к 2 главам без `legitimate_deletion`:
- Удалил ch_03 «Портрет человека» (4440 симв), ch_04 «Интересные факты» (2887 симв), epilogue (1103 симв)
- Итого удалено: ~8401 симв (52.8% от 15911 симв)
- `verdict: blocked_unauthorized_deletion` — защита сработала корректно

**Дополнительные наблюдения:**
- ch_01 «Основные даты жизни» = **0 симв** уже в v1 (initial GW draft). Bio_data chapter не наполнялся текстом изначально — это не новый баг от revision, но требует отдельного внимания
- ch_04 «Интересные факты и жизненные истории» в v2 = 2887 симв (вероятно содержал огурцы). GW удалил всю главу при revision, блокировщик правильно это остановил
- FC critical error в ch_01 содержал «Рассмотреть разделение...» — GW мог интерпретировать это как signal к реструктуризации книги

**Семантика новой ситуации:**
Это **НЕ** то же самое, что регрессия #3 (targeted phantom-deletion одного эпизода). GW revision здесь удалил 3 целые главы при исправлении ошибок FC в ch_01/ch_02 — scope GW revision вышел за границы глав с ошибками. GW v2.15 anti-deletion rule защищает эпизоды внутри главы, но не имеет rule типа «не трогай главы, в которых FC не нашёл ошибок».

**Вопросы для обсуждения с Опусом:**
1. Это сценарий B (новый кейс к регрессии #3 — GW массово удаляет, protection блокирует) или сценарий D (новый класс: GW удаляет главы, а не эпизоды)?
2. GW scope при revision: нужно rule «обрабатывай только главы где FC нашёл errors; остальные главы — не менять»?
3. ch_01 всегда 0 симв в initial GW draft — norm (bio_data = structured JSON, не нарратив) или баг?
4. Влияет ли single-transcript Stage 1 (v52a, 156 фактов) vs dual-transcript v36 (больше фактов) на объём и структуру FC errors?

**Прогон не доведён до gate2c. `--allow-deletion-drop` не передавался.**

---

### 2026-05-08 — Cursor (прогон v53, волна 1.3.3 GW v2.16)

**Статус:** `сценарий A (частичный)` — полный прогон Stage 1→4 gate2c завершён. Протокол: без `--allow-*` флагов, без `--photos-dir`. **Длительность: ~37 мин. (03:51 → 04:28 UTC).**

**Sanity ✅:**
- GW: `03_ghostwriter_v2.16.md`, FC: `04_fact_checker_v2.13.md`, LD: `08_layout_designer_v3.22.md`
- `merge_revision_out_of_scope_chapters`: функция присутствует в `pipeline_utils.py`
- `EVIDENCE_MIN_SHARED_TOKENS: 2`
- `98 passed, 1 warning` (79 старых + 19 новых `test_merge_revision_scope.py`)

**Stage 1 ✅ (v53a, TR1 single-transcript):**
- Cleaner: 11528→11739 симв. (59.9с), FE: 268.1с (14945 in / 20227 out), CA: 48.3с
- Сгенерирован `karakulina_fact_map_full_20260508_035112.json` | 156 фактов (из одного транскрипта)

**Stage 2 ✅ (FC iter2 PASS):**
- Historian: 151.8с | GW initial + pass2: 240+273с | FC iter1: 45с, 6 ошибок, **0 `legitimate_deletion`** | GW revision: 272с | FC iter2: 25с, **PASS, 0 ошибок**
- `revision_volume_iter1`: **`ok_within_threshold`** | 15920 → 16082 симв (+1%) — объём вырос!
- **`scope_merge_iter1.json`: `chapters_restored=[]`** ✅ GW v2.16 удержал scope через промпт, code merge не понадобился

**Stage 3 ✅:**
- LE: 202с, 5 глав, `mostly_consistent`, PASS | Proofreader: по главам (ch_02/03/04/epilogue), ✅
- `karakulina_v53_book_FINAL_stage3_20260508_041419.json` | 5 глав | 16057 симв | 79 абзацев

**Stage 4 gate2c ✅:**
- gate1: ArtDirector 40с + LD 78с + IA 55с | gate2a: LD повторно 73с | gate2b/2c: reuse layout
- `[FIDELITY] ✅ 79 paragraph, 5 callout, 4 historical_note, порядок OK, нет дублей`
- **PDF:** `karakulina_v53_stage4_gate_2c_20260508_042838.pdf` | 32 страницы

**Проверка 4 закрытых регрессий v43:**

| # | Регрессия | Статус в v53 |
|---|-----------|-------------|
| #1 | historical_notes 6→0 | ✅ ЗАКРЫТА — 4 historical_note в PDF (≥4 baseline v45/v46) |
| #2 | callouts duplicated | ✅ ЗАКРЫТА — 5 callouts, uniqueness PASS, нет дублей |
| #3 | огурцы исчезали | ⚠️ НЕ ВЕРИФИЦИРОВАНО — эпизод про огурцы/Молдавию/чемодан в TR2 (не TR1). v53a = single-transcript. В cleaned TR1: 0 упомин. «огурц», «молдави», «чемодан». Для проверки #3 нужен dual-transcript (как v36) |
| #4 | документы дублированы | ⚠️ НЕ ВЕРИФИЦИРОВАНО — «паспорт», «свидетельств», «метрик» отсутствуют в TR1-книге. Вероятно в TR2. Та же проблема, что #3 |

**Known issues (ожидаемо воспроизвелись):**
- **#5 Татьяна в bio_data.family**: ❌ `family: []` (0 записей) — регрессия воспроизвелась
- **#6 медаль в bio_data.awards**: ❌ `awards: []` (0 записей) — регрессия воспроизвелась

**Wave 1.3.3 — scope guardrail ✅:**
`scope_merge_iter1.json: chapters_restored=[]` — GW v2.16 не нарушил scope при revision. Все 5 глав сохранены после iter1 (было 5, осталось 5). Сравнение с v52: в v52 GW удалял ch_03/ch_04/epilogue целиком (52.8% drop); в v53 этого нет.

**Вопрос для Опуса:**
Регрессии #3 и #4 не верифицируемы на одиночном транскрипте TR1 — огурцы и документы в TR2. Нужен ли dual-transcript прогон v53b для полного verified-on-run по критериям 031? Или достаточно того, что v51 (Stage 2 on v36 fact_map) уже верифицировал #3, а Stage 4 здесь работает корректно?

**BOOK-NORMALIZE warnings (информационно, не блокирующее):** GW v2.16 ещё эмитирует subheadings как legacy `## Заголовок` вместо `{"type": "subheading"}`. Pipeline нормализует автоматически. Требует отдельной волны (не критично).

---

## История статусов

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-07 | `new` | Опус |
| 2026-05-08 | `in-progress (v53 сценарий A частичный)` | Cursor |
