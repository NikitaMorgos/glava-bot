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

---

## История статусов

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-07 | `new` | Опус |
