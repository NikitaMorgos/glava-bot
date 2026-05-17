# Задача 045c: Класс 10 extension — Chapter sections anchors

**Статус:** `spec-approved`
**Номер:** 045c
**Автор:** Опус
**Дата создания:** 2026-05-17
**Тип:** `cco-скрипт` + промпт GW ПРАВИЛО 11 + конфиг
**Batch:** v60 sprint (extension of класс 10)

---

## Контекст

В v59 ch_03 утратил раздел «Гостеприимство и кулинария» — GW иногда убирает тематические подзаголовки. Task 045 (из Batch 2) планировал anchors, но не был реализован.

**Class 10 extension:** принудительные якоря для tematических подразделов глав. Если anchor отсутствует в главе — enforcer создаёт краткую заглушку или выдаёт warning.

## Universality check

1. ✅ ПРАВИЛО 11 universal: «включай обязательные tематические разделы из chapter_sections_anchors конфига»
2. ✅ Конфиг `chapter_sections_anchors_karakulina.json` — subject-specific разделы
3. ✅ Алгоритм generic — читает конфиг + проверяет presence в chapters
4. ✅ Subject-replacement test: для Корольковой — свои разделы ✅

---

## Спек

### 1. Новый конфиг `collab/context/chapter_sections_anchors_karakulina.json`

```json
{
  "chapter_sections_anchors": {
    "ch_03": [
      {
        "anchor_id": "hospitality_cuisine",
        "heading": "Гостеприимство и кулинария",
        "required": true,
        "fallback_action": "warn"
      }
    ]
  }
}
```

### 2. Новые функции в `pipeline_utils.py`

```python
def validate_chapter_sections_anchors(book, anchors_config):
    """Проверяет наличие обязательных tематических разделов в главах."""
    
def enforce_chapter_sections_anchors(book, fact_map, anchors_config):
    """Предупреждает или создаёт заглушку для отсутствующих разделов."""
```

### 3. GW v2.21 — ПРАВИЛО 11

```
ПРАВИЛО 11: ТЕМАТИЧЕСКИЕ РАЗДЕЛЫ ГЛАВ
В каждой главе должны быть все обязательные тематические подразделы из chapter_sections_anchors конфига.
Для данного субъекта обязательные разделы указаны в конфиге (передаётся в системном промпте).
Не пропускай тематические разделы даже при коротком нарративе.
```

### 4. Передача конфига разделов в GW

В Stage 2 runner: загрузить `chapter_sections_anchors_<subject>.json`, сериализовать и добавить в системный контекст GW.

### 5. Интеграция в Stage 3

После `normalize_book_topo` — вызов `validate_chapter_sections_anchors`, отчёт `chapter_sections_anchors.json`.

---

## Verified-on-run критерий

«ch_03 содержит раздел «Гостеприимство и кулинария» (восстановлен)»

---

## Dev Review

**[TECH]** — нет флагов. Новые функции + конфиг + ПРАВИЛО 11 GW v2.21.
**[PRODUCT]** — нет.
**Сложность:** `s`
**Риск:** `medium` (интеграция в Stage 2 — new prompt context)

---

## История

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-17 | `spec-approved` | Опус |
