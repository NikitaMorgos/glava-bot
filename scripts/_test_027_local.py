#!/usr/bin/env python3
"""
Unit tests for Task 027: enforce_bio_data_completeness in pipeline_utils.py

Run: python scripts/_test_027_local.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline_utils import enforce_bio_data_completeness

PASS = "PASS"
FAIL = "FAIL"
results = []


def run(name, fn):
    try:
        fn()
        print(f"  [{PASS}] {name}")
        results.append(True)
    except AssertionError as e:
        print(f"  [{FAIL}] {name}: {e}")
        results.append(False)
    except Exception as e:
        print(f"  [{FAIL}] {name}: unexpected {type(e).__name__}: {e}")
        results.append(False)


def _book(family):
    return {
        "chapters": [{
            "id": "ch_01",
            "bio_data": {"family": family}
        }]
    }


def _fm(persons):
    return {"persons": persons}


print("\n=== Task 027: enforce_bio_data_completeness ===\n")

# Test 1: auto-fill срабатывает для персон с тётя/дядя в имени
def test_autofill_by_name_marker():
    book = _book([
        {"label": "Муж", "value": "Дмитрий Каракулин"},
    ])
    fm = _fm([
        {"name": "тётя Шура", "relation": None},
        {"name": "тётя Маня", "relation": None},
        {"name": "Нинвана Полсачева", "relation": None},  # not family by name
    ])
    result = enforce_bio_data_completeness(book, fm, strict=False)
    family = result["chapters"][0]["bio_data"]["family"]
    names = [e["value"] for e in family]
    assert "тётя Шура" in names, f"тётя Шура missing, got {names}"
    assert "тётя Маня" in names, f"тётя Маня missing, got {names}"
    assert "Нинвана Полсачева" not in names, f"Нинвана should not be auto-filled"
    for e in family:
        if e.get("source") == "auto-filled":
            assert e.get("source") == "auto-filled"

run("auto-fill срабатывает для тётя/дядя в имени", test_autofill_by_name_marker)


# Test 2: strict=True → raise вместо auto-fill
def test_strict_raises():
    book = _book([])
    fm = _fm([{"name": "тётя Шура", "relation": None}])
    try:
        enforce_bio_data_completeness(book, fm, strict=True)
        assert False, "Должно было вызвать RuntimeError"
    except RuntimeError as e:
        assert "STRICT" in str(e), f"Unexpected error text: {e}"

run("strict=True вызывает RuntimeError", test_strict_raises)


# Test 3: нормальный проход — уже упомянутые персоны не дублируются
def test_already_mentioned_not_duplicated():
    book = _book([
        {"label": "Муж", "value": "Дмитрий Каракулин, военный"},
        {"label": "Дети", "value": "Валерий (р. 1948), Татьяна (р. 1956)"},
        {"label": "тётя", "value": "тётя Шура"},
    ])
    fm = _fm([
        {"name": "Каракулин Дмитрий", "relation": None},
        {"name": "Каракулин Валерий", "relation": None},
        {"name": "тётя Шура", "relation": None},
    ])
    result = enforce_bio_data_completeness(book, fm, strict=False)
    family = result["chapters"][0]["bio_data"]["family"]
    # Count entries — no duplicates
    assert len(family) == 3, f"Ожидалось 3 записи, получили {len(family)}: {[e['value'] for e in family]}"

run("уже упомянутые персоны не дублируются", test_already_mentioned_not_duplicated)


# Test 4: пустой fact_map → no changes
def test_empty_fact_map():
    book = _book([{"label": "Муж", "value": "Дмитрий"}])
    fm = _fm([])
    result = enforce_bio_data_completeness(book, fm)
    family = result["chapters"][0]["bio_data"]["family"]
    assert len(family) == 1, f"Ожидалась 1 запись, получили {len(family)}"

run("empty fact_map - no changes", test_empty_fact_map)


# Test 5: bio_data отсутствует → создаётся
def test_missing_bio_data_created():
    book = {"chapters": [{"id": "ch_01"}]}
    fm = _fm([{"name": "тётя Маня", "relation": None}])
    result = enforce_bio_data_completeness(book, fm, strict=False)
    ch01 = result["chapters"][0]
    assert "bio_data" in ch01, "bio_data не создана"
    family = ch01["bio_data"].get("family", [])
    names = [e["value"] for e in family]
    assert "тётя Маня" in names, f"тётя Маня отсутствует, got {names}"

run("bio_data missing - created and filled", test_missing_bio_data_created)


# Test 6: relation="?" + нет маркера в имени → не добавляется
def test_non_family_with_unknown_relation_skipped():
    book = _book([])
    fm = _fm([
        {"name": "Нинвана Полсачева", "relation": "?"},
        {"name": "Маргось Владимир", "relation": None},
    ])
    result = enforce_bio_data_completeness(book, fm, strict=False)
    family = result["chapters"][0]["bio_data"]["family"]
    names = [e["value"] for e in family]
    assert "Нинвана Полсачева" not in names, "Нинвана не должна быть в family (нет маркера)"
    assert "Маргось Владимир" not in names, "Маргось не должен быть в family (нет маркера)"

run("relation='?' + no marker in name -> not auto-filled", test_non_family_with_unknown_relation_skipped)


# Test 7: relation = семейное слово (даже при наличии маркера в имени)
def test_relation_based_detection():
    book = _book([])
    fm = _fm([
        {"name": "Рудай Иван Андреевич", "relation": "отец"},
        {"name": "Рудая Пелагея", "relation": "мать"},
    ])
    result = enforce_bio_data_completeness(book, fm, strict=False)
    family = result["chapters"][0]["bio_data"]["family"]
    names = [e["value"] for e in family]
    assert "Рудай Иван Андреевич" in names, "Отец должен быть auto-filled"
    assert "Рудая Пелагея" in names, "Мать должна быть auto-filled"
    # Labels match relation
    for e in family:
        if e["value"] == "Рудай Иван Андреевич":
            assert e["label"] == "отец", f"Label: {e['label']}"

run("relation=family word -> auto-fill with correct label", test_relation_based_detection)


# Summary
total = len(results)
passed = sum(results)
failed = total - passed
print(f"\n{'='*40}")
print(f"Total: {passed}/{total} PASS", f"| {failed} FAIL" if failed else "")
if failed:
    sys.exit(1)
