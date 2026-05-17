#!/usr/bin/env python3
"""Собирает метрики всех версий Каракулиной для таблицы quality trajectory."""
import json, os, glob, subprocess
from pathlib import Path

EXPORTS = Path("/opt/glava/exports")

def chars_in_book(path):
    try:
        d = json.load(open(path, encoding="utf-8"))
        chapters = d.get("chapters", [])
        total = 0
        per_ch = {}
        for ch in chapters:
            cid = ch.get("id", "?")
            ct = 0
            for p in ch.get("paragraphs", []):
                ct += len(p.get("text", ""))
            # also try content field
            ct += len(ch.get("content", ""))
            total += ct
            per_ch[cid] = ct
        callouts = len(d.get("callouts", []))
        hist = len(d.get("historical_notes", []))
        return total, per_ch, len(chapters), callouts, hist
    except Exception as e:
        return None, {}, 0, 0, 0

def pdf_info(path):
    try:
        sz = os.path.getsize(path)
        # try pdfinfo
        r = subprocess.run(["pdfinfo", path], capture_output=True, text=True, timeout=5)
        pages = 0
        for line in r.stdout.splitlines():
            if line.startswith("Pages:"):
                pages = int(line.split(":")[1].strip())
        return pages, sz
    except:
        return 0, os.path.getsize(path) if os.path.exists(path) else 0

def find_latest(pattern):
    files = sorted(glob.glob(str(EXPORTS / pattern)))
    return files[-1] if files else None

def find_in_dir(d, pattern):
    if not os.path.isdir(d):
        return None
    files = sorted(glob.glob(str(Path(d) / pattern)))
    return files[-1] if files else None

versions = []

# ─── v27 ─── gate2a/2b only, no full stage3 book
v = {"ver": "v27", "date": "2026-04-17", "transcripts": "TR1", "notes": "gate2a/2b only, no stage3"}
v["pdf_gate2c"] = None
v["book_stage3"] = None
v["pdf_pages"], v["pdf_size"] = 0, 0
v["total_chars"] = v["chapters"] = v["callouts"] = v["hist_notes"] = None
v["per_ch"] = {}
versions.append(v)

# ─── v28 ─── полный gate2c, TR1+TR2
v = {"ver": "v28", "date": "2026-04-19", "transcripts": "TR1+TR2", "notes": "первый gate2c"}
pdf = find_latest("karakulina_v28_gate2c*gate_2c*.pdf")
v["pdf_gate2c"] = pdf
v["pdf_pages"], v["pdf_size"] = pdf_info(pdf) if pdf else (0, 0)
# v28 book stage3 — искать в run-dirs
book28 = find_in_dir(EXPORTS / "karakulina_v28_run_*", "karakulina_v28_book_FINAL_stage3*.json")
if not book28:
    book28 = find_latest("karakulina_v28_run_*/karakulina_v28_book_FINAL_stage3*.json")
v["book_stage3"] = book28
if book28:
    v["total_chars"], v["per_ch"], v["chapters"], v["callouts"], v["hist_notes"] = chars_in_book(book28)
else:
    v["total_chars"] = v["chapters"] = v["callouts"] = v["hist_notes"] = None
    v["per_ch"] = {}
versions.append(v)

# ─── v29–v35 ─── ранние прогоны Stage 1+2, без gate2c
for ver_num, run_date, run_ts, tr in [
    ("v29", "2026-04-20", "20260420_072506", "TR1+TR2"),
    ("v30", "2026-04-20", "20260420_122027", "TR1+TR2"),
    ("v31", "2026-04-21", "20260421_042318", "TR1+TR2"),
    ("v32", "2026-04-21", "20260421_133558", "TR1+TR2"),
    ("v33", "2026-04-22", "20260422_085445", "TR1+TR2"),
    ("v34", "2026-04-23", "20260423_085243", "TR1+TR2"),
    ("v35", "2026-04-23", "20260423_144616", "TR1+TR2"),
]:
    run_dir = EXPORTS / f"karakulina_{ver_num}_run_{run_ts}"
    v = {"ver": ver_num, "date": run_date, "transcripts": tr, "notes": "Stage 1+2 only"}
    v["pdf_gate2c"] = None
    v["pdf_pages"] = v["pdf_size"] = 0
    book = find_in_dir(run_dir, f"karakulina_{ver_num}_book_FINAL_stage3*.json")
    if not book:
        book = find_in_dir(run_dir, "karakulina_book_FINAL_*.json")
    v["book_stage3"] = book
    if book:
        v["total_chars"], v["per_ch"], v["chapters"], v["callouts"], v["hist_notes"] = chars_in_book(book)
    else:
        v["total_chars"] = v["chapters"] = v["callouts"] = v["hist_notes"] = None
        v["per_ch"] = {}
    versions.append(v)

# ─── v36 ─── stage3 есть, gate2b+2c
v = {"ver": "v36", "date": "2026-04-28/29", "transcripts": "TR1+TR2", "notes": "first S1-4 full, callout bugs"}
book36 = find_in_dir(EXPORTS / "stage3_v36", "karakulina_book_FINAL_stage3*.json")
v["book_stage3"] = book36
if book36:
    v["total_chars"], v["per_ch"], v["chapters"], v["callouts"], v["hist_notes"] = chars_in_book(book36)
else:
    v["total_chars"] = v["chapters"] = v["callouts"] = v["hist_notes"] = None
    v["per_ch"] = {}
pdf36 = find_latest("karakulina_v36_stage4_gate_2c*.pdf")
v["pdf_gate2c"] = pdf36
v["pdf_pages"], v["pdf_size"] = pdf_info(pdf36) if pdf36 else (0, 0)
versions.append(v)

# ─── v37 ─── stage3 есть, gate2c
v = {"ver": "v37", "date": "2026-04-30", "transcripts": "TR1+TR2", "notes": "GW v2.5, fix023"}
book37 = find_in_dir(EXPORTS / "stage3_v37", "karakulina_v37_book_FINAL_stage3*.json")
v["book_stage3"] = book37
if book37:
    v["total_chars"], v["per_ch"], v["chapters"], v["callouts"], v["hist_notes"] = chars_in_book(book37)
else:
    v["total_chars"] = v["chapters"] = v["callouts"] = v["hist_notes"] = None
    v["per_ch"] = {}
pdf37 = find_latest("karakulina_v37_stage4_gate_2c*.pdf")
v["pdf_gate2c"] = pdf37
v["pdf_pages"], v["pdf_size"] = pdf_info(pdf37) if pdf37 else (0, 0)
versions.append(v)

# ─── v37a/v37b — Stage1-only variants
for sub in ["v37a", "v37b"]:
    d = EXPORTS / f"karakulina_{sub}"
    v = {"ver": sub, "date": "2026-04-30", "transcripts": "TR1 / TR2", "notes": "Stage 1 только"}
    v["pdf_gate2c"] = None; v["pdf_pages"] = v["pdf_size"] = 0
    book = find_in_dir(d, "*.json")
    v["book_stage3"] = None
    v["total_chars"] = v["chapters"] = v["callouts"] = v["hist_notes"] = None
    v["per_ch"] = {}
    versions.append(v)

# ─── v38 ─── stage3 есть, gate2c
v = {"ver": "v38", "date": "2026-04-30", "transcripts": "TR1+TR2", "notes": "GW v2.6, прогон после fix023"}
book38 = find_in_dir(EXPORTS / "stage3_v38", "karakulina_v38_book_FINAL_stage3*.json")
v["book_stage3"] = book38
if book38:
    v["total_chars"], v["per_ch"], v["chapters"], v["callouts"], v["hist_notes"] = chars_in_book(book38)
else:
    v["total_chars"] = v["chapters"] = v["callouts"] = v["hist_notes"] = None
    v["per_ch"] = {}
pdf38 = find_latest("karakulina_v38_stage4_gate_2c*.pdf")
v["pdf_gate2c"] = pdf38
v["pdf_pages"], v["pdf_size"] = pdf_info(pdf38) if pdf38 else (0, 0)
versions.append(v)

# ─── v38a/v38b/v40a/v40b/v40c — Stage1-only variants
for sub, date, note in [
    ("v38a", "2026-04-30", "Stage 1 TR1"),
    ("v38b", "2026-04-30", "Stage 1 TR2"),
    ("v40a", "2026-05-01", "Stage 1 TR1"),
    ("v40b", "2026-05-01", "Stage 1 TR2"),
    ("v40c", "2026-05-01", "Stage 1 TR1+TR2 merge"),
]:
    v = {"ver": sub, "date": date, "transcripts": "TR1 or TR2", "notes": note}
    v["pdf_gate2c"] = None; v["pdf_pages"] = v["pdf_size"] = 0
    v["book_stage3"] = None
    v["total_chars"] = v["chapters"] = v["callouts"] = v["hist_notes"] = None
    v["per_ch"] = {}
    versions.append(v)

# ─── v44/v45/v46 ─── Stage 4 only (book_FINAL = v36)
for ver_num, date, note in [
    ("v44", "2026-05-06", "Stage4 only, LD v3.21, base=v36"),
    ("v45", "2026-05-06", "Stage4 only, LD v3.22, callout_ref added"),
    ("v46", "2026-05-06", "Stage4 only, soft ORDER, callout/hist verified"),
]:
    v = {"ver": ver_num, "date": date, "transcripts": "TR1+TR2 (v36 base)", "notes": note}
    v["book_stage3"] = book36  # same book as v36
    # grab metrics from v36
    v["total_chars"], v["per_ch"], v["chapters"], v["callouts"], v["hist_notes"] = chars_in_book(book36) if book36 else (None, {}, 0, 0, 0)
    pdf = find_latest(f"karakulina_{ver_num}_stage4_gate_2c*.pdf")
    v["pdf_gate2c"] = pdf
    v["pdf_pages"], v["pdf_size"] = pdf_info(pdf) if pdf else (0, 0)
    versions.append(v)

# ─── v47–v51 ─── Stage 2 only (FC iterations), no gate2c
for ver_num, date, note in [
    ("v47", "2026-05-06", "Stage2 FC v2.9, cucumber deleted (reg #3 reopen)"),
    ("v48", "2026-05-07", "Stage2 FC v2.10 evidence-required, blocked unauth del"),
    ("v49", "2026-05-07", "Stage2 FC v2.11 historical_ctx, cucumber still del"),
    ("v50", "2026-05-07", "Stage2 FC v2.12 topic-overlap, blocked phantom evidence"),
    ("v51", "2026-05-07", "Stage2 FC v2.13 min_shared_tokens, reg #3 CLOSED"),
]:
    v = {"ver": ver_num, "date": date, "transcripts": "TR1+TR2 (v36 base)", "notes": note}
    v["pdf_gate2c"] = None; v["pdf_pages"] = v["pdf_size"] = 0
    v["book_stage3"] = None  # stage3 not run
    v["total_chars"] = v["chapters"] = v["callouts"] = v["hist_notes"] = None
    v["per_ch"] = {}
    versions.append(v)

# ─── v52 ─── Stage 2 blocked, stage3 exists
v = {"ver": "v52", "date": "2026-05-08", "transcripts": "TR1+TR2", "notes": "GW deleted 3 chapters, blocked 52.8% drop"}
book52 = find_in_dir(EXPORTS / "stage3_v52", "karakulina_v52_book_FINAL_stage3*.json")
if not book52:
    book52 = find_in_dir(EXPORTS / "stage3_v52", "*.json")
v["book_stage3"] = book52
if book52:
    v["total_chars"], v["per_ch"], v["chapters"], v["callouts"], v["hist_notes"] = chars_in_book(book52)
else:
    v["total_chars"] = v["chapters"] = v["callouts"] = v["hist_notes"] = None
    v["per_ch"] = {}
v["pdf_gate2c"] = None; v["pdf_pages"] = v["pdf_size"] = 0
versions.append(v)

# ─── v53 ─── TR1, full run, GW v2.16
v = {"ver": "v53", "date": "2026-05-08", "transcripts": "TR1", "notes": "GW v2.16 scope guardrail, Scenario A"}
book53 = find_in_dir(EXPORTS / "stage3_v53", "karakulina_v53_book_FINAL_stage3*.json")
v["book_stage3"] = book53
if book53:
    v["total_chars"], v["per_ch"], v["chapters"], v["callouts"], v["hist_notes"] = chars_in_book(book53)
else:
    v["total_chars"] = v["chapters"] = v["callouts"] = v["hist_notes"] = None
    v["per_ch"] = {}
pdf53 = find_latest("karakulina_v53_stage4_gate_2c*.pdf")
v["pdf_gate2c"] = pdf53
v["pdf_pages"], v["pdf_size"] = pdf_info(pdf53) if pdf53 else (0, 0)
versions.append(v)

# ─── v53b ─── TR2, Scenario C
v = {"ver": "v53b", "date": "2026-05-08", "transcripts": "TR2", "notes": "LE deleted cucumber, Scenario C"}
book53b = find_in_dir(EXPORTS / "stage3_v53b", "karakulina_v53b_book_FINAL_stage3*.json")
v["book_stage3"] = book53b
if book53b:
    v["total_chars"], v["per_ch"], v["chapters"], v["callouts"], v["hist_notes"] = chars_in_book(book53b)
else:
    v["total_chars"] = v["chapters"] = v["callouts"] = v["hist_notes"] = None
    v["per_ch"] = {}
pdf53b = find_latest("karakulina_v53b_stage4_gate_2c*.pdf")
v["pdf_gate2c"] = pdf53b
v["pdf_pages"], v["pdf_size"] = pdf_info(pdf53b) if pdf53b else (0, 0)
versions.append(v)

# ─── OUTPUT ───
print("\n=== METRICS ===")
for v in versions:
    tc = v["total_chars"]
    ch = v["chapters"]
    co = v["callouts"]
    hn = v["hist_notes"]
    pp = v["pdf_pages"]
    ps = v["pdf_size"]
    per_ch = v["per_ch"]
    top_ch = sorted(per_ch.items(), key=lambda x: x[1], reverse=True)[:3] if per_ch else []
    top_str = ", ".join(f"{k}:{vv}" for k,vv in top_ch) if top_ch else "-"
    print(f"VER={v['ver']} | date={v['date']} | TR={v['transcripts']}")
    print(f"  total_chars={tc} | chapters={ch} | callouts={co} | hist_notes={hn}")
    print(f"  top_ch_chars={top_str}")
    print(f"  pdf_pages={pp} | pdf_size={ps//1024}KB | gate2c={'YES' if v['pdf_gate2c'] else 'NO'}")
    print(f"  notes={v['notes']}")
    print()

# JSON for later use
out = []
for v in versions:
    row = {k: str(v[k]) if isinstance(v[k], Path) else v[k] for k, val in v.items() for k in [k]}
    # simplify per_ch to min/max/total
    pc = v.get("per_ch", {})
    row["per_ch_min"] = min(pc.values()) if pc else None
    row["per_ch_max"] = max(pc.values()) if pc else None
    row["per_ch_detail"] = {k: val for k, val in sorted(pc.items())}
    row.pop("per_ch", None)
    row.pop("pdf_gate2c", None)
    row.pop("book_stage3", None)
    out.append(row)

with open("/tmp/karakulina_version_metrics.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print("JSON saved: /tmp/karakulina_version_metrics.json")
