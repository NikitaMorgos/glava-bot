"""validate_layout_fidelity.py — валидатор соответствия layout_json ↔ book_FINAL.

Задача 017: ссылочная архитектура абзацев.

Три проверки:
  1. Completeness  — все (chapter_id, paragraph_ref) из book_FINAL есть в layout
  2. Order         — порядок абзацев внутри каждой главы совпадает с book_FINAL
  3. Uniqueness    — каждая (chapter_id, paragraph_ref) встречается ровно один раз

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


# ─── Конфигурация типов ref ──────────────────────────────────────────────────
#
# Каждый ключ — логический тип ref.
# elem_types    — допустимые значения поля "type" у layout-элемента.
# ref_fields    — имена полей ref в layout-элементе (первое непустое используется).
# book_path     — описание: откуда берутся ids в book (реализовано в _collect_book_refs).
#
# callout / historical_note добавятся в шаге 3.

REF_TYPE_CONFIG: dict[str, dict] = {
    "paragraph": {
        "elem_types": ("paragraph", "subheading", "section_header"),
        "ref_fields": ("paragraph_ref", "subheading_ref", "paragraph_id"),  # legacy last
        "book_path": "chapters[].paragraphs[]",  # fallback: content split by \n\n
    },
}


# ─── Внутренние helpers ───────────────────────────────────────────────────────

def _get_ref(elem: dict, ref_fields: tuple[str, ...]) -> str:
    """Возвращает первый непустой ref из списка полей."""
    for field in ref_fields:
        val = elem.get(field, "")
        if val:
            return val
    return ""


def _collect_book_refs(book: dict, ref_type: str) -> dict[str, list[str]]:
    """Возвращает {chapter_id: [ref, ...]} в порядке главы для заданного ref_type."""
    result: dict[str, list[str]] = {}

    if ref_type == "paragraph":
        for ch in book.get("chapters", []):
            ch_id = ch.get("id", "")
            if not ch_id:
                continue
            paras = ch.get("paragraphs")
            if paras:
                ids = [p["id"] for p in paras if p.get("id")]
            else:
                content = ch.get("content") or ""
                parts = [p.strip() for p in content.split("\n\n") if p.strip()]
                ids = [f"p{i + 1}" for i in range(len(parts))]
            if ids:
                result[ch_id] = ids

    return result


def _collect_layout_refs(layout: dict, ref_type: str) -> dict[str, list[tuple[int, str]]]:
    """Возвращает {chapter_id: [(page_number, ref), ...]} в порядке встречи в layout."""
    cfg = REF_TYPE_CONFIG[ref_type]
    elem_types: tuple[str, ...] = cfg["elem_types"]
    ref_fields: tuple[str, ...] = cfg["ref_fields"]

    result: dict[str, list[tuple[int, str]]] = defaultdict(list)
    pages = layout.get("pages") or layout.get("layout_instructions", {}).get("pages", [])
    for page in pages:
        page_num = page.get("page_number", 0)
        page_ch  = page.get("chapter_id", "")
        for elem in page.get("elements", []):
            if elem.get("type") not in elem_types:
                continue
            ref   = _get_ref(elem, ref_fields)
            el_ch = elem.get("chapter_id", "") or page_ch
            if ref and el_ch:
                result[el_ch].append((page_num, ref))
    return result


def _validate_ref_type(book: dict, layout: dict, ref_type: str) -> list[str]:
    """
    Выполняет completeness / order / uniqueness check для одного типа ref'ов.

    Возвращает список строк с ошибками (пустой список = всё ок).
    Префиксы ошибок: [COMPLETENESS], [ORDER], [UNIQUENESS].
    """
    errors: list[str] = []

    book_refs   = _collect_book_refs(book, ref_type)
    layout_refs = _collect_layout_refs(layout, ref_type)

    # Нормализуем: list of (page_num, ref) → just [ref]
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

    # Обратная проверка: лишние refs, которых нет в book
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
        common_expected = [pid for pid in expected_ids if pid in set(lo)]
        common_actual   = [pid for pid in lo if pid in set(expected_ids)]
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


# ─── Публичный API ────────────────────────────────────────────────────────────

def validate_fidelity(
    layout: dict,
    book: dict,
    allow_mismatch: bool = False,
    strict_mode: bool = True,
) -> tuple[bool, list[str]]:
    """
    Запускает три проверки для paragraph-ref'ов.

    Возвращает (passed: bool, errors: list[str]).
    Если allow_mismatch=True — ошибки логируются, но passed=True.
    """
    errors = _validate_ref_type(book, layout, "paragraph")

    book_refs = _collect_book_refs(book, "paragraph")

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
        total = sum(len(v) for v in book_refs.values())
        print(f"[FIDELITY] ✅ Проверки пройдены: {total} абзацев, порядок OK, нет дублей.")

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
    book_path   = Path(args.book)

    if not layout_path.exists():
        print(f"[ERROR] layout не найден: {layout_path}")
        sys.exit(1)
    if not book_path.exists():
        print(f"[ERROR] book не найден: {book_path}")
        sys.exit(1)

    layout = json.loads(layout_path.read_text(encoding="utf-8"))
    book   = json.loads(book_path.read_text(encoding="utf-8"))

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
