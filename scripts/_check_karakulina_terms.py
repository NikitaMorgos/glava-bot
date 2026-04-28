import glob
import json
from pathlib import Path

TERMS = ["Маргось", "Кужба", "стрекоза"]

files = sorted(glob.glob("/opt/glava/exports/karakulina_book_draft_v*_20260408_110940.json"))
files.append("/opt/glava/exports/karakulina_full_latest_proofreader_report_20260408_113026.json")
files.append("/opt/glava/exports/test_fact_map_karakulina_v5.json")

for f in files:
    p = Path(f)
    if not p.exists():
        print(f"MISSING {f}")
        continue
    data = json.loads(p.read_text(encoding="utf-8"))
    text = json.dumps(data, ensure_ascii=False)
    print(f"\nFILE {p.name}")
    for t in TERMS:
        print(f"  {t}: {text.count(t)}")

fc_path = Path("/opt/glava/exports/karakulina_fc_report_iter2_20260408_110940.json")
if fc_path.exists():
    fc = json.loads(fc_path.read_text(encoding="utf-8"))
    miss = (fc.get("completeness_check", {}) or {}).get("facts_missing_from_text", []) or []
    print(f"\nFC missing facts: {len(miss)}")
    for item in miss:
        print(" ", item.get("fact_id"), "|", item.get("reason", "")[:120])
