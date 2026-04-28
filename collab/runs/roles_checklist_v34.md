# Roles Checklist — v34

> Прогон: `karakulina_v34`  
> Дата запуска: 2026-04-22  
> config_sha256: `f93a060e884732d5`  
> Цель: первый прогон на полностью универсальных промптах (задача 010)

---

## Pre-flight

| Параметр | Значение | Статус |
|----------|----------|--------|
| config `_updated` | 2026-04-22 | ✅ |
| `config_sha256` | `f93a060e884732d5` | ✅ |
| Ghostwriter prompt | `03_ghostwriter_v2.13.md` | ✅ |
| Ghostwriter temperature | 0.4 | ✅ |
| Fact Checker prompt | `04_fact_checker_v2.6.md` | ✅ |
| Layout Designer prompt | `08_layout_designer_v3.19.md` | ✅ |
| Historian | ENABLED (нет --skip-historian) | ✅ |
| Phase B max-fc-iterations | 3 | ✅ |
| FC FAIL блокировка | sys.exit(1) | ✅ |
| Phase B merge защита ch_01 | bio_data + timeline | ✅ |

---

## Stage 1 — Fact Extractor

| Роль | Промпт | Temp | Время | Вердикт |
|------|--------|------|-------|---------|
| Fact Extractor | `02_fact_extractor_v3.3.md` | 0.15 | | |

**Артефакт:** `fact_map_v34.json` — получен? ☐

---

## Stage 2 — Historian + Ghostwriter + Fact Checker

| Роль | Промпт | Temp | Итераций FC | Время | Вердикт |
|------|--------|------|-------------|-------|---------|
| Historian | `12_historian_v3.md` | 0.3 | — | | |
| Ghostwriter | `03_ghostwriter_v2.13.md` | 0.4 | — | | |
| Fact Checker | `04_fact_checker_v2.6.md` | 0.1 | | | |

**FC Stage 2 итог:** ☐ PASS / ☐ FAIL  
**FC итераций потребовалось:** ___  
**Артефакт:** `book_FINAL_stage2.json` — получен? ☐

---

## Stage 3 — Literary Editor + Proofreader

| Роль | Промпт | Temp | Время | Вердикт |
|------|--------|------|-------|---------|
| Literary Editor | `05_literary_editor_v3.md` | 0.5 | | |
| Proofreader | `06_proofreader_v1.md` | 0.0 | | |

**Артефакт:** `book_FINAL_stage3.json` + `.txt` — получен? ☐

---

## Phase B — Incremental FactExtractor + Ghostwriter + FC

| Роль | Промпт | Temp | Итераций FC | Время | Вердикт |
|------|--------|------|-------------|-------|---------|
| Fact Extractor (incr.) | `02_fact_extractor_v3.3.md` | 0.15 | — | | |
| Ghostwriter | `03_ghostwriter_v2.13.md` | 0.4 | — | | |
| Fact Checker | `04_fact_checker_v2.6.md` | 0.1 | | | |

**FC Phase B итог:** ☐ PASS / ☐ FAIL  
**FC Phase B итераций:** ___  
**ch_01.bio_data после merge:** ☐ сохранён  
**ch_01.timeline после merge:** ☐ непустой (≥4 этапов)  
**Артефакт:** `book_FINAL_phase_b_v34.json` + `karakulina_v34_FINAL_phase_b.txt` — получен? ☐

---

## Итоговый статус

| Секция | Статус |
|--------|--------|
| Stage 1 | |
| Stage 2 (FC) | |
| Stage 3 | |
| Phase B (FC) | |
| **Общий** | |

---

## Gate 1 чек-лист (заполняет Даша)

- [ ] Нет «раздражалась на подарки»
- [ ] Нет «семейная драма с Валерой»
- [ ] Нет «революции»
- [ ] Нет «выковыривать как символ»
- [ ] `death_year=null` → не утверждается смерть в тексте
- [ ] `bio_data` полный (все родственники из fact_map)
- [ ] `timeline` 4–7 этапов (не пустой)
- [ ] `historical_notes` в массиве (не `***triple***` в content)
- [ ] Гл.03 плоская структура
- [ ] Исторические справки в гл.02 (≥50% страниц)
- [ ] Ключевые факты: Сахалин, пианино/шуба, стрекоза/муравей

**Gate 1 вердикт:** ☐ PASS → Gate 2a / ☐ FAIL → анализ + v35
