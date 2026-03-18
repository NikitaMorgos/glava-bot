# -*- coding: utf-8 -*-
"""Фиксит invalid syntax в нодах State: assembling_phase_a и State: delivered_v1."""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WF = os.path.join(ROOT, "n8n-workflows", "phase-a.json")

with open(WF, encoding="utf-8") as f:
    wf = json.load(f)

ASSEMBLING_BODY = (
    "={{ JSON.stringify({"
    "  telegram_id: $('Webhook').first().json.body.telegram_id,"
    "  state: 'assembling_phase_a',"
    "  draft_id: $('Webhook').first().json.body.draft_id || 0,"
    "  character_name: $('Webhook').first().json.body.character_name || '',"
    "  phase: 'A'"
    "}) }}"
)

DELIVERED_BODY = (
    "={{ JSON.stringify({"
    "  telegram_id: $('Webhook').first().json.body.telegram_id,"
    "  state: 'delivered_v1',"
    "  draft_id: $('Webhook').first().json.body.draft_id || 0,"
    "  character_name: $('Webhook').first().json.body.character_name || '',"
    "  phase: 'A',"
    "  notes: 'PDF delivered'"
    "}) }}"
)

fixed = 0
for n in wf["nodes"]:
    name = n.get("name", "")
    if name == "State: assembling_phase_a":
        n["parameters"]["body"] = ASSEMBLING_BODY
        fixed += 1
        print(f"Fixed: {name}")
    elif name == "State: delivered_v1":
        n["parameters"]["body"] = DELIVERED_BODY
        fixed += 1
        print(f"Fixed: {name}")

with open(WF, "w", encoding="utf-8") as f:
    json.dump(wf, f, ensure_ascii=False, indent=2)

print(f"Done, fixed {fixed} nodes")
