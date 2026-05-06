"""validate_layout_fidelity.py — валидатор соответствия layout_json ↔ book_FINAL.

Задача 017: ссылочная архитектура. Параметризован по типу ref (волна 1.1):
- "paragraph"        — paragraphs[].id (включая subheading/section_header элементы)
- "callout"          — book.callouts[] top-level
- "historical_note"  — book.historical_notes[] top-level

Три проверки на каждый ref-тип:
  1. Completeness  — все (chapter_id, ref) из book_FINAL есть в layout
  2. Order         — порядок refs внутри главы совпадает с book_FINAL
  3. Uniqueness    — каждая (chapter_id, ref) встречается ровно один раз

Флаги:
  --allow-mismatch    не падать, только предупреждать
  --skip-fidelity-check  полностью пропустить проверку (аварийный режим)

Exit codes:
  0 — все проверки прошли
  1 — ошибки найдены (и --allow-mismatch не задан)
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent.parent


# ──────────────────────────────────────────────────────────────────
# Конфигурация типов ref
# ──────────────────────────────────────────────────────────────────
# elem_types          — tuple допустимых значений поля "type" в layout-элементе
#                       (paragraph включает subheading и section_header — task 025)
# ref_fields          — поля ref в порядке приоритета (новый → legacy)
# book_path           — документационная метка пути в book_FINAL
# book_collection     — имя коллекции (paragraphs / callouts / historical_notes)
# book_top_level      — True: коллекция на top-level book, items имеют chapter_id
#                       False: коллекция внутри каждого chapter
# book_split_content  — fallback (только для paragraph): если paragraphs[] нет,
#                       разбивать chapter.content по \n\n и генерить id p1, p2, ...
REF_TYPE_CONFIG: dict[str, dict] = {
    "paragraph": {
        "elem_types": ("paragraph", "subheading", "section_header"),
        "ref_fields": ("paragraph_ref", "subheading_ref", "paragraph_id"),
        "book_path": "chapters[].paragraphs[]",
        "book_collection": "paragraphs",
        "book_top_level": False,
        "book_split_content": True,
    },
    "callout": {
        "elem_types": ("callout",),
        "ref_fields": ("callout_ref", "callout_id"),
        "book_path": "callouts[] (top-level, grouped by chapter_id)",
        "book_collection": "callouts",
        "book_top_level": True,
        "book_split_content": False,
    },
    "historical_note": {
        "elem_types": ("historical_note",),
        "ref_fields": ("historical_note_ref", "note_ref", "note_id"),
        "book_path": "historical_notes[] (top-level, grouped by chapter_id)",
        "book_collection": "historical_notes",
        "book_top_level": True,
        "book_split_content": False,
    },
}


def _get_ref(elem: dict, ref_fields: tuple[str, ...]) -> str:
    """Возвращает значение первого непустого ref-поля из заданных."""
    for field in ref_fields:
        value = elem.get(field, "")
        if value:
            return value
    return ""


def _collect_book_refs(book: dict, ref_type: str) -> dict[str, list[str]]:
    """
    Возвращает {chapter_id: [ref, ...]} в порядке появления для заданного ref_type.

    paragraph: читает chapters[].paragraphs[].id; если коллекции нет —
    fallback split по \\n\\n с генерацией id p1, p2, ... (legacy совместимость).
    callout / historical_note: читает book.<collection>[] (top-level), группирует
    по полю chapter_id каждого item, сохраняя относительный порядок в исходном массиве.
    """
    cfg = REF_TYPE_CONFIG[ref_type]
    collection_key = cfg["book_collection"]
    top_level = cfg.get("book_top_level", False)
    split_content = cfg.get("book_split_content", False)

    result: dict[str, list[str]] = {}

    if top_level:
        # callouts / historical_notes — список на top-level, item имеет chapter_id
        items = book.get(collection_key, []) or []
        for item in items:
            ch_id = item.get("chapter_id", "")
            iid = item.get("id")
            if ch_id and iid:
                result.setdefault(ch_id, []).append(iid)
        return result

    # paragraphs (или другие nested-в-chapter коллекции)
    for ch in book.get("chapters", []):
        ch_id = ch.get("id", "")
        if not ch_id:
            continue
        items = ch.get(collection_key)
        if items:
            ids = [item["id"] for item in items if item.get("id")]
        elif split_content:
            content = ch.get("content") or ""
            parts = [p.strip() for p in content.split("\n\n") if p.strip()]
            ids = [f"p{i + 1}" for i in range(len(parts))]
        else:
            ids = []
        if ids:
            result[ch_id] = ids
    return result


def _collect_layout_refs(layout: dict, ref_type: str) -> dict[str, list[tuple[int, str]]]:
    """
    Возвращает {chapter_id: [(page_number, ref), ...]} для заданного ref_type.
    Игнорирует элементы других типов и элементы без ref / без chapter_id.
    """
    cfg = REF_TYPE_CONFIG[ref_type]
    elem_types: tuple[str, ...] = cfg["elem_types"]
    ref_fields: tuple[str, ...] = cfg["ref_fields"]

    result: dict[str, list[tuple[int, str]]] = defaultdict(list)
    pages = layout.get("pages") or layout.get("layout_instructions", {}).get("pages", [])
    for page in pages:
        page_num = page.get("page_number", 0)
        page_ch = page.get("chapter_id", "")
        for elem in page.get("elements", []):
            if elem.get("type") not in elem_types:
                continue
            ref = _get_ref(elem, ref_fields)
            el_ch = elem.get("chapter_id", "") or page_ch
            if ref and el_ch:
                result[el_ch].append((page_num, ref))
    return result


def _validate_ref_type(book: dict, layout: dict, ref_type: str) -> list[str]:
    """
    Запускает три проверки (completeness/order/uniqueness) для одного типа ref.

    Возвращает список текстовых ошибок. Префиксы [COMPLETENESS]/[ORDER]/[UNIQUENESS]
    зафиксированы как часть API — на них завязаны тесты и логи.
    """
    if ref_type not in REF_TYPE_CONFIG:
        raise ValueError(f"Неизвестный ref_type: {ref_type!r}. "
                         f"Поддерживаются: {list(REF_TYPE_CONFIG)}")

    errors: list[str] = []

    book_refs = _collect_book_refs(book, ref_type)
    layout_refs = _collect_layout_refs(layout, ref_type)

    # Normalise layout_refs: list of (page_num, ref) → just [ref]
    layout_refs_ordered: dict[str, list[str]] = {
        ch_id: [ref for _, ref in entries]
        for ch_id, entries in layout_refs.items()
    }

    # ── Проверка 1: Completeness ──────────────────────────────────────────────
    for ch_id, expected_ids in book_refs.items():
        layout_ids_set = set(layout_refs_ordered.get(ch_id, []))
        for pid in expected_ids:
            if pid not in layout_ids_set:
                errors.append(
                    f"[COMPLETENESS] {ch_id}/{pid} — отсутствует в layout"
                )

    # Обратная проверка: лишние refs которых нет в book
    for ch_id, layout_ids in layout_refs_ordered.items():
        book_ids_set = set(book_refs.get(ch_id, []))
        for pid in layout_ids:
            if pid not in book_ids_set:
                errors.append(
                    f"[COMPLETENESS] {ch_id}/{pid} — лишний ref (нет в book_FINAL)"
                )

    # ── Проверка 2: Order ─────────────────────────────────────────────────────
    for ch_id, expected_ids in book_refs.items():
        lo = layout_refs_ordered.get(ch_id, [])
        # Берём только те, что есть и там и там, проверяем относительный порядок
        common_expected = [pid for pid in expected_ids if pid in set(lo)]
        common_actual = [pid for pid in lo if pid in set(expected_ids)]
        if common_expected != common_actual:
            errors.append(
                f"[ORDER] {ch_id}: порядок абзацев не совпадает с book_FINAL. "
                f"Ожидалось: {common_expected}, в layout: {common_actual}"
            )

    # ── Проверка 3: Uniqueness ────────────────────────────────────────────────
    for ch_id, lo in layout_refs_ordered.items():
        seen: dict[str, int] = {}
        for pid in lo:
            seen[pid] = seen.get(pid, 0) + 1
        for pid, count in seen.items():
            if count > 1:
                errors.append(
                    f"[UNIQUENESS] {ch_id}/{pid} — встречается {count} раза в layout (дубль)"
                )

    return errors


def _inject_ref_type_label(err: str, ref_type: str) -> str:
    """Добавляет [<ref_type>] после ярлыка категории: '[COMPLETENESS] ch_02/p1 ...' →
    '[COMPLETENESS][callout] ch_02/p1 ...'. Для paragraph оставляет без ярлыка
    ради backward compatibility с тестами и логами."""
    if ref_type == "paragraph":
        return err
    for tag in ("[COMPLETENESS]", "[ORDER]", "[UNIQUENESS]"):
        if err.startswith(tag):
            return err.replace(tag, f"{tag}[{ref_type}]", 1)
    return f"[{ref_type}] {err}"


def validate_fidelity(
    layout: dict,
    book: dict,
    allow_mismatch: bool = False,
    strict_mode: bool = True,
) -> tuple[bool, list[str]]:
    """
    Запускает три проверки (completeness/order/uniqueness) для всех типов
    ref из REF_TYPE_CONFIG: paragraph, callout, historical_note.

    Возвращает (passed: bool, errors: list[str]).
    Если allow_mismatch=True — ошибки логируются, но passed=True.

    Префиксы ошибок дополнены типом: [COMPLETENESS][callout] / [ORDER][historical_note] / etc.
    Для paragraph — без ярлыка (backward compatibility с существующими тестами/логами).
    """
    errors: list[str] = []
    counts: dict[str, int] = {}

    for ref_type in REF_TYPE_CONFIG:
        type_errors = _validate_ref_type(book, layout, ref_type)
        prefixed = [_inject_ref_type_label(e, ref_type) for e in type_errors]
        errors.extend(prefixed)
        counts[ref_type] = sum(len(v) for v in _collect_book_refs(book, ref_type).values())

    passed = len(errors) == 0
    if errors:
        prefix = "[WARN]" if allow_mismatch else "[ERROR]"
        for e in errors:
            print(f"{prefix} {e}")
        if not allow_mismatch:
            print(f"\n[FIDELITY] ❌ Найдено {len(errors)} нарушений.")
        else:
            print(f"\n[FIDELITY] ⚠️  {len(errors)} нарушений (--allow-mismatch: пропускаем).")
    else:
        summary = ", ".join(f"{n} {t}" for t, n in counts.items() if n)
        print(f"[FIDELITY] ✅ Проверки пройдены: {summary or '0 элементов'}, порядок OK, нет дублей.")

    if allow_mismatch:
        return True, errors
    return passed, errors


def main():
    parser = argparse.ArgumentParser(description="Валидатор соответствия layout ↔ book_FINAL (задача 017)")
    parser.add_argument("--layout", required=True, help="Путь к layout JSON (pages_json)")
    parser.add_argument("--book", required=True, help="Путь к book_FINAL.json (stage3 или stage2)")
    parser.add_argument("--allow-mismatch", action="store_true",
                        help="Предупреждать о нарушениях но не падать")
    parser.add_argument("--skip-fidelity-check", action="store_true",
                        help="Пропустить все проверки (аварийный режим)")
    args = parser.parse_args()

    if args.skip_fidelity_check:
        print("[FIDELITY] ⚠️  --skip-fidelity-check: все проверки пропущены.")
        sys.exit(0)

    layout_path = Path(args.layout)
    book_path = Path(args.book)

    if not layout_path.exists():
        print(f"[ERROR] layout не найден: {layout_path}")
        sys.exit(1)
    if not book_path.exists():
        print(f"[ERROR] book не найден: {book_path}")
        sys.exit(1)

    layout = json.loads(layout_path.read_text(encoding="utf-8"))
    book = json.loads(book_path.read_text(encoding="utf-8"))

    # Нормализуем paragraph IDs через prepare_book_for_layout
    try:
        sys.path.insert(0, str(ROOT))
        from pipeline_utils import prepare_book_for_layout as _prep
        book = _prep(book)
    except Exception as e:
        print(f"[FIDELITY] ⚠️  prepare_book_for_layout недоступен: {e} — используем raw paragraphs")

    print(f"[FIDELITY] Layout:  {layout_path.name}")
    print(f"[FIDELITY] Book:    {book_path.name}")

    passed, _errors = validate_fidelity(
        layout,
        book,
        allow_mismatch=args.allow_mismatch,
    )

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
