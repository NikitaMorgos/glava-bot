#!/bin/bash
set -e
export PYTHONUNBUFFERED=1
export ANTHROPIC_API_KEY=$(grep ANTHROPIC_API_KEY /opt/glava/.env | cut -d= -f2- | tr -d '"' | tr -d $'\r')
VENV=/opt/glava/venv/bin/python3
LAYOUT=/opt/glava/exports/karakulina_stage4_layout_iter1_20260501_075223.json
cd /opt/glava
echo "=== gate2b ==="
$VENV -u scripts/test_stage4_karakulina.py --acceptance-gate 2b --existing-layout $LAYOUT --approve-gate
echo "=== gate2c ==="
$VENV -u scripts/test_stage4_karakulina.py --acceptance-gate 2c --existing-layout $LAYOUT --approve-gate
echo "=== done ==="
