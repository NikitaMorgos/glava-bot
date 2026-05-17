#!/usr/bin/env python3
import json, sys

# Check v40 fact_map persons structure
fm = json.load(open('/opt/glava/exports/karakulina_fact_map_full_20260430_064718.json', encoding='utf-8'))
ps = fm.get('persons', [])
print(f"Total persons in v40 fact_map: {len(ps)}")
for p in ps[:5]:
    print(json.dumps(p, ensure_ascii=False, indent=2))

# Check which fact_map files exist
import os, glob
fms = sorted(glob.glob('/opt/glava/exports/karakulina_fact_map*.json'))
print(f"\nFact_map files in exports: {len(fms)}")
for f in fms[-5:]:
    size = os.path.getsize(f)
    print(f"  {os.path.basename(f)} ({size} bytes)")
