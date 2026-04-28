# Валидация протокола прогона GLAVA
**Дата валидации:** 2026-04-21
**Источник:** `collab/context/pipeline-run-protocol.md`
**Сверено с кодом:** `pipeline_utils.py`, `test_stage1_karakulina_full.py`, `test_stage2_pipeline.py`, `test_stage3.py`, `test_stage2_phase_b.py`, `prompts/pipeline_config.json`

---

## Итог

| Раздел | Статус | Критичность |
|--------|--------|-------------|
| Pre-flight: таблица промптов | ⚠️ Расхождение (Layout v1.8/v3.14 ≠ v1.9/v3.19) | Низкая — Stage 4 |
| Pre-flight: температуры | ✅ Совпадает | — |
| Pre-flight: max_tokens | ⚠️ Historian 16000, FC 8000 — не упомянуты в «≥32000» | Низкая |
| Stage 1: последовательность | ✅ Совпадает | — |
| Stage 1: артефакты | ⚠️ Имена файлов немного отличаются от протокола | Низкая |
| Stage 2: порядок Историк/GW | ⚠️ «Параллельно» — неверно, код делает последовательно | Низкая |
| Stage 2: два прохода Историка | ❗ Протокол не упоминает pass2 историка | Средняя |
| Stage 2: FC FAIL → блокировать | ❗ Код **не блокирует**, продолжает с последней книгой | Высокая |
| Stage 3: style_passport файл | ⚠️ Не создаётся отдельный файл | Низкая |
| Stage 3: bio_data сохранение | ✅ Есть явная защита (строки 629–635) | — |
| Stage 3: per-chapter порог | ✅ 10 000 симв. совпадает | — |
| Phase B: макс итераций FC | ❗ Протокол: 2, v32 запущен с 3 | Средняя |
| Phase B: FC FAIL → блокировать | ❗ Код **не блокирует** | Высокая |
| Артефакты Stage 2: book_draft | ⚠️ Называется `book_draft_v1`, `book_draft_v2`, не `book_draft_vXX` | Низкая |
| Артефакты Stage 3: style_passport | ❗ Файл не создаётся отдельно | Средняя |

---

## Раздел: Pre-flight — таблица версий промптов

**В протоколе:**
```
Layout Art Director (15) | 15_layout_art_director_v1.8.md | v1.9
Layout Designer (08)     | 08_layout_designer_v3.14.md    | v3.19
```

**В коде (`prompts/pipeline_config.json`):**
```
layout_art_director: prompt=15_layout_art_director_v1.8.md
layout_designer    : prompt=08_layout_designer_v3.14.md
```
Ожидаемые версии в протоколе — v1.9 и v3.19 — не совпадают с файлами в конфиге (v1.8 и v3.14).

**Предлагаю:** Обновить таблицу в протоколе до актуальных файлов (v1.8 и v3.14), либо обновить конфиг когда Layout-промпты получат новую версию. Это касается только Stage 4 — пока не критично.

---

## Раздел: Pre-flight — max_tokens

**В протоколе:**
> Все агенты должны иметь `max_tokens >= 32000` (Ghostwriter, Literary Editor, Proofreader, FactExtractor). Layout Designer — 64000.

**В коде:**
```
historian   : max_tokens=16000
fact_checker: max_tokens= 8000
```

**Предлагаю:** Оставить протокол — перечисленные там агенты действительно ≥ 32000. Историк и FC — специально меньше (JSON-ответ небольшой). Добавить в протокол явное примечание: «Historian = 16000, FC = 8000 — намеренно, ответ компактный».

---

## Раздел: Stage 2 — порядок Историка

**В протоколе:**
> 1. Историк (12) — **параллельно с Ghostwriter**, генерирует исторические справки

**В коде (`test_stage2_pipeline.py`):**
```python
# Последовательно:
if not args.skip_historian:
    historical_context = run_historian(...)   # сначала Историк
    
book_draft_v1 = run_ghostwriter(...)          # потом Ghostwriter pass1 (получает historical_context)

# потом опционально второй pass Историка (--skip-historian-pass2)
# потом GW pass2
```
Историк запускается **до** Ghostwriter, не параллельно. Плюс в коде есть `--skip-historian-pass2` для второго прохода — протокол этого не упоминает вообще.

**Предлагаю:** Исправить формулировку в протоколе: «Историк запускается **перед** Ghostwriter и передаёт ему `historical_context`». Добавить упоминание pass2 (если нужен).

---

## Раздел: Stage 2 — FC FAIL после 3 итераций

**В протоколе:**
> Если после 3-й итерации FAIL → **блокировать прогон**, диагностика

**В коде:**
```python
print(f"\n❌ [FACT_CHECKER] FAIL после {args.max_fc_iterations} итераций. ЭСКАЛАЦИЯ → Продюсер.")
# ... и продолжает сохранять финальную книгу без sys.exit()
```
Прогон **не останавливается** — книга сохраняется с FAIL вердиктом и пайплайн идёт дальше в Stage 3.

**Предлагаю:** Либо добавить `sys.exit(1)` после сообщения (строгий вариант), либо добавить `--allow-fc-fail` флаг для форсированного продолжения. По договорённости с Дашей — скорее всего блокировать по умолчанию, продолжать только с явным флагом. Это изменение кода нужно согласовать.

---

## Раздел: Phase B — максимум итераций FC

**В протоколе:**
> Минимум 1 попытка, максимум **2**: если на 2-й итерации FAIL — блокировать прогон

**В коде (default):**
```python
parser.add_argument("--max-fc-iterations", type=int, default=1, ...)
```
v32 запущен с `--max-fc-iterations 3` (2 ревизии Ghostwriter).

**Расхождение:** Протокол говорит максимум 2 итерации FC (1 ревизия), код v32 — 3 итерации FC (2 ревизии).

**Предлагаю:** Обновить протокол в соответствии с v32: «максимум 3 итерации FC (2 ревизии Ghostwriter), на 3-й финал без доп. правок». Это то, что Даша одобрила в задании v32.

---

## Раздел: Phase B — FC FAIL блокировка

**В протоколе:**
> Если на 2-й итерации FAIL — **блокировать прогон**, диагностика

**В коде:**
```python
# После цикла — просто сохраняет финальную книгу без sys.exit
final_path.write_text(...)
save_run_manifest(...)
```
Аналогично Stage 2 — блокировки нет. Книга сохраняется с FAIL вердиктом.

**Предлагаю:** Тот же подход что для Stage 2 — добавить блокировку или `--allow-fc-fail` флаг. Согласовать с Дашей.

---

## Раздел: Stage 3 — артефакт style_passport

**В протоколе:**
```
Артефакты в collab:
- style_passport_vXX.json
```

**В коде:**
`style_passport` сохраняется **внутри** `proofreader_report_{ts}.json` (поле `style_passport`), отдельный файл не создаётся.

**Предлагаю:** Обновить протокол — заменить `style_passport_vXX.json` на `proofreader_report_vXX.json (содержит style_passport)`. Или добавить в Stage 3 отдельное сохранение паспорта стиля если важна читаемость.

---

## Раздел: Артефакты — имена файлов

**В протоколе vs код:**

| Протокол | Реальное имя в коде |
|----------|---------------------|
| `stage1_manifest.json` | `karakulina_stage1_full_run_manifest_{ts}.json` |
| `stage2_manifest.json` | `karakulina_stage2_run_manifest_{ts}.json` |
| `stage3_manifest.json` | `{prefix}_stage3_run_manifest_{ts}.json` |
| `phase_b_manifest.json` | `{prefix}_phase_b_run_manifest_{ts}.json` |
| `historian_result_vXX.json` | `karakulina_historian_{ts}.json` |
| `book_draft_vXX.json` | `karakulina_book_draft_v1_{ts}.json` / `v2` / `v3` |
| `fc_report_iter1.json` | `karakulina_fc_report_iter1_{ts}.json` ✅ |
| `liteditor_report_vXX.json` | `{prefix}_liteditor_report_{ts}.json` ✅ |
| `style_passport_vXX.json` | ❌ не создаётся отдельно |
| `fact_map_phase_b_vXX.json` | `{prefix}_fact_map_phase_b_{ts}.json` ✅ |

**Предлагаю:** Привести протокол к реальным именам. Или договориться о едином шаблоне и применить в коде. Не критично, но мешает при ручном поиске артефактов.

---

## Что корректно в протоколе (подтверждено)

✅ **Pre-flight температуры** — все совпадают с конфигом
✅ **Stage 1 последовательность** — Cleaner → Fact Extractor верно
✅ **Stage 2 default max-fc-iterations=3** — верно для Stage 2
✅ **Stage 3 bio_data защита** — явная (строки 629–635 в test_stage3.py)
✅ **Stage 3 per-chapter порог 10000 симв.** — точное совпадение
✅ **Phase B affected_chapters** — только ch_02, ch_03, ch_04 (ch_01 и epilogue защищены)
✅ **Stage 4 paragraph-ref архитектура** — верное описание
✅ **6 ворот приёмки** — Gate 1, 2a, 2b, 2c, 3, 4 — структура верна
✅ **roles_checklist шаблон** — совпадает с созданным `_roles_checklist_template.md`

---

## Приоритетные правки

### Нужно исправить в коде (согласовать с Дашей):
1. **FC FAIL после max итераций → `sys.exit(1)` или `--allow-fc-fail`** (Stage 2 и Phase B)

### Нужно исправить в протоколе:
2. **Phase B max итераций**: 2 → 3 (обновить по v32)
3. **Историк**: «параллельно» → «последовательно, до Ghostwriter»; добавить упоминание pass2
4. **Layout промпты**: v1.9/v3.19 → v1.8/v3.14
5. **Артефакты**: привести имена к реальным
6. **style_passport**: уточнить что это поле внутри proofreader_report, не отдельный файл
7. **max_tokens**: добавить Historian=16000, FC=8000 как явное исключение

---

*Создан: 2026-04-21. Следующее обновление — после v32 и применения правок.*
