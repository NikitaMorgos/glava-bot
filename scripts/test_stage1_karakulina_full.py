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
    apply_completeness_enrichment,
)
from scripts.normalize_named_entities import normalize_named_entities

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
    args = parser.parse_args()

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("[ERROR] ANTHROPIC_API_KEY не задан"); sys.exit(1)

    tr1 = Path(args.transcript1)
    if not tr1.exists():
        print(f"[ERROR] Файл не найден: {tr1}"); sys.exit(1)

    text1 = tr1.read_text(encoding="utf-8")

    if args.transcript2:
        tr2 = Path(args.transcript2)
        if not tr2.exists():
            print(f"[ERROR] Файл не найден: {tr2}"); sys.exit(1)
        text2 = tr2.read_text(encoding="utf-8")
        combined = (
            f"=== ИСТОЧНИК 1: {tr1.name} (оригинальный ASR, март 2026) ===\n\n"
            + text1.strip()
            + "\n\n" + "=" * 70 + "\n\n"
            + f"=== ИСТОЧНИК 2: {tr2.name} (уточняющее интервью, апрель 2026) ===\n\n"
            + text2.strip()
        )
        print(f"\n[STAGE1] Каракулина — два транскрипта")
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

    # Completeness Auditor (агент 16)
    print(f"\n>>> ШАГ 3: COMPLETENESS AUDITOR {cfg.get('completeness_auditor', {}).get('prompt_file', 'N/A')}")
    audit_result = run_completeness_auditor(
        client, cleaned,
        fact_map=fact_map,
        subject_name=CHARACTER_NAME,
        narrator_name=NARRATOR_NAME,
        narrator_relation=NARRATOR_RELATION,
        project_id=PROJECT_ID,
        cfg=cfg,
    )
    fact_map, enrichment_stats = apply_completeness_enrichment(fact_map, audit_result)

    # Сохраняем audit-отчёт
    audit_path = out_dir / f"karakulina_completeness_audit_{ts}.json"
    audit_path.write_text(json.dumps(audit_result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[SAVED] {audit_path.name}")

    # Перезаписываем fact_map_full с обогащением от Auditor
    fm_path.write_text(json.dumps(fact_map, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[SAVED] {fm_path.name} (обновлён после Auditor)")

    # Name Normalizer (детерминированный скрипт)
    print(f"\n>>> ШАГ 4: NAME NORMALIZER")
    fact_map, merged_pairs = normalize_named_entities(fact_map, cleaned)
    normalization_stats = {
        "merged_pairs": merged_pairs,
        "normalized_count": len(merged_pairs),
    }
    fm_path.write_text(json.dumps(fact_map, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[SAVED] {fm_path.name} (обновлён после Name Normalizer)")

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
        },
        outputs={
            "cleaned": str(cleaned_path),
            "fact_map_full": str(fm_path),
            "fact_map_clean": str(fm_clean_path),
            "completeness_audit": str(audit_path),
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
