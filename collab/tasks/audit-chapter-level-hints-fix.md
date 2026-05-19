# v66 backlog: audit_revision_diff chapter-level hints fix

**Status:** `new`  
**Source:** v65 STOP false positive (2026-05-19)  
**Sprint:** v66a

---

## Описание проблемы

В v65 pipeline `audit_revision_diff` вернул `unauthorized_changes=23` и остановил Stage 3, хотя
все изменения являлись **валидными ответами на chapter-level hints**.

Root cause: функция сравнивает diff на уровне отдельных параграфов, тогда как hints для
`personal_historical_voice` и `required_episodes_coverage` задаются на уровне главы (без конкретного
`snippet`). Каждый затронутый параграф считается отдельным `unauthorized_change`.

---

## Факты из v65 run

| Параметр | Значение |
|---------|---------|
| hints_count | 18 |
| applied | 16 |
| skipped | 2 |
| unauthorized_changes | 23 |
| Реальные violations | 0 |

Распределение `unauthorized_changes` по главам:
- ch_02: 6 (добавление "Как вспоминает Татьяна" — hint h_003 personal_historical_voice)
- ch_03: 7 (hint h_004)
- ch_04: 8 (hint h_005)
- epilogue: 2 (episode hints h_008–h_018)

---

## Предлагаемый fix

### Вариант A (minimal, recommended for v66)

В `audit_revision_diff` добавить логику: если hint не имеет `snippet` (snippet is None) и
имеет `chapter_id` — считать ВСЕ изменения в этой главе как потенциально авторизованные.
Помечать их как `authorized_chapter_level` вместо `unauthorized_changes`.

```python
# pipeline_utils.py — audit_revision_diff
def _is_authorized_change(change, revision_hints):
    chapter_id = change.get('chapter_id')
    # Check if any hint covers this chapter without snippet (chapter-level hint)
    chapter_level_hints = [
        h for h in revision_hints
        if h.get('chapter_id') == chapter_id and h.get('snippet') is None
    ]
    if chapter_level_hints:
        return True, 'authorized_chapter_level'
    return False, 'unauthorized'
```

### Вариант B (schema fix, for v2.25 GW prompt)

GW v2.24 возвращает в `rule13_revision_applied` структуру `{"hint_id", "fix"}` вместо
`{"hint_id", "action", "diff_summary"}`. Нужно либо:
- Обновить `audit_revision_diff` принимать поле `"fix"` как `diff_summary`
- Или добавить в GW v2.25 явную инструкцию выводить `action` и `diff_summary`

---

## Threshold корректировка (interim fix)

Пока Вариант A не реализован: для chapter-level hints (personal_historical_voice, required_episodes)
пересмотреть `THRESHOLD = 5` → `THRESHOLD = 30` или добавить параметр
`chapter_level_hint_threshold = 50`.

**Опус-decision v65:** использовать Option C (продолжить Stage 3 без остановки), audit fix → v66 backlog.

---

## Files affected

- `pipeline_utils.py` → функция `audit_revision_diff`
- `tests/test_v65_sprint.py` → добавить snapshot test для chapter-level hint scenario
- `prompts/03_ghostwriter_v2.25.md` (если Вариант B) → обновить schema rule13

---

## Priority

`medium` — STOP был false positive, не повлиял на quality. Но блокирует автоматический пайплайн
без Opus review при каждом запуске с chapter-level hints.
