# RP-0 — Baseline (pre-refactor)

**Дата создания:** 2026-05-08
**Git tag:** `rp-0-baseline-pre-refactor`
**Commit:** будет привязан к merge этого PR в main
**Статус:** активный baseline

> Это **исходная точка отсчёта** перед началом рефакторинга по новой стратегии (Этап 1: gate1 infrastructure). Сюда мы можем откатиться если последующие этапы создадут проблемы которые не можем разрешить за разумное время.

---

## Что зафиксировано

### Code state

- main после волны 1.3.3 (PR #11 merged 2026-05-08)
- pipeline_config.json — активные версии:
  - cleaner: `01_cleaner_v1.md`
  - fact_extractor: `02_fact_extractor_v3.4.md`
  - historian: `12_historian_v3.md`
  - **ghostwriter: `03_ghostwriter_v2.16.md`** (волна 1.3.3 — scope guardrail)
  - **fact_checker: `04_fact_checker_v2.13.md`** (волна 1.3.2 — object markers test)
  - **literary_editor: `05_literary_editor_v3.md`** (v3.0, базовый)
  - proofreader: `06_proofreader_v1.md`
  - photo_editor: `07_photo_editor_v1.md`
  - layout_designer: `08_layout_designer_v3.22.md` (волна 1.1 шаг 4)
  - qa_layout: `09_qa_layout_v1.md`
  - cover_designer: `13_cover_designer_v2.6.md`
  - layout_art_director: `15_layout_art_director_v1.8.md`
  - interview_architect: `11_interview_architect_v4.1.md`
  - completeness_auditor: `16_completeness_auditor_v1.1.md`

### Защитные функции в pipeline_utils

- `validate_layout_fidelity` — fidelity check book→layout (paragraphs/callouts/historical_notes)
- `validate_revision_volume` — protection от volume drop при GW revision
- `_verify_evidence_in_book` + `_evidence_topic_overlap` + `_topic_tokens` — evidence verification с topic-overlap + abs floor (волны 1.2.3 / 1.3.1 / 1.3.2)
- `merge_revision_out_of_scope_chapters` — out-of-scope chapter guardrail (волна 1.3.3)
- `enforce_bio_data_completeness` — bio_data.family completeness (task 027)
- `pipeline_quality_gates`: 7 gate-функций (non-empty book, required entities, repetition overlap, bio not empty, phase B volume growth, structural layout guard, pdf preflight)

### Test coverage

98 unit-тестов в 5 файлах:
- `tests/test_revision_volume.py` (25)
- `tests/test_validate_layout_fidelity.py` (24)
- `tests/test_pdf_renderer_refs.py` (17)
- `tests/test_quality_gates.py` (4)
- `tests/test_fact_checker_historical_context.py` (9)
- `tests/test_merge_revision_scope.py` (19)

---

## Что должно работать (инварианты)

При запуске на тестовом сценарии (Stage 2 fragment или Stage 1→4 полный) с активными промптами выше:

- **Регрессия #1** (historical_notes 6→0 в PDF) — закрыта (волна 1.1)
- **Регрессия #2** (callouts duplicated между ch_02 и ch_03) — закрыта (волна 1.1)
- **Регрессия #3** (огурцы исчезают через FC false positive deletion) — закрыта (волны 1.2.2/1.2.3/1.3/1.3.1/1.3.2, verified v51 + v53b stage2)
- **Регрессия #4** (документы дублированы между ch_02 и ch_04) — закрыта (волна 1.2)
- **GW out-of-scope при revision** — закрыта (волна 1.3.3, verified v53)
- **GW scope merge fallback** — `chapters_restored=[]` на TR1+TR2 means GW promt держит scope (v53 verified)

---

## Что точно НЕ работает (known issues — НЕ в scope baseline)

- **Регрессия #5** (Татьяна missing в bio_data.family) — backlog, не закрыта
- **Регрессия #6** (галлюцинированная медаль, FC strength insufficient) — backlog
- **err_004** (historical_note в narrative body вместо `book.historical_notes[]`) — backlog
- **Пластиковый абзац в ch_04 v53b** («ярких поступков и запоминающихся привычек») — стилистическая регрессия GW, не покрыта защитами. Будет лечиться в Этапе 1 (GW v2.17).
- **chapters[ch_01].timeline удаляется LE** (v53b: Stage 2 = 6 этапов → Stage 3 = 0) — реальная регрессия LE, task 034. Будет лечиться в Этапе 1.
- **gate1 product checklist отсутствует** — нет инструмента продуктовой оценки текста. Будет создан в Этапе 1.
- **Сводный текстовый артефакт до вёрстки отсутствует** — нет одного MD файла для чтения глазами. Будет создан в Этапе 1.

---

## Исторические артефакты (good states)

Зафиксированы как reference в `collab/runs/`:

| Версия | Чем хороша | Где |
|---|---|---|
| **v36** (2026-04-29) | Best TR1+TR2 охват: 13K chars, 6 historical_notes, 16 bio_data.family, 5 глав. Прошёл gate2c (PDF 53 стр — с дублями LD, но контент good). | `collab/runs/karakulina_v36_20260428/book_FINAL_stage3_v36.json` + `karakulina_v36_gate2c_20260429.pdf` |
| **v46** (2026-05-06) | Тот же v36-текст с правильной вёрсткой (LD v3.22, без дублей). 22 стр PDF. validate_fidelity PASS. | `collab/runs/karakulina_v46/` (только PNG страниц 06/07/14, full PDF на сервере) |
| **v53** (2026-05-08) | Рекорд по объёму: 16K chars на TR1. GW v2.16 + все защиты волн 1.1-1.3.3. Прошёл gate2c (23 стр). | `feat/v53-artifacts` ветка |
| **v53b** (2026-05-08) | TR2 only: 13K chars. Огурцы сохранены в ch_02. Stage 2 timeline=6 этапов (но LE удаляет — реальная регрессия). | `feat/v53-artifacts` ветка |

**Если последующие этапы сломают что-то непоправимо** — мы знаем что v36/v46/v53 работали. Можем сравнивать прогоны новых версий с этими как с эталоном.

---

## Команда отката

```bash
git checkout main
git reset --hard rp-0-baseline-pre-refactor
git push origin main --force  # только с согласия Никиты
```

**Не делать без явного go от Никиты.** Откат — destructive операция, теряет всю работу после tag.

Альтернатива безопаснее — создать новую ветку от tag, продолжить работу с этой точки:
```bash
git checkout -b restart-from-rp-0 rp-0-baseline-pre-refactor
```

---

## Команда воспроизведения baseline на тестовом прогоне

После checkout на tag — запустить тестовый Stage 2 фрагмент:
```bash
git checkout rp-0-baseline-pre-refactor
python scripts/test_stage2_pipeline.py \
    --fact-map exports/karakulina_v52a/karakulina_fact_map_<TS>.json \
    --output-dir exports/baseline_verify
```

Ожидаемые результаты:
- FC v2.13 PASS на 2-3 итерациях
- GW v2.16 scope_merge: `chapters_restored=[]`
- validate_revision_volume verdict: `ok_within_threshold`
- 98 unit-тестов PASS

---

## Что НЕ закрывает RP-0

- Качество текста по Дашин чек-листу (его нет ещё)
- Стилистическую регрессию (пластиковый абзац ch_04)
- Удаление timeline LE (task 034)
- Универсализацию пайплайна (генерализация на других субъектов)

Это всё в Этапах 1-5.

---

## Решение об активации отката

Принимает **Никита**. Опус / Даша / Курсор могут предложить — go даёт Никита. Зафиксировано в `dev-review-protocol.md`.

---

## Связанные документы

- [stocktake (PR #12)](https://github.com/NikitaMorgos/glava-bot/pull/12)
- [audit (PR #13)](https://github.com/NikitaMorgos/glava-bot/pull/13)
- [product-goal (PR #15)](https://github.com/NikitaMorgos/glava-bot/pull/15)
- [wave-1.4.0 lessons (PR #16)](https://github.com/NikitaMorgos/glava-bot/pull/16)
- [karakulina-versions-metrics](karakulina-versions-metrics.md) — таблица всех версий
- `collab/context/dev-review-protocol.md` — правила процесса
