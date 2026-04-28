#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit-тесты для pipeline_quality_gates.py — gate_required_entities.

Три кейса покрывают фикс 2026-04-28:
  1. False positive «дочь тёти X» — племянник/племянница НЕ должны быть critical.
  2. bio_data scan — персона в bio_data.family должна считаться найденной (found_in=bio_data).
  3. sidebars scan — персона только в sidebars должна считаться найденной (found_in=sidebars).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline_quality_gates import gate_required_entities, _split_critical_optional_entities


# ──────────────────────────────────────────────────────────────────
# Вспомогательные фабрики
# ──────────────────────────────────────────────────────────────────

def _make_fact_map(persons: list[dict]) -> dict:
    return {
        "subject": {"name": "Иванова Мария Петровна"},
        "persons": persons,
    }


def _make_book(chapters: list[dict]) -> dict:
    return {"chapters": chapters}


def _ch(ch_id: str, content: str = "", bio_data: dict | None = None, sidebars: list | None = None) -> dict:
    ch: dict = {"id": ch_id, "title": ch_id, "order": 1, "content": content}
    if bio_data is not None:
        ch["bio_data"] = bio_data
    if sidebars is not None:
        ch["sidebars"] = sidebars
    return ch


# ──────────────────────────────────────────────────────────────────
# Тест 1: False positive «дочь тёти X»
#   Племянники/племянницы — relation содержит «дочь/сын тёти» →
#   НЕ должны попасть в critical_labels.
# ──────────────────────────────────────────────────────────────────

def test_indirect_relation_not_critical():
    """
    Рима и Толя — «племянница (дочь тёти Поли)» и «племянник (сын тёти Поли)».
    Слова «дочь» и «сын» встречаются как часть косвенного отношения.
    После фикса они должны быть optional, не critical.
    """
    persons = [
        {
            "id": "person_001",
            "name": "Рима",
            "relation_to_subject": "племянница (дочь тёти Поли)",
        },
        {
            "id": "person_002",
            "name": "Толя",
            "relation_to_subject": "племянник (сын тёти Поли)",
        },
        {
            "id": "person_003",
            "name": "Александр Иванов",
            "relation_to_subject": "муж",
        },
    ]
    fact_map = _make_fact_map(persons)
    critical, optional = _split_critical_optional_entities(fact_map)

    critical_labels = {e["label"] for e in critical}
    optional_labels = {e["label"] for e in optional}

    assert "Рима" not in critical_labels, "Рима (племянница) не должна быть critical"
    assert "Толя" not in critical_labels, "Толя (племянник) не должен быть critical"
    assert "Рима" in optional_labels, "Рима должна быть optional"
    assert "Толя" in optional_labels, "Толя должен быть optional"
    assert "Александр Иванов" in critical_labels, "Муж должен быть critical"

    print("✅ test_indirect_relation_not_critical PASSED")


# ──────────────────────────────────────────────────────────────────
# Тест 2: bio_data scan
#   Персона упомянута только в bio_data.family[], НЕ в нарративе →
#   gate должен пройти (found_in=bio_data).
# ──────────────────────────────────────────────────────────────────

def test_bio_data_family_scan():
    """
    Мать «Анна Петровна» — critical персона (relation=мать).
    В нарративе её нет, но она есть в bio_data.family[].value.
    Gate должен пройти, found_in=bio_data.
    """
    persons = [
        {
            "id": "person_m",
            "name": "Анна Петровна",
            "relation_to_subject": "мать",
        }
    ]
    fact_map = _make_fact_map(persons)

    bio_data = {
        "family": [
            {"label": "мать", "value": "Анна Петровна", "note": "ум. 1965"},
        ]
    }
    book = _make_book([
        _ch("ch_01", content="", bio_data=bio_data),
        _ch("ch_02", content="Текст главы о детстве без имён."),
    ])

    result = gate_required_entities(book, fact_map)
    assert result.passed, f"Gate должен пройти, critical_missing={result.details['critical_missing']}"
    matched = result.details.get("critical_matched", [])
    anna = next((m for m in matched if "Анна" in m["label"]), None)
    assert anna is not None, "Анна Петровна должна быть в matched"
    assert anna["found_in"] == "bio_data", f"Ожидался found_in=bio_data, получен {anna['found_in']}"

    print("✅ test_bio_data_family_scan PASSED")


# ──────────────────────────────────────────────────────────────────
# Тест 3: sidebars scan
#   Персона упомянута только в sidebars[], НЕ в нарративе и НЕ в bio_data →
#   gate должен пройти (found_in=sidebars).
# ──────────────────────────────────────────────────────────────────

def test_sidebars_scan():
    """
    Отец «Иван Сидоров» — critical (relation=отец).
    В нарративе и bio_data его нет, но он есть в sidebars[].content.
    Gate должен пройти, found_in=sidebars.
    """
    persons = [
        {
            "id": "person_f",
            "name": "Степан Кузнецов",
            "relation_to_subject": "отец",
        }
    ]
    fact_map = _make_fact_map(persons)

    sidebars = [
        {"title": "Справка о семье", "content": "Степан Кузнецов — отец героини, участник войны."}
    ]
    book = _make_book([
        _ch("ch_01", content="Иванова Мария Петровна родилась в 1920 году.", bio_data={}),
        _ch("ch_02", content="История без упоминания отца.", sidebars=sidebars),
    ])

    result = gate_required_entities(book, fact_map)
    assert result.passed, f"Gate должен пройти, critical_missing={result.details['critical_missing']}"
    matched = result.details.get("critical_matched", [])
    stepan = next((m for m in matched if "Степан" in m["label"]), None)
    assert stepan is not None, "Степан Кузнецов должен быть в matched"
    assert stepan["found_in"] == "sidebars", f"Ожидался found_in=sidebars, получен {stepan['found_in']}"

    print("✅ test_sidebars_scan PASSED")


# ──────────────────────────────────────────────────────────────────
# Тест 4 (регрессия): прямая «дочь» без косвенного маркера — остаётся critical
# ──────────────────────────────────────────────────────────────────

def test_direct_daughter_stays_critical():
    """
    Дочь субъекта с relation_to_subject='дочь' должна оставаться critical.
    Проверяем что фикс не ломает обратный случай.
    """
    persons = [
        {
            "id": "person_d",
            "name": "Татьяна Каракулина",
            "relation_to_subject": "дочь",
        }
    ]
    fact_map = _make_fact_map(persons)
    critical, optional = _split_critical_optional_entities(fact_map)
    critical_labels = {e["label"] for e in critical}
    assert "Татьяна Каракулина" in critical_labels, \
        "Прямая дочь субъекта должна оставаться critical"

    print("✅ test_direct_daughter_stays_critical PASSED")


if __name__ == "__main__":
    test_indirect_relation_not_critical()
    test_bio_data_family_scan()
    test_sidebars_scan()
    test_direct_daughter_stays_critical()
    print("\n✅ Все 4 теста прошли.")
