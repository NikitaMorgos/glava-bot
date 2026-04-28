#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pipeline_quality_gates.py — строгие quality-gates для стабилизации пайплайна.

Назначение:
  - Stage2/Stage3: блокирующие проверки текста (обязательные сущности, повторы, пустые поля)
  - Stage4: preflight PDF + структурные проверки layout/page_map
  - Regression suite: единый набор проверок перед approve чекпоинтов
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Zа-яА-ЯёЁ0-9]+", _norm(text))


def _chapter_texts(book: dict) -> list[dict]:
    out: list[dict] = []
    for ch in book.get("chapters", []) or []:
        out.append(
            {
                "id": ch.get("id", ""),
                "title": ch.get("title", ""),
                "content": ch.get("content") or "",
                "bio_data": ch.get("bio_data"),
            }
        )
    return out


def _content_join(book: dict) -> str:
    return "\n".join(ch["content"] for ch in _chapter_texts(book))


def _entity_variants(name: str) -> list[str]:
    """
    Генерирует простые варианты поиска по сущности:
      - полная форма
      - слова длиной >= 4
    """
    n = _norm(name)
    words = [w for w in _tokenize(n) if len(w) >= 4]
    variants = [n] + words
    # remove duplicates keeping order
    seen = set()
    uniq = []
    for v in variants:
        if v and v not in seen:
            seen.add(v)
            uniq.append(v)
    return uniq


def collect_required_entities(fact_map: dict) -> list[dict]:
    """
    Обязательные сущности для проверки текста:
      - subject.name
      - все persons[].name
    """
    entities: list[dict] = []
    subject_name = (fact_map.get("subject", {}) or {}).get("name")
    if subject_name:
        entities.append({"type": "subject", "label": subject_name, "variants": _entity_variants(subject_name)})

    for p in fact_map.get("persons", []) or []:
        name = (p or {}).get("name")
        if not name:
            continue
        entities.append({"type": "person", "label": name, "variants": _entity_variants(name)})
    return entities


def _relation_text(person: dict) -> str:
    chunks = [
        str(person.get("relation_to_subject") or ""),
        str(person.get("relation") or ""),
        str(person.get("role") or ""),
        str(person.get("note") or ""),
    ]
    return _norm(" ".join(chunks))


def _contains_place_relaxed(text: str, place: str) -> bool:
    """
    Нечёткая проверка места: совпадение хотя бы по значимым токенам/основам.
    """
    ntext = _norm(text)
    nplace = _norm(place)
    if not nplace:
        return True
    if nplace in ntext:
        return True
    place_tokens = [t for t in _tokenize(nplace) if len(t) >= 5]
    if not place_tokens:
        return True
    # Достаточно совпадения 2 токенов или 1 при коротком месте
    hits = 0
    for t in place_tokens:
        stem = t[:6] if len(t) > 6 else t
        if stem and stem in ntext:
            hits += 1
    threshold = 2 if len(place_tokens) >= 2 else 1
    return hits >= threshold


def _split_critical_optional_entities(fact_map: dict) -> tuple[list[dict], list[dict]]:
    """
    Делит сущности на блокирующие (critical) и предупреждающие (optional).

    Блокирующие:
      - subject
      - близкие родственники по relation/role
      - fallback: первые 5 персон, если relation-поля пустые
    """
    all_entities = collect_required_entities(fact_map)
    subject_entities = [e for e in all_entities if e["type"] == "subject"]
    persons = fact_map.get("persons", []) or []
    person_entities = [e for e in all_entities if e["type"] == "person"]

    critical_keywords = [
        "мать", "отец", "муж", "жена", "сын", "дочь", "сестра", "брат",
        "мама", "папа", "бабушка", "дедушка",
        "mother", "father", "husband", "wife", "son", "daughter", "sister", "brother",
    ]

    critical_labels = set()
    for p in persons:
        name = (p or {}).get("name")
        if not name:
            continue
        rel = _relation_text(p or {})
        if any(k in rel for k in critical_keywords):
            critical_labels.add(name)

    critical: list[dict] = []
    optional: list[dict] = []
    for e in subject_entities + person_entities:
        if e["type"] == "subject" or e["label"] in critical_labels:
            critical.append(e)
        else:
            optional.append(e)
    return critical, optional


def _contains_any(text: str, variants: list[str]) -> bool:
    ntext = _norm(text)
    return any(v in ntext for v in variants if v)


@dataclass
class GateResult:
    passed: bool
    name: str
    details: dict

    def as_dict(self) -> dict:
        return {"gate": self.name, "passed": self.passed, **self.details}


def gate_required_entities(book: dict, fact_map: dict) -> GateResult:
    text = _content_join(book)
    critical_entities, optional_entities = _split_critical_optional_entities(fact_map)
    missing_critical = []
    missing_optional = []
    matched_critical = 0
    matched_optional = 0

    for e in critical_entities:
        if _contains_any(text, e["variants"]):
            matched_critical += 1
        else:
            missing_critical.append({"type": e["type"], "label": e["label"], "variants": e["variants"][:4]})

    for e in optional_entities:
        if _contains_any(text, e["variants"]):
            matched_optional += 1
        else:
            missing_optional.append({"type": e["type"], "label": e["label"], "variants": e["variants"][:4]})

    return GateResult(
        passed=(len(missing_critical) == 0),
        name="required_entities",
        details={
            "required_total": len(critical_entities) + len(optional_entities),
            "critical_total": len(critical_entities),
            "critical_matched_total": matched_critical,
            "critical_missing_total": len(missing_critical),
            "critical_missing": missing_critical,
            "optional_total": len(optional_entities),
            "optional_matched_total": matched_optional,
            "optional_missing_total": len(missing_optional),
            "optional_missing": missing_optional,
        },
    )


def _ngrams(tokens: list[str], n: int) -> set[tuple[str, ...]]:
    if len(tokens) < n:
        return set()
    return {tuple(tokens[i : i + n]) for i in range(0, len(tokens) - n + 1)}


def gate_repetition_overlap(book: dict, ngram_size: int = 5, threshold: float = 0.20) -> GateResult:
    chapters = _chapter_texts(book)
    overlaps = []
    for i in range(len(chapters)):
        for j in range(i + 1, len(chapters)):
            a = _ngrams(_tokenize(chapters[i]["content"]), ngram_size)
            b = _ngrams(_tokenize(chapters[j]["content"]), ngram_size)
            if not a or not b:
                continue
            inter = len(a & b)
            denom = max(1, min(len(a), len(b)))
            ratio = inter / denom
            if ratio >= threshold:
                overlaps.append(
                    {
                        "ch_a": chapters[i]["id"] or f"idx_{i}",
                        "ch_b": chapters[j]["id"] or f"idx_{j}",
                        "overlap_ratio": round(ratio, 4),
                    }
                )
    return GateResult(
        passed=(len(overlaps) == 0),
        name="cross_chapter_repetition",
        details={"ngram_size": ngram_size, "threshold": threshold, "violations": overlaps},
    )


def gate_ch01_bio_not_empty(book: dict, fact_map: dict, min_chars: int = 300) -> GateResult:
    subject = fact_map.get("subject", {}) or {}
    ch01 = None  # normalized
    ch01_raw = None  # original chapter dict
    for raw_ch in book.get("chapters", []) or []:
        if (raw_ch or {}).get("id") == "ch_01":
            ch01_raw = raw_ch
            ch01 = {
                "id": raw_ch.get("id", ""),
                "content": raw_ch.get("content") or "",
            }
            break
    if ch01 is None:
        return GateResult(False, "ch01_bio", {"reason": "chapter ch_01 is missing"})

    content = ch01["content"]
    birth_year = str(subject.get("birth_year") or "")
    birth_place = _norm(subject.get("birth_place") or "")
    global_text = _norm(_content_join(book))
    ch01_blob = _norm(json.dumps(ch01_raw or {}, ensure_ascii=False))
    has_bio_struct = bool((ch01_raw or {}).get("bio_data")) or ("timeline" in ch01_blob)

    checks = {
        "content_len_ok": (len(content) >= min_chars) or has_bio_struct,
        "has_birth_year": ((birth_year in content) or (birth_year in ch01_blob) or (birth_year in global_text)) if birth_year else True,
        "has_birth_place": (
            _contains_place_relaxed(content, birth_place)
            or _contains_place_relaxed(ch01_blob, birth_place)
            or _contains_place_relaxed(global_text, birth_place)
        ) if birth_place else True,
    }
    passed = all(checks.values())
    return GateResult(
        passed,
        "ch01_bio",
        {
            "min_chars": min_chars,
            "actual_chars": len(content),
            "has_bio_struct": has_bio_struct,
            "checks": checks,
        },
    )


def gate_non_empty_book(book: dict, min_chapter_chars: int = 120) -> GateResult:
    chapters = _chapter_texts(book)
    issues = []
    if not chapters:
        issues.append({"issue": "no_chapters"})
    for ch in chapters:
        content = ch["content"]
        # ch_01 may use bio_data structure instead of text content — skip content check if bio_data present
        if ch.get("id") == "ch_01" and ch.get("bio_data"):
            continue
        ch_min = 80 if ch.get("id") == "ch_01" else min_chapter_chars
        if content is None or len(content.strip()) < ch_min:
            issues.append(
                {
                    "issue": "chapter_too_short_or_empty",
                    "chapter_id": ch["id"],
                    "chars": len((content or "").strip()),
                    "min_required_chars": ch_min,
                }
            )
    return GateResult(
        passed=(len(issues) == 0),
        name="non_empty_book",
        details={"issues": issues, "min_chapter_chars": min_chapter_chars},
    )


def run_stage2_text_gates(book_draft: dict, fact_map: dict) -> dict:
    gates = [
        gate_required_entities(book_draft, fact_map),
        gate_repetition_overlap(book_draft, ngram_size=5, threshold=0.20),
        gate_ch01_bio_not_empty(book_draft, fact_map, min_chars=300),
    ]
    return {"stage": "stage2", "passed": all(g.passed for g in gates), "gates": [g.as_dict() for g in gates]}


def run_stage3_text_gates(book_final: dict, fact_map: dict) -> dict:
    gates = [
        gate_non_empty_book(book_final, min_chapter_chars=120),
        gate_required_entities(book_final, fact_map),
        gate_repetition_overlap(book_final, ngram_size=5, threshold=0.22),
    ]
    return {"stage": "stage3", "passed": all(g.passed for g in gates), "gates": [g.as_dict() for g in gates]}


def run_stage2_text_gates_variant_b(book_draft: dict, fact_map: dict) -> dict:
    """
    Вариант B (TR1-only base): пропускает gate_required_entities
    (часть сущностей появится только после Phase B с TR2).
    """
    gates = [
        gate_repetition_overlap(book_draft, ngram_size=5, threshold=0.20),
        gate_ch01_bio_not_empty(book_draft, fact_map, min_chars=300),
        gate_non_empty_book(book_draft, min_chapter_chars=120),
    ]
    return {"stage": "stage2_variant_b", "passed": all(g.passed for g in gates), "gates": [g.as_dict() for g in gates]}


def run_stage3_text_gates_variant_b(book_final: dict, fact_map: dict) -> dict:
    """
    Вариант B: проверяет только непустоту и повторы, без gate_required_entities.
    """
    gates = [
        gate_non_empty_book(book_final, min_chapter_chars=120),
        gate_repetition_overlap(book_final, ngram_size=5, threshold=0.22),
    ]
    return {"stage": "stage3_variant_b", "passed": all(g.passed for g in gates), "gates": [g.as_dict() for g in gates]}


def gate_phase_b_volume_growth(book_before: dict, book_after: dict, min_growth: float = 0.20) -> GateResult:
    """
    Проверяет, что Phase B увеличила суммарный объём текста не менее чем на min_growth (20%).
    """
    def _total_chars(book: dict) -> int:
        return sum(len(ch.get("content") or "") for ch in book.get("chapters", []))

    chars_before = _total_chars(book_before)
    chars_after = _total_chars(book_after)
    if chars_before == 0:
        return GateResult(False, "phase_b_volume_growth", {"reason": "book_before is empty"})

    actual_growth = (chars_after - chars_before) / chars_before
    passed = actual_growth >= min_growth
    return GateResult(
        passed=passed,
        name="phase_b_volume_growth",
        details={
            "chars_before": chars_before,
            "chars_after": chars_after,
            "actual_growth": round(actual_growth, 4),
            "min_growth": min_growth,
            "growth_ok": passed,
        },
    )


def _try_pdf_page_count(pdf_path: Path) -> int | None:
    try:
        from pypdf import PdfReader  # type: ignore

        return len(PdfReader(str(pdf_path)).pages)
    except Exception:
        return None


def pdf_preflight(pdf_path: str | Path, page_map: list | None, min_size_bytes: int = 12_000) -> dict:
    p = Path(pdf_path)
    exists = p.exists()
    size = p.stat().st_size if exists else 0
    readable_header = False
    if exists:
        try:
            with open(p, "rb") as f:
                readable_header = f.read(4) == b"%PDF"
        except Exception:
            readable_header = False
    page_count_pdf = _try_pdf_page_count(p) if exists else None
    page_count_map = len(page_map or [])
    page_count_match = True if page_count_pdf is None else (page_count_pdf == page_count_map)
    passed = all(
        [
            exists,
            readable_header,
            size >= min_size_bytes,
            page_count_map > 0,
            page_count_match,
        ]
    )
    return {
        "gate": "pdf_preflight",
        "passed": passed,
        "checks": {
            "exists": exists,
            "readable_header_pdf": readable_header,
            "size_ok": size >= min_size_bytes,
            "size_bytes": size,
            "min_size_bytes": min_size_bytes,
            "page_map_pages": page_count_map,
            "pdf_pages": page_count_pdf,
            "page_count_match": page_count_match,
        },
    }


def _normalize_plan_page_type(page_type: str) -> str:
    t = (page_type or "").strip().lower()
    mapping = {
        "cover": "cover",
        "blank": "blank",
        "toc": "toc",
        "chapter_start": "chapter_start",
        "text_only": "chapter_body",
        "text_with_photo": "chapter_body",
        "text_with_photos": "chapter_body",
        "text_with_callout": "chapter_body",
        "bio_timeline": "chapter_body",
        "photo_section": "photo_page",
        "photo_section_start": "photo_page",
        "full_page_photo": "photo_page",
        "final_page": "final_page",
    }
    return mapping.get(t, "")


def _normalize_page_map_type(content_type: str) -> str:
    t = (content_type or "").strip().lower()
    mapping = {
        "cover": "cover",
        "blank": "blank",
        "toc": "toc",
        "chapter_start": "chapter_start",
        "chapter_body": "chapter_body",
        "photo_page": "photo_page",
        "final_page": "final_page",
    }
    return mapping.get(t, "")


def _iter_page_elements(page: dict) -> list[Any]:
    elems = page.get("elements", [])
    return elems if isinstance(elems, list) else []


def _extract_plan_callouts(plan_pages: list[dict]) -> dict[str, int]:
    out: dict[str, int] = {}
    for p in plan_pages:
        page_num = p.get("page_number")
        if not isinstance(page_num, int):
            continue
        for elem in _iter_page_elements(p):
            if not isinstance(elem, dict):
                continue
            etype = (elem.get("type") or "").strip().lower()
            if etype != "callout":
                continue
            cid = str(elem.get("id") or elem.get("callout_id") or "").strip()
            if not cid:
                continue
            out[cid] = page_num
    return out


def _extract_page_map_callouts(page_map: list[dict]) -> dict[str, int]:
    out: dict[str, int] = {}
    for p in page_map:
        page_num = p.get("page_number")
        if not isinstance(page_num, int):
            continue
        for raw in _iter_page_elements(p):
            if isinstance(raw, str):
                m = re.match(r"^(callout_\d+)$", raw.strip().lower())
                if m:
                    out[m.group(1)] = page_num
                continue
            if not isinstance(raw, dict):
                continue
            if (raw.get("type") or "").strip().lower() != "callout":
                continue
            cid = str(raw.get("id") or raw.get("callout_id") or "").strip().lower()
            if cid:
                out[cid] = page_num
    return out


def _technical_notes_blob(technical_notes: dict) -> str:
    return _norm(json.dumps(technical_notes or {}, ensure_ascii=False))


def _has_callout_deviation_justification(technical_notes: dict, callout_id: str, expected: int, actual: int) -> bool:
    blob = _technical_notes_blob(technical_notes)
    if not blob:
        return False
    cid = _norm(callout_id)
    expected_s = str(expected)
    actual_s = str(actual)
    has_reason = ("обосн" in blob) or ("justify" in blob) or ("reason" in blob) or ("deviation" in blob)
    return (cid in blob) and (expected_s in blob) and (actual_s in blob) and has_reason


def _chapter_starts_from_page_map(page_map: list[dict]) -> list[dict]:
    out: list[dict] = []
    for p in page_map:
        if _normalize_page_map_type(str(p.get("content_type", ""))) != "chapter_start":
            continue
        page_num = p.get("page_number")
        if not isinstance(page_num, int):
            continue
        ch_id = p.get("chapter_id")
        out.append({"chapter_id": ch_id, "physical_page": page_num, "visible_page": max(1, page_num - 2)})
    return out


def _toc_items(layout_result: dict) -> list[dict]:
    pages = layout_result.get("pages", []) or []
    for p in pages:
        if (p.get("type") or "").strip().lower() == "toc":
            items = p.get("items", [])
            return items if isinstance(items, list) else []
    return []


def _safe_int(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def structural_layout_guard(layout_result: dict, page_plan: dict) -> dict:
    page_map = layout_result.get("page_map", []) or []
    plan = page_plan.get("page_plan", []) or []
    technical_total = (layout_result.get("technical_notes", {}) or {}).get("total_pages")
    technical_notes = layout_result.get("technical_notes", {}) or {}

    checks = {
        "page_map_not_empty": len(page_map) > 0,
        "page_plan_not_empty": len(plan) > 0,
        # Контракт 1:1 — больше не "close", а строгое соответствие.
        "page_plan_vs_page_map_exact_len": len(plan) == len(page_map) if plan or page_map else False,
        "technical_total_matches_page_map": (technical_total == len(page_map)) if technical_total else True,
    }

    contract_violations: list[dict] = []
    if checks["page_plan_not_empty"] and checks["page_map_not_empty"]:
        paired = min(len(plan), len(page_map))
        for idx in range(paired):
            pp = plan[idx] or {}
            pm = page_map[idx] or {}
            pp_num = pp.get("page_number")
            pm_num = pm.get("page_number")
            pp_type = _normalize_plan_page_type(str(pp.get("page_type", "")))
            pm_type = _normalize_page_map_type(str(pm.get("content_type", "")))
            pp_ch = pp.get("chapter_id")
            pm_ch = pm.get("chapter_id")

            if isinstance(pp_num, int) and isinstance(pm_num, int) and pp_num != pm_num:
                contract_violations.append(
                    {"kind": "page_number_mismatch", "index": idx, "page_plan": pp_num, "page_map": pm_num}
                )
            if pp_type and pm_type and pp_type != pm_type:
                contract_violations.append(
                    {"kind": "page_type_mismatch", "index": idx, "page_plan": pp_type, "page_map": pm_type}
                )
            # chapter_id сверяем только там, где он должен быть.
            if pp_ch is not None and pm_ch is not None and pp_ch != pm_ch:
                contract_violations.append(
                    {"kind": "chapter_id_mismatch", "index": idx, "page_plan": pp_ch, "page_map": pm_ch}
                )

    # Callout alignment: page_plan -> page_map, допуск +-1 только с обоснованием.
    plan_callouts = _extract_plan_callouts(plan)
    map_callouts = _extract_page_map_callouts(page_map)
    callout_violations: list[dict] = []
    callout_warnings: list[dict] = []

    if map_callouts and not plan_callouts:
        callout_violations.append(
            {
                "reason": "page_plan_missing_callouts_source_of_truth",
                "expected": "callouts must be explicit in page_plan.elements",
                "found_in_page_map": sorted(map_callouts.keys()),
            }
        )

    for cid, expected_page in plan_callouts.items():
        actual_page = map_callouts.get(cid.lower()) or map_callouts.get(cid)
        if actual_page is None:
            callout_violations.append(
                {"callout_id": cid, "expected_page": expected_page, "actual_page": None, "reason": "missing_in_page_map"}
            )
            continue
        delta = actual_page - expected_page
        if delta == 0:
            continue
        if abs(delta) <= 1 and _has_callout_deviation_justification(technical_notes, cid, expected_page, actual_page):
            callout_warnings.append(
                {
                    "callout_id": cid,
                    "expected_page": expected_page,
                    "actual_page": actual_page,
                    "delta": delta,
                    "status": "allowed_with_justification",
                }
            )
            continue
        callout_violations.append(
            {
                "callout_id": cid,
                "expected_page": expected_page,
                "actual_page": actual_page,
                "delta": delta,
                "reason": "outside_tolerance_or_missing_justification",
            }
        )

    # Pagination/TOC model checks:
    # physical 1 cover (no visible), physical 2 blank (no visible), physical 3 toc (visible page 1).
    pagination_checks = {
        "first_page_is_cover": False,
        "second_page_is_blank": False,
        "third_page_is_toc": False,
        "toc_visible_numbering_matches_chapter_starts": True,
    }
    if len(page_map) >= 1:
        p1 = page_map[0] or {}
        pagination_checks["first_page_is_cover"] = (
            isinstance(p1.get("page_number"), int)
            and p1.get("page_number") == 1
            and _normalize_page_map_type(str(p1.get("content_type", ""))) == "cover"
        )
    if len(page_map) >= 2:
        p2 = page_map[1] or {}
        pagination_checks["second_page_is_blank"] = (
            isinstance(p2.get("page_number"), int)
            and p2.get("page_number") == 2
            and _normalize_page_map_type(str(p2.get("content_type", ""))) == "blank"
        )
    if len(page_map) >= 3:
        p3 = page_map[2] or {}
        pagination_checks["third_page_is_toc"] = (
            isinstance(p3.get("page_number"), int)
            and p3.get("page_number") == 3
            and _normalize_page_map_type(str(p3.get("content_type", ""))) == "toc"
        )

    toc_items = _toc_items(layout_result)
    chapter_starts = _chapter_starts_from_page_map(page_map)
    toc_mismatches: list[dict] = []
    if toc_items and chapter_starts:
        comp_len = min(len(toc_items), len(chapter_starts))
        for idx in range(comp_len):
            toc_page = _safe_int((toc_items[idx] or {}).get("page"))
            expected_visible = chapter_starts[idx]["visible_page"]
            if toc_page is None:
                continue
            if toc_page != expected_visible:
                toc_mismatches.append(
                    {
                        "index": idx,
                        "toc_page": toc_page,
                        "expected_visible_page": expected_visible,
                        "chapter_id": chapter_starts[idx].get("chapter_id"),
                        "chapter_physical_page": chapter_starts[idx].get("physical_page"),
                    }
                )
        pagination_checks["toc_visible_numbering_matches_chapter_starts"] = len(toc_mismatches) == 0

    checks.update(
        {
            "page_plan_contract_ok": len(contract_violations) == 0,
            "callouts_follow_page_plan": len(callout_violations) == 0,
            "pagination_model_ok": all(pagination_checks.values()),
        }
    )

    return {
        "gate": "structural_layout_guard",
        "passed": all(checks.values()),
        "checks": checks,
        "page_type_mapping_table": {
            "cover": "cover",
            "blank": "blank",
            "toc": "toc",
            "chapter_start": "chapter_start",
            "text_only/text_with_photo/text_with_photos/text_with_callout/bio_timeline": "chapter_body",
            "photo_section/photo_section_start/full_page_photo": "photo_page",
            "final_page": "final_page",
        },
        "contract_violations": contract_violations,
        "callouts": {
            "expected_from_page_plan": plan_callouts,
            "found_in_page_map": map_callouts,
            "violations": callout_violations,
            "warnings": callout_warnings,
        },
        "pagination_model": {
            "checks": pagination_checks,
            "toc_mismatches": toc_mismatches,
        },
    }


def summarize_failed_gates(report: dict) -> list[dict]:
    failed = []
    for g in report.get("gates", []):
        if not g.get("passed"):
            failed.append(g)
    return failed


def save_gate_report(path: Path, report: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
