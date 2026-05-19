#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stage 1 — Факт-экстракция из двух транскриптов Каракулиной.
"""
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import anthropic
from pipeline_utils import (
    load_config, run_cleaner, run_fact_extractor, save_run_manifest,
    clean_fact_map_for_downstream, run_completeness_auditor,
    apply_completeness_enrichment, merge_fact_maps,
    enrich_timeline_with_subject_age, normalize_fact_map_topo,
    parse_pin_list_from_markdown, validate_pin_list_in_auto_enrich,
)
from scripts.normalize_named_entities import normalize_named_entities

GAZETEER_PATH = ROOT / "collab" / "context" / "gazeteer_karakulina.json"

CHARACTER_NAME   = "Каракулина Валентина Ивановна"
NARRATOR_NAME    = "Татьяна Каракулина"
NARRATOR_RELATION = "дочь"
PROJECT_ID       = "karakulina"
KNOWN_BIRTH_YEAR = 1920


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--transcript1",
        default="/opt/glava/exports/transcripts/karakulina_valentina_interview_assemblyai.txt")
    parser.add_argument("--transcript2",
        default=None,
        help="Второй транскрипт (опционально). Если не указан — Stage1 работает только с TR1.")
    parser.add_argument("--output-dir", default="/opt/glava/exports")
    parser.add_argument("--skip-cleaner", action="store_true")
    parser.add_argument(
        "--prev-fact-map",
        default=None,
        help="Путь к fact_map предыдущего прогона Stage 1 (JSON). "
             "Используется Completeness Auditor как pin-list: "
             "персоны/events из предыдущего прогона — контрольный список; "
             "если кто-то был раньше и не найден сейчас — flag для re-extraction.",
    )
    parser.add_argument(
        "--split-extract", action="store_true",
        help="task 035 split-extract mode (для combined TR1+TR2). "
             "Cleaner и FE проходят на КАЖДОМ транскрипте отдельно: "
             "TR1 → fact_map_TR1 (Phase A) → TR2 (Phase B, existing_facts=fact_map_TR1) → "
             "merged fact_map. Защита от потери TR2-уникальных эпизодов "
             "(огурцы Молдавия, счётчик 1977, Нинвана — v54 регрессия). "
             "Применимо только при --transcript2.",
    )
    parser.add_argument(
        "--known-episodes",
        default=None,
        help="Task 041b: путь к known_episodes_<subject>.md. "
             "Если не указан — ищется автоматически как "
             "collab/context/known_episodes_<subject>.md. "
             "Pin-list передаётся в CA для bypass strict + compliance check.",
    )
    args = parser.parse_args()

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("[ERROR] ANTHROPIC_API_KEY не задан"); sys.exit(1)

    # Task 041b: load pin-list from known_episodes_<subject>.md
    _known_ep_path = args.known_episodes
    if not _known_ep_path:
        _auto_path = ROOT / "collab" / "context" / f"known_episodes_{PROJECT_ID}.md"
        if _auto_path.exists():
            _known_ep_path = str(_auto_path)
            print(f"[STAGE1] Auto-detected pin-list: {_auto_path.name}")
        else:
            print(f"[STAGE1] ⚠️ Pin-list не найден ({_auto_path}) — CA без pin-list bypass")

    pin_list_episodes: dict | None = None
    if _known_ep_path:
        pin_list_episodes = parse_pin_list_from_markdown(_known_ep_path)
        ep_count = len(pin_list_episodes.get("episodes", []))
        rp_count = len(pin_list_episodes.get("required_persons", []))
        print(f"[STAGE1] Pin-list загружен: {ep_count} эпизодов, {rp_count} required_persons")

    prev_fact_map: dict | None = None
    if args.prev_fact_map:
        prev_path = Path(args.prev_fact_map)
        if not prev_path.exists():
            print(f"[WARN] --prev-fact-map: файл не найден: {prev_path} — pin-list отключён")
        else:
            with open(prev_path, encoding="utf-8") as _f:
                _prev = json.load(_f)
            prev_fact_map = _prev.get("fact_map") if "fact_map" in _prev else _prev
            prev_persons = len(prev_fact_map.get("persons", []))
            print(f"[STAGE1] Pin-list из {prev_path.name}: {prev_persons} персон")

    tr1 = Path(args.transcript1)
    if not tr1.exists():
        print(f"[ERROR] Файл не найден: {tr1}"); sys.exit(1)

    text1 = tr1.read_text(encoding="utf-8")

    has_tr2 = bool(args.transcript2)
    text2 = None
    tr2 = None
    if has_tr2:
        tr2 = Path(args.transcript2)
        if not tr2.exists():
            print(f"[ERROR] Файл не найден: {tr2}"); sys.exit(1)
        text2 = tr2.read_text(encoding="utf-8")

    # Validation: split-extract требует --transcript2
    split_mode = args.split_extract and has_tr2
    if args.split_extract and not has_tr2:
        print("[WARN] --split-extract игнорируется: --transcript2 не указан. Один транскрипт = классический режим.")
        split_mode = False

    if split_mode:
        print(f"\n[STAGE1] Каракулина — SPLIT-EXTRACT mode (task 035)")
        print(f"  Источник 1: {tr1.name} ({len(text1):,} симв) → Phase A")
        print(f"  Источник 2: {tr2.name} ({len(text2):,} симв) → Phase B (existing_facts=fact_map_TR1)")
    elif has_tr2:
        combined = (
            f"=== ИСТОЧНИК 1: {tr1.name} (оригинальный ASR, март 2026) ===\n\n"
            + text1.strip()
            + "\n\n" + "=" * 70 + "\n\n"
            + f"=== ИСТОЧНИК 2: {tr2.name} (уточняющее интервью, апрель 2026) ===\n\n"
            + text2.strip()
        )
        print(f"\n[STAGE1] Каракулина — два транскрипта (combined, classic mode)")
        print(f"  Источник 1: {tr1.name} ({len(text1):,} симв)")
        print(f"  Источник 2: {tr2.name} ({len(text2):,} симв)")
        print(f"  Суммарно:   {len(combined):,} симв")
    else:
        combined = text1.strip()
        print(f"\n[STAGE1] Каракулина — один транскрипт (Вариант B)")
        print(f"  Источник 1: {tr1.name} ({len(text1):,} симв)")
        print(f"  TR2 не подан — будет использован в Phase B")

    cfg = load_config()
    print(f"\n[CONFIG] Cleaner:       {cfg['cleaner']['prompt_file']}")
    print(f"[CONFIG] FactExtractor: {cfg['fact_extractor']['prompt_file']}")

    client = anthropic.Anthropic(api_key=api_key)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    if split_mode:
        # === SPLIT-EXTRACT mode (task 035) ===
        # Cleaner отдельно на каждом транскрипте, FE Phase A на TR1, FE Phase B на TR2.
        # Цель — защита от потери TR2-уникальных эпизодов на combined Stage 1 (v54 регрессия).

        # Cleaner TR1
        print(f"\n>>> ШАГ 1a: CLEANER на TR1")
        if args.skip_cleaner:
            cleaned_tr1 = text1.strip()
            print("[CLEANER TR1] Пропущен")
        else:
            cleaned_tr1, _ = run_cleaner(
                client, text1,
                subject_name=CHARACTER_NAME,
                narrator_name=NARRATOR_NAME,
                narrator_relation=NARRATOR_RELATION,
                cfg=cfg,
            )
        cleaned_tr1_path = out_dir / f"karakulina_cleaned_TR1_{ts}.txt"
        cleaned_tr1_path.write_text(cleaned_tr1, encoding="utf-8")
        print(f"[SAVED] {cleaned_tr1_path.name} ({len(cleaned_tr1):,} симв)")

        # Cleaner TR2
        print(f"\n>>> ШАГ 1b: CLEANER на TR2")
        if args.skip_cleaner:
            cleaned_tr2 = text2.strip()
            print("[CLEANER TR2] Пропущен")
        else:
            cleaned_tr2, _ = run_cleaner(
                client, text2,
                subject_name=CHARACTER_NAME,
                narrator_name=NARRATOR_NAME,
                narrator_relation=NARRATOR_RELATION,
                cfg=cfg,
            )
        cleaned_tr2_path = out_dir / f"karakulina_cleaned_TR2_{ts}.txt"
        cleaned_tr2_path.write_text(cleaned_tr2, encoding="utf-8")
        print(f"[SAVED] {cleaned_tr2_path.name} ({len(cleaned_tr2):,} симв)")

        # Объединённый cleaned для downstream (CA + manifest)
        cleaned = (
            f"=== ИСТОЧНИК 1: {tr1.name} (после Cleaner) ===\n\n"
            + cleaned_tr1
            + "\n\n" + "=" * 70 + "\n\n"
            + f"=== ИСТОЧНИК 2: {tr2.name} (после Cleaner) ===\n\n"
            + cleaned_tr2
        )
        cleaned_path = out_dir / f"karakulina_combined_cleaned_{ts}.txt"
        cleaned_path.write_text(cleaned, encoding="utf-8")

        # FE Phase A на TR1
        print(f"\n>>> ШАГ 2a: FACT EXTRACTOR Phase A на TR1 ({cfg['fact_extractor']['prompt_file']})")
        fact_map_tr1 = run_fact_extractor(
            client, cleaned_tr1,
            subject_name=CHARACTER_NAME,
            narrator_name=NARRATOR_NAME,
            narrator_relation=NARRATOR_RELATION,
            project_id=PROJECT_ID,
            known_birth_year=KNOWN_BIRTH_YEAR,
            phase="A",
            call_type="initial",
            cfg=cfg,
        )
        fm_tr1_path = out_dir / f"karakulina_fact_map_TR1_{ts}.json"
        fm_tr1_path.write_text(json.dumps(fact_map_tr1, ensure_ascii=False, indent=2), encoding="utf-8")
        tr1_persons = len(fact_map_tr1.get("persons", []))
        tr1_events = len(fact_map_tr1.get("timeline", []))
        print(f"[SAVED] {fm_tr1_path.name} (persons={tr1_persons}, events={tr1_events})")

        # FE Phase B на TR2 с existing_facts=fact_map_TR1
        print(f"\n>>> ШАГ 2b: FACT EXTRACTOR Phase B на TR2 (existing_facts=fact_map_TR1)")
        fact_map_tr2_incremental = run_fact_extractor(
            client, cleaned_tr2,
            subject_name=CHARACTER_NAME,
            narrator_name=NARRATOR_NAME,
            narrator_relation=NARRATOR_RELATION,
            project_id=PROJECT_ID,
            known_birth_year=KNOWN_BIRTH_YEAR,
            existing_facts=fact_map_tr1,
            phase="B",
            call_type="incremental",
            cfg=cfg,
        )
        tr2_persons_new = len(fact_map_tr2_incremental.get("persons", []))
        tr2_events_new = len(fact_map_tr2_incremental.get("timeline", []))
        print(f"[FE TR2 Phase B] incremental: persons={tr2_persons_new}, events={tr2_events_new}")

        # Merge TR1 + TR2 incremental → fact_map_combined
        fact_map = merge_fact_maps(base=fact_map_tr1, incremental=fact_map_tr2_incremental)
        merged_persons = len(fact_map.get("persons", []))
        merged_events = len(fact_map.get("timeline", []))
        print(f"[SPLIT-EXTRACT] Merged: persons {tr1_persons}+{tr2_persons_new} → {merged_persons}, "
              f"events {tr1_events}+{tr2_events_new} → {merged_events}")

        fm_path = out_dir / f"karakulina_fact_map_full_{ts}.json"
        fm_path.write_text(json.dumps(fact_map, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[SAVED] {fm_path.name}")

    else:
        # === CLASSIC mode (без split, один FE на combined cleaned) ===
        # Cleaner
        print(f"\n>>> ШАГ 1: CLEANER")
        if args.skip_cleaner:
            cleaned = combined
            print("[CLEANER] Пропущен")
        else:
            cleaned, _ = run_cleaner(
                client, combined,
                subject_name=CHARACTER_NAME,
                narrator_name=NARRATOR_NAME,
                narrator_relation=NARRATOR_RELATION,
                cfg=cfg,
            )
        cleaned_path = out_dir / f"karakulina_combined_cleaned_{ts}.txt"
        cleaned_path.write_text(cleaned, encoding="utf-8")
        print(f"[SAVED] {cleaned_path.name} ({len(cleaned):,} симв)")

        # Fact Extractor
        print(f"\n>>> ШАГ 2: FACT EXTRACTOR {cfg['fact_extractor']['prompt_file']}")
        fact_map = run_fact_extractor(
            client, cleaned,
            subject_name=CHARACTER_NAME,
            narrator_name=NARRATOR_NAME,
            narrator_relation=NARRATOR_RELATION,
            project_id=PROJECT_ID,
            known_birth_year=KNOWN_BIRTH_YEAR,
            cfg=cfg,
        )

        fm_path = out_dir / f"karakulina_fact_map_full_{ts}.json"
        fm_path.write_text(json.dumps(fact_map, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[SAVED] {fm_path.name}")

    # Task 042: subject_age enrichment
    print(f"\n>>> ШАГ 2.5: SUBJECT AGE ENRICHMENT (task 042)")
    fact_map = enrich_timeline_with_subject_age(fact_map)

    # Task 040: gazeteer topo normalize на fact_map
    gazeteer: dict = {}
    if GAZETEER_PATH.exists():
        with open(GAZETEER_PATH, encoding="utf-8") as _gf:
            gazeteer = json.load(_gf)
        print(f"[TOPO-NORMALIZE] gazeteer загружен: {GAZETEER_PATH.name} "
              f"({len(gazeteer.get('topo_corrections', {}))} замен)")
        fact_map, _topo_reps = normalize_fact_map_topo(fact_map, gazeteer)
        topo_norm_path = out_dir / f"karakulina_topo_normalize_factmap_{ts}.json"
        topo_norm_path.write_text(
            json.dumps({"replacements": _topo_reps, "gazeteer_version": gazeteer.get("version", "?")},
                       ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"[SAVED] {topo_norm_path.name}")
    else:
        print(f"[TOPO-NORMALIZE] gazeteer не найден ({GAZETEER_PATH}) — пропускаем.")

    # Сохраняем enriched fact_map (до CA) для диагностики
    fm_enriched_path = out_dir / f"karakulina_fact_map_enriched_{ts}.json"
    fm_enriched_path.write_text(json.dumps(fact_map, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[SAVED] {fm_enriched_path.name} (enriched fact_map: subject_age + topo normalize)")

    # Completeness Auditor (агент 16) — task 038b: pin_list_episodes for bypass strict
    print(f"\n>>> ШАГ 3: COMPLETENESS AUDITOR {cfg.get('completeness_auditor', {}).get('prompt_file', 'N/A')}")
    audit_result = run_completeness_auditor(
        client, cleaned,
        fact_map=fact_map,
        subject_name=CHARACTER_NAME,
        narrator_name=NARRATOR_NAME,
        narrator_relation=NARRATOR_RELATION,
        project_id=PROJECT_ID,
        pin_list_fact_map=prev_fact_map,
        pin_list_episodes=pin_list_episodes,
        cfg=cfg,
    )
    fact_map, enrichment_stats = apply_completeness_enrichment(fact_map, audit_result)

    # Task 038b: pin-list compliance check
    if pin_list_episodes:
        _compliance = validate_pin_list_in_auto_enrich(audit_result, pin_list_episodes)
        print(f"[STAGE1] Pin-list compliance: missing_events={len(_compliance.get('pin_list_event_missing', []))}, "
              f"missing_persons={len(_compliance.get('pin_list_person_missing', []))}")

    # Сохраняем audit-отчёт
    audit_path = out_dir / f"karakulina_completeness_audit_{ts}.json"
    audit_path.write_text(json.dumps(audit_result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[SAVED] {audit_path.name}")

    # Перезаписываем fact_map_full с обогащением от Auditor
    fm_path.write_text(json.dumps(fact_map, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[SAVED] {fm_path.name} (обновлён после Auditor)")

    # Name Normalizer (детерминированный скрипт)
    print(f"\n>>> ШАГ 4: NAME NORMALIZER")
    fact_map, nn_log = normalize_named_entities(fact_map, cleaned)
    merged_pairs = [e for e in nn_log if e.get("status") == "merged"]
    rejected_pairs = [e for e in nn_log if e.get("status") == "rejected"]
    normalization_stats = {
        "merged_pairs": merged_pairs,
        "rejected_pairs": rejected_pairs,
        "normalized_count": len(merged_pairs),
    }
    if rejected_pairs:
        print(f"[NAME NORMALIZER] ⛔ заблокировано слияний: {len(rejected_pairs)}")
    fm_path.write_text(json.dumps(fact_map, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[SAVED] {fm_path.name} (обновлён после Name Normalizer)")

    # Сохраняем полный NN-лог (merged + rejected) — для верификации semantic guard
    nn_log_path = out_dir / f"karakulina_normalization_log_{ts}.json"
    nn_log_path.write_text(json.dumps(nn_log, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[SAVED] {nn_log_path.name} (merged={len(merged_pairs)}, rejected={len(rejected_pairs)})")

    # Очищенная копия для Stage 2 (без asr_variants/reasoning/confidence)
    fact_map_clean = clean_fact_map_for_downstream(fact_map)
    fm_clean_path = out_dir / f"karakulina_fact_map_{ts}.json"
    fm_clean_path.write_text(json.dumps(fact_map_clean, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[SAVED] {fm_clean_path.name}  (clean — для GW и FC)")

    # needs_verification — предупреждение в лог
    nv_locs = [l for l in fact_map.get("locations", []) if l.get("needs_verification")]
    nv_pers = [p for p in fact_map.get("persons", []) if p.get("needs_verification")]
    if nv_locs or nv_pers:
        print(f"\n⚠️  needs_verification: {len(nv_locs)} локаций, {len(nv_pers)} персон")
        for l in nv_locs:
            print(f"   LOC [{l.get('id')}] {l.get('name')}  confidence={l.get('confidence')}  reason: {l.get('reasoning','')[:80]}")
        for p in nv_pers:
            print(f"   PER [{p.get('id')}] {p.get('name')}  confidence={p.get('confidence')}")
    else:
        print("[✓] Все топонимы и персоны верифицированы (needs_verification=false)")

    # Статистика
    subj = fact_map.get("subject", {})
    print(f"\n[STATS] {subj.get('name')} {subj.get('birth_year')}–{subj.get('death_year','?')}")
    print(f"  timeline: {len(fact_map.get('timeline',[]))}")
    print(f"  persons:  {len(fact_map.get('persons',[]))}")
    print(f"  quotes:   {len(fact_map.get('quotes',[]))}")
    print(f"  traits:   {len(fact_map.get('character_traits',[]))}")
    metaphors = [t for t in fact_map.get("character_traits",[]) if t.get("category") == "metaphor"]
    print(f"  metaphors:{len(metaphors)}")
    print(f"  gaps:     {len(fact_map.get('gaps',[]))}")

    save_run_manifest(
        output_dir=out_dir, prefix="karakulina", stage="stage1_full",
        project_id=PROJECT_ID, cfg=cfg, ts=ts,
        inputs={
            "transcript1": str(tr1),
            "transcript2": str(args.transcript2) if args.transcript2 else None,
            # task 041b: pin-list tracking
            "pin_list_used": _known_ep_path or "none",
            "pin_list_episodes_count": len((pin_list_episodes or {}).get("episodes", [])),
            "pin_list_required_persons_count": len((pin_list_episodes or {}).get("required_persons", [])),
        },
        outputs={
            "cleaned": str(cleaned_path),
            "fact_map_full": str(fm_path),
            "fact_map_clean": str(fm_clean_path),
            "completeness_audit": str(audit_path),
            "normalization_log": str(nn_log_path),
        },
        notes={
            "completeness_audit": enrichment_stats,
            "name_normalization": normalization_stats,
        },
    )

    print(f"\n✅ Stage1 завершён")
    print(f"FACT_MAP_PATH={fm_path}")


if __name__ == "__main__":
    main()
