#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
compare_persons_across_runs.py — сравнение persons[] между двумя прогонами fact_map.

Используется для регрессионного тестирования стабильности Fact Extractor:
  — Какие персоны появились в run B, которых не было в run A
  — Какие исчезли (были в A, нет в B)
  — Какие есть в обоих прогонах

Это инструмент из задачи 014 (Completeness Auditor + Name Normalizer).
Критерий приёмки: не более 1–2 пропущенных персон между двумя прогонами.

Использование:
  python scripts/compare_persons_across_runs.py \\
      --run-a collab/runs/fact_map_full_v32.json \\
      --run-b collab/runs/fact_map_full_v35.json \\
      [--output report.json]
"""

import argparse
import json
import sys
from pathlib import Path
from typing import NamedTuple


class PersonEntry(NamedTuple):
    id: str
    name: str
    aliases: frozenset
    relation: str


def _load_persons(fact_map_path: Path) -> list[PersonEntry]:
    data = json.loads(fact_map_path.read_text(encoding="utf-8"))
    persons = []
    for p in data.get("persons", []):
        aliases = frozenset(a.lower() for a in (p.get("aliases") or []))
        persons.append(PersonEntry(
            id=p.get("id", ""),
            name=p.get("name", ""),
            aliases=aliases,
            relation=p.get("relation_to_subject", ""),
        ))
    return persons


def _names_match(a: PersonEntry, b: PersonEntry) -> bool:
    """
    Проверяет, является ли a и b одной и той же персоной.
    Матч по: точное имя, имя в aliases другого, пересечение aliases.
    Без учёта регистра.
    """
    a_name_l = a.name.lower()
    b_name_l = b.name.lower()
    if a_name_l == b_name_l:
        return True
    if a_name_l in b.aliases or b_name_l in a.aliases:
        return True
    if a.aliases & b.aliases:
        return True
    return False


def compare_persons(persons_a: list[PersonEntry], persons_b: list[PersonEntry]) -> dict:
    """
    Сравнивает два списка персон.
    Возвращает:
      {
        "in_both": [...],   — нашлись в обоих прогонах
        "only_in_a": [...], — потеряны в B (регрессия!)
        "only_in_b": [...], — добавились в B (обогащение)
        "match_count": N,
        "total_a": N,
        "total_b": N,
        "stability_score": 0..1  — доля A-персон, которые есть в B
      }
    """
    in_both: list[dict] = []
    only_in_a: list[dict] = []
    only_in_b: list[dict] = []

    matched_b_indices: set[int] = set()

    for pa in persons_a:
        found = False
        for idx_b, pb in enumerate(persons_b):
            if idx_b in matched_b_indices:
                continue
            if _names_match(pa, pb):
                in_both.append({
                    "run_a": {"id": pa.id, "name": pa.name, "relation": pa.relation},
                    "run_b": {"id": pb.id, "name": pb.name, "relation": pb.relation},
                })
                matched_b_indices.add(idx_b)
                found = True
                break
        if not found:
            only_in_a.append({"id": pa.id, "name": pa.name, "relation": pa.relation})

    for idx_b, pb in enumerate(persons_b):
        if idx_b not in matched_b_indices:
            only_in_b.append({"id": pb.id, "name": pb.name, "relation": pb.relation})

    stability = len(in_both) / len(persons_a) if persons_a else 1.0

    return {
        "in_both": in_both,
        "only_in_a": only_in_a,
        "only_in_b": only_in_b,
        "match_count": len(in_both),
        "total_a": len(persons_a),
        "total_b": len(persons_b),
        "stability_score": round(stability, 3),
    }


def print_report(result: dict, path_a: Path, path_b: Path) -> None:
    print("=" * 60)
    print(f"СРАВНЕНИЕ ПЕРСОН МЕЖДУ ПРОГОНАМИ")
    print(f"  Run A: {path_a.name}  ({result['total_a']} персон)")
    print(f"  Run B: {path_b.name}  ({result['total_b']} персон)")
    print("=" * 60)

    score = result["stability_score"]
    score_str = f"{score:.0%}"
    if score >= 0.9:
        verdict = "✅ СТАБИЛЬНО"
    elif score >= 0.75:
        verdict = "⚠️  НЕЗНАЧИТЕЛЬНЫЕ ПОТЕРИ"
    else:
        verdict = "🔴 РЕГРЕССИЯ"
    print(f"\nStability Score: {score_str}  {verdict}")
    print(f"Совпадают: {result['match_count']} / {result['total_a']}")

    if result["only_in_a"]:
        print(f"\n🔴 ПОТЕРЯНЫ в B ({len(result['only_in_a'])} персон):")
        for p in result["only_in_a"]:
            rel = f"  [{p['relation']}]" if p["relation"] else ""
            print(f"  — {p['name']}{rel}")
    else:
        print("\n✅ Не потеряно ни одной персоны из Run A")

    if result["only_in_b"]:
        print(f"\n🟢 ДОБАВЛЕНЫ в B ({len(result['only_in_b'])} персон):")
        for p in result["only_in_b"]:
            rel = f"  [{p['relation']}]" if p["relation"] else ""
            print(f"  + {p['name']}{rel}")

    print("\nСОВПАДАЮЩИЕ:")
    for pair in result["in_both"]:
        a_name = pair["run_a"]["name"]
        b_name = pair["run_b"]["name"]
        name_diff = f" (B: '{b_name}')" if a_name != b_name else ""
        print(f"  ✓ {a_name}{name_diff}")

    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Сравнение persons[] между двумя прогонами fact_map"
    )
    parser.add_argument("--run-a", required=True, help="Путь к fact_map прогона A (baseline)")
    parser.add_argument("--run-b", required=True, help="Путь к fact_map прогона B (сравниваемый)")
    parser.add_argument("--output", default=None, help="Сохранить JSON-отчёт (опционально)")
    parser.add_argument("--fail-on-loss", type=int, default=None,
                        help="Завершить с кодом 1 если потеряно > N персон (для CI)")
    args = parser.parse_args()

    path_a = Path(args.run_a)
    path_b = Path(args.run_b)

    if not path_a.exists():
        print(f"[ERROR] Не найден: {path_a}"); sys.exit(1)
    if not path_b.exists():
        print(f"[ERROR] Не найден: {path_b}"); sys.exit(1)

    persons_a = _load_persons(path_a)
    persons_b = _load_persons(path_b)

    result = compare_persons(persons_a, persons_b)
    print_report(result, path_a, path_b)

    if args.output:
        out_path = Path(args.output)
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n[SAVED] {out_path}")

    if args.fail_on_loss is not None:
        lost = len(result["only_in_a"])
        if lost > args.fail_on_loss:
            print(f"\n[FAIL] Потеряно {lost} персон > порога {args.fail_on_loss}")
            sys.exit(1)


if __name__ == "__main__":
    main()
