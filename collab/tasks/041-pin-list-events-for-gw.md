# Задача 041: Pin-list events для GW (Stage 2) + diff-валидация между прогонами

**Статус:** `outline` (полный spec после v57 verify)
**Номер:** 041
**Автор:** Опус
**Дата создания:** 2026-05-17
**Тип:** `промпт` (GW) + `cco-скрипт` (diff-валидация)
**Batch:** 2 (гибрид, после Batch 1 v57)
**Связано:** [architecture-stocktake-2026-05-17.md](../context/architecture-stocktake-2026-05-17.md) Класс 5 «Episode regression»; task 035 (CA pin-list для Stage 1)

---

## Контекст (кратко)

Task 035 ввёл pin-list events для **CA** (Stage 1) — выявляет какие эпизоды pin-list есть в fact_map. Но **GW (Stage 2) не получает pin-list** и не имеет обязательства развёрнуто рассказать каждый из них. Результат — между прогонами стохастика:
- v55 → v56 потеряло: операция на желудке 1960, хрущевское сокращение армии 1962, церковь во Власьево, разные отцы у В/П, раздел «строгость / забота / простые радости», масштаб трагедии 1933 (только мать)
- v56 → может потерять что-то новое если без guard

Это **Класс 5 stocktake**. Чисто GW проблема (Stage 2) — на Stage 1 эпизоды уже извлечены.

---

## Definition of Done

- ✅ Pin-list расширен → `known_episodes_karakulina.md` v2 (после Batch 1 verify): добавить операцию желудок, хрущевское сокращение, церковь Власьево, разные отцы В/П, масштаб трагедии 1933, шарлотку, тётю Машу-соседку, «французскую бабушку», продажу дачи, дороговизну 90-х.
- ✅ Промпт GW v2.19: новый раздел input `pin_list_events` — «обязательно развёрнуто рассказать в одной из глав; если эпизод отсутствует — flag в revision_log».
- ✅ Stage 2 runner передаёт pin_list_events в GW input.
- ✅ Скрипт `validate_pin_list_coverage(book, pin_list) -> report`:
  - Для каждого pin_list эпизода — поиск маркеров (grep по `markers` из pin-list) в book
  - Возвращает `[{episode_id, found: true/false, chapter_id, snippet}]`
- ✅ Скрипт `diff_episodes_between_versions(book_v_N, book_v_N-1, pin_list) -> report`:
  - Сравнивает coverage v_N и v_(N-1)
  - Flag если v_N теряет ≥3 эпизода из pin_list которые были в v_(N-1)
- ✅ Tests + integration: v56 baseline, v57/v58 сравнение

---

## Что финализировать после v57

- Pin-list v2 пишет Опус после v57 verify (когда видно какие новые эпизоды стали доступны через subject_age + ASR normalize).
- Дашин review pin-list v2 перед implementation task 041 (продактовое решение по списку «обязательно в книге»).
- Threshold «≥3 регрессий = flag» — обсудить с Дашей.

---

## История статусов

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-17 | `outline` | Опус |
