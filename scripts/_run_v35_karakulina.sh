#!/usr/bin/env bash
# Karakulina v35: Stage1(TR1+TR2)->Stage2(+historian)->Stage3 — Phase A только
# FE v3.4 (полные награды + reasoning), GW v2.14 (стоп-фразы, all awards), FC v2.8 (awards check)
# Phase B НЕ запускается — откладывается до прохождения Gate 1→4 на Phase A
set -euo pipefail

GLAVA_DIR="/opt/glava"
VENV="$GLAVA_DIR/venv"
EXPORTS="$GLAVA_DIR/exports"
COLLAB="$GLAVA_DIR/collab"
SCRIPTS="$GLAVA_DIR/scripts"

TS=$(date +%Y%m%d_%H%M%S)
V="v35"
PREFIX="karakulina_${V}"
RUN_DIR="$EXPORTS/${PREFIX}_run_${TS}"
mkdir -p "$RUN_DIR"

LOG="$RUN_DIR/run.log"
exec > >(tee "$LOG") 2>&1

echo "=============================================="
echo " GLAVA Full Run Karakulina $V"
echo " Tag:    $PREFIX"
echo " Time:   $(date)"
echo " Config: prompts/pipeline_config.json"
echo "=============================================="
echo ""
echo "===== PRE-FLIGHT CHECK ====="
source "$VENV/bin/activate"
set -a; source "$GLAVA_DIR/.env"; set +a
cd "$GLAVA_DIR"

python3 - <<'PREFLIGHT'
import json, hashlib, sys

cfg_path = "prompts/pipeline_config.json"
with open(cfg_path) as f:
    raw = f.read()
cfg = json.loads(raw)

sha256 = hashlib.sha256(raw.encode()).hexdigest()[:16]

roles = [
    ("cleaner",          "Cleaner"),
    ("fact_extractor",   "Fact Extractor"),
    ("historian",        "Historian"),
    ("ghostwriter",      "Ghostwriter"),
    ("fact_checker",     "Fact Checker"),
    ("literary_editor",  "Literary Editor"),
    ("proofreader",      "Proofreader"),
    ("photo_editor",     "Photo Editor"),
    ("layout_designer",  "Layout Designer"),
    ("cover_designer",   "Cover Designer"),
    ("layout_art_director", "Layout Art Director"),
    ("interview_architect", "Interview Architect"),
]

print(f"  config_sha256 : {sha256}")
print(f"  _updated      : {cfg.get('_updated', '?')}")
print()
print(f"  {'Роль':<22} {'Файл промпта':<35} {'temp':>5}  {'max_tokens':>10}")
print(f"  {'-'*22} {'-'*35} {'-'*5}  {'-'*10}")
for key, label in roles:
    r = cfg.get(key, {})
    pf   = r.get("prompt_file", "—")
    temp = r.get("temperature", "—")
    mt   = r.get("max_tokens", "—")
    print(f"  {label:<22} {pf:<35} {str(temp):>5}  {str(mt):>10}")

# Critical assertions
gw = cfg["ghostwriter"]
fc = cfg["fact_checker"]
ld = cfg["layout_designer"]

errors = []
if gw["temperature"] != 0.4:
    errors.append(f"  ❌ Ghostwriter temperature={gw['temperature']} (требуется 0.4)")
if "v2.14" not in gw["prompt_file"]:
    errors.append(f"  ❌ Ghostwriter prompt={gw['prompt_file']} (требуется v2.14)")
if "v2.8" not in fc["prompt_file"]:
    errors.append(f"  ❌ Fact Checker prompt={fc['prompt_file']} (требуется v2.8)")
if "v3.19" not in ld["prompt_file"]:
    errors.append(f"  ❌ Layout Designer prompt={ld['prompt_file']} (требуется v3.19)")
fe = cfg["fact_extractor"]
if "v3.4" not in fe["prompt_file"]:
    errors.append(f"  ❌ Fact Extractor prompt={fe['prompt_file']} (требуется v3.4)")

if errors:
    print()
    print("  ОШИБКИ КОНФИГУРАЦИИ:")
    for e in errors:
        print(e)
    sys.exit(1)
else:
    print()
    print("  ✅ Конфигурация v35 подтверждена (FE v3.4, GW v2.14 temp=0.4, FC v2.8, LD v3.19)")
PREFLIGHT

echo "============================="
echo ""

TR1="$EXPORTS/transcripts/karakulina_valentina_interview_assemblyai.txt"
TR2="$EXPORTS/transcripts/karakulina_meeting_transcript_20260403.txt"

if [ ! -f "$TR1" ]; then
    TR1=$(find "$EXPORTS" -name "*karakulina*assemblyai*.txt" 2>/dev/null | head -1)
fi
if [ ! -f "$TR2" ]; then
    TR2=$(find "$EXPORTS" -name "*meeting_transcript*.txt" 2>/dev/null | head -1)
fi

echo "[TR1] $TR1 ($(wc -c < "$TR1") bytes)"
echo "[TR2] $TR2 ($(wc -c < "$TR2") bytes)"
echo "[Stage 1 input] TR1 + TR2 суммарно: $(($(wc -c < "$TR1") + $(wc -c < "$TR2"))) bytes"

echo ""
echo ">>> STAGE 1: Fact Extractor v3.3 (оба транскрипта)"
python3 "$SCRIPTS/test_stage1_karakulina_full.py" \
    --transcript1 "$TR1" \
    --transcript2 "$TR2" \
    --output-dir  "$RUN_DIR"

FACT_MAP_FULL=$(ls -t "$RUN_DIR"/karakulina_fact_map_full_*.json 2>/dev/null | head -1)
# Предпочитаем очищенную версию (FE v3.4+); для FE v3.3 fallback на full
FACT_MAP=$(ls -t "$RUN_DIR"/karakulina_fact_map_[0-9]*.json 2>/dev/null | head -1)
if [ -z "$FACT_MAP" ]; then FACT_MAP="$FACT_MAP_FULL"; fi
if [ -z "$FACT_MAP" ]; then echo "[ERROR] fact_map not found"; exit 1; fi
echo "[OK] fact_map (для Stage 2): $(basename $FACT_MAP)"
[ -n "$FACT_MAP_FULL" ] && echo "[OK] fact_map_full: $(basename $FACT_MAP_FULL)"

echo ""
echo ">>> STAGE 2: Historian v3 + Ghostwriter v2.14 + FC v2.8 (historian ENABLED)"
python3 "$SCRIPTS/test_stage2_pipeline.py" \
    --fact-map          "$FACT_MAP" \
    --output-dir        "$RUN_DIR" \
    --variant-b \
    --max-fc-iterations 5

BOOK_S2=$(ls -t "$RUN_DIR"/karakulina_book_FINAL_*.json 2>/dev/null | head -1)
if [ -z "$BOOK_S2" ]; then echo "[ERROR] stage2 book not found"; exit 1; fi
echo "[OK] stage2 book: $(basename $BOOK_S2)"

echo ""
echo ">>> STAGE 3: LitEditor v3 + Proofreader v1"
python3 "$SCRIPTS/test_stage3.py" \
    --book-draft "$BOOK_S2" \
    --fact-map   "$FACT_MAP" \
    --prefix     "$PREFIX" \
    --variant-b

BOOK_S3=$(ls -t "$EXPORTS"/${PREFIX}_book_FINAL_stage3_*.json 2>/dev/null | head -1)
if [ -z "$BOOK_S3" ]; then echo "[ERROR] stage3 book not found"; exit 1; fi
TXT_S3=$(ls -t "$EXPORTS"/${PREFIX}_FINAL_stage3_*.txt 2>/dev/null | head -1 || true)
echo "[OK] stage3 book: $(basename $BOOK_S3)"

cp "$BOOK_S3" "$RUN_DIR/"
test -n "$TXT_S3" && cp "$TXT_S3" "$RUN_DIR/"

# ── Сборка артефактов в collab ────────────────────────────────────────────────
COLLAB_RUN="$COLLAB/runs/${PREFIX}_${TS}"
mkdir -p "$COLLAB_RUN"

cp "$FACT_MAP"  "$COLLAB_RUN/fact_map_v35.json"
[ -n "$FACT_MAP_FULL" ] && cp "$FACT_MAP_FULL" "$COLLAB_RUN/fact_map_full_v35.json"
cp "$BOOK_S2"   "$COLLAB_RUN/book_FINAL_stage2.json"
cp "$BOOK_S3"   "$COLLAB_RUN/book_FINAL_stage3_v35.json"
test -n "$TXT_S3" && cp "$TXT_S3" "$COLLAB_RUN/karakulina_v35_FINAL_phase_a.txt"
cp "$LOG" "$COLLAB_RUN/run.log"

MANIFEST_S1=$(ls -t "$RUN_DIR"/karakulina_stage1_full_run_manifest_*.json 2>/dev/null | head -1 || true)
test -n "$MANIFEST_S1" && cp "$MANIFEST_S1" "$COLLAB_RUN/run_manifest_s1.json"
MANIFEST_S2=$(ls -t "$RUN_DIR"/karakulina_stage2_run_manifest_*.json 2>/dev/null | head -1 || true)
test -n "$MANIFEST_S2" && cp "$MANIFEST_S2" "$COLLAB_RUN/run_manifest_s2.json"
MANIFEST_S3=$(ls -t "$EXPORTS"/${PREFIX}_stage3_run_manifest_*.json 2>/dev/null | head -1 || true)
test -n "$MANIFEST_S3" && cp "$MANIFEST_S3" "$COLLAB_RUN/run_manifest_s3.json"

# fc_reports
for fc in "$RUN_DIR"/karakulina_fc_report_iter*.json; do
    test -f "$fc" && cp "$fc" "$COLLAB_RUN/"
done

HIST=$(ls -t "$RUN_DIR"/karakulina_historian_*.json 2>/dev/null | head -1 || true)
test -n "$HIST" && cp "$HIST" "$COLLAB_RUN/historian_result_v34.json"

printf "# Run: %s (%s)\n\nАрхитектура: Phase A (Stage 1→2→3), оба транскрипта в Stage 1.\nPhase B отложена до Gate 1→4 PASS.\n\nGhostwriter v2.13 (универсальный), temp=0.4\nFC v2.6 (универсальный)\nLayout Designer v3.19 (универсальный, base v3.18)\nHistorian 12_historian_v3.md — ENABLED (streaming)\nTR1: assemblyai (%d bytes)\nTR2: meeting transcript (%d bytes)\n\n## Цель v34\nПервый прогон на полностью универсальных промптах (задача 010).\nBaseline для Gate 1→2a→2b→2c→3→4.\n" \
  "$PREFIX" "$TS" "$(wc -c < "$TR1")" "$(wc -c < "$TR2")" > "$COLLAB_RUN/README.md"

echo "${COLLAB_RUN}" > "$EXPORTS/karakulina_v34_last_collab_run.txt"

echo ""
echo "=============================================="
echo " DONE: ${PREFIX} (Phase A)"
echo " collab: $COLLAB_RUN"
echo " Gate 1: проверь karakulina_v35_FINAL_phase_a.txt"
echo "=============================================="
