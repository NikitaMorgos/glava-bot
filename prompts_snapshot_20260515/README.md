# Снимок активных промптов на 2026-05-15

Все 14 активных промптов pipeline'а GLAVA, скопированные из `prompts/` согласно `prompts/pipeline_config.json`.

## Сводка

| # | Роль | Файл | Модель | Темп. | Размер | Послед. изменение |
|---|---|---|---|---|---|---|
| 01 | Cleaner | `01_cleaner_v1.md` | Haiku 4.5 | 0.10 | 1.5K / 28 строк | 25 мар |
| 02 | Fact Extractor | `02_fact_extractor_v3.4.md` | Sonnet 4 | 0.15 | 41K / 679 строк | 28 апр |
| 03 | Ghostwriter | `03_ghostwriter_v2.18.md` | Sonnet 4 | 0.40 | 132K / 1934 строки | **15 мая** ⭐ |
| 04 | Fact Checker | `04_fact_checker_v2.13.md` | Sonnet 4 | 0.10 | 86K / 1241 строка | 7 мая |
| 05 | Literary Editor | `05_literary_editor_v3.1.md` | Sonnet 4 | 0.50 | 50K / 804 строки | **15 мая** ⭐ |
| 06 | Proofreader | `06_proofreader_v1.md` | Sonnet 4 | 0.00 | 32K / 550 строк | 29 мар |
| 07 | Photo Editor | `07_photo_editor_v1.md` | Sonnet 4 | 0.25 | 33K / 561 строка | 29 апр |
| 08 | Layout Designer | `08_layout_designer_v3.22.md` | Sonnet 4 | 0.25 | 101K / 1937 строк | 7 мая |
| 09 | QA Layout | `09_qa_layout_v1.md` | Sonnet 4 | 0.05 | 38K / 704 строки | 9 апр |
| 11 | Interview Architect | `11_interview_architect_v4.1.md` | Sonnet 4 | 0.50 | 36K / 668 строк | 23 апр |
| 12 | Historian | `12_historian_v3.md` | Sonnet 4 | 0.30 | 40K / 651 строка | 28 апр |
| 13 | Cover Designer | `13_cover_designer_v2.6.md` | Sonnet 4 | 0.65 | 49K / 916 строк | 28 апр |
| 15 | Layout Art Director | `15_layout_art_director_v1.8.md` | Sonnet 4 | 0.45 | 33K / 638 строк | 29 апр |
| 16 | Completeness Auditor | `16_completeness_auditor_v1.2.md` | Haiku 4.5 | 0.10 | 21K / 341 строка | **15 мая** ⭐ |

⭐ — обновлено сегодня (15 мая): Ghostwriter v2.18, Literary Editor v3.1, Completeness Auditor v1.2.

## Порядок в пайплайне

```
Stage 1: 01 Cleaner → 02 Fact Extractor → 16 Completeness Auditor → [Name Normalizer script]
Stage 2: 12 Historian → 03 Ghostwriter → 04 Fact Checker
Stage 3: 05 Literary Editor → 06 Proofreader
Stage 4: 07 Photo Editor → 15 Layout Art Director → 08 Layout Designer → 09 QA Layout → 13 Cover Designer
Утилитарный: 11 Interview Architect (для составления уточняющих вопросов)
```

## Источник

`prompts/pipeline_config.json` (snapshot 2026-05-15).
