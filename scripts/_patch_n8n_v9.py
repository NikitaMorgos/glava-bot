# -*- coding: utf-8 -*-
"""
Патч n8n workflow phase-a.json → v9.
Добавляет:
  - State transition: assembling_phase_a (сразу после Extract Triage)
  - State transition: delivered_v1 (после Update Job Status)
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
WF_PATH = os.path.join(ROOT, "n8n-workflows", "phase-a.json")

with open(WF_PATH, encoding="utf-8") as f:
    wf = json.load(f)

c = wf["connections"]

# ── Новые ноды ─────────────────────────────────────────────────────

new_nodes = [
    # State: assembling_phase_a — сразу после Extract Triage, перед Wrap for Fact Extractor
    {
        "id": "node-state-assembling",
        "name": "State: assembling_phase_a",
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4,
        "position": [-50, 300],
        "parameters": {
            "method": "POST",
            "url": "http://127.0.0.1:5001/api/state/transition",
            "sendHeaders": True,
            "headerParameters": {"parameters": [
                {"name": "Content-Type", "value": "application/json"}
            ]},
            "sendBody": True,
            "contentType": "raw",
            "rawContentType": "application/json",
            "body": (
                "={{ JSON.stringify({"
                "  telegram_id: $('Webhook').first().json.body.telegram_id,"
                "  state: 'assembling_phase_a',"
                "  draft_id: $('Webhook').first().json.body.draft_id || 0,"
                "  character_name: $('Webhook').first().json.body.character_name || null,"
                "  phase: 'A',"
                "  metadata: { pipeline_variant: $('Extract Triage').first().json.triage_result.pipeline_variant || 'standard' }"
                "}) }}"
            ),
            "options": {"timeout": 10000},
        },
    },
    # State: delivered_v1 — после Update Job Status
    {
        "id": "node-state-delivered",
        "name": "State: delivered_v1",
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4,
        "position": [9250, 450],
        "parameters": {
            "method": "POST",
            "url": "http://127.0.0.1:5001/api/state/transition",
            "sendHeaders": True,
            "headerParameters": {"parameters": [
                {"name": "Content-Type", "value": "application/json"}
            ]},
            "sendBody": True,
            "contentType": "raw",
            "rawContentType": "application/json",
            "body": (
                "={{ JSON.stringify({"
                "  telegram_id: $('Webhook').first().json.body.telegram_id,"
                "  state: 'delivered_v1',"
                "  draft_id: $('Webhook').first().json.body.draft_id || 0,"
                "  character_name: $('Webhook').first().json.body.character_name || null,"
                "  phase: 'A',"
                "  notes: 'PDF доставлен клиенту'"
                "}) }}"
            ),
            "options": {"timeout": 10000},
        },
    },
    # Уведомление клиенту: «Начинаем работу над вашей книгой»
    {
        "id": "node-notify-start",
        "name": "Notify: Pipeline Started",
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4,
        "position": [-50, 150],
        "parameters": {
            "method": "POST",
            "url": "={{ 'https://api.telegram.org/bot' + $('Webhook').first().json.body.bot_token + '/sendMessage' }}",
            "sendHeaders": True,
            "headerParameters": {"parameters": [
                {"name": "Content-Type", "value": "application/json"}
            ]},
            "sendBody": True,
            "contentType": "raw",
            "rawContentType": "application/json",
            "body": (
                "={{ JSON.stringify({"
                "  chat_id: $('Webhook').first().json.body.telegram_id,"
                "  text: '📖 Начинаем работу над вашей книгой. Это займёт несколько минут — мы пришлём результат сюда.'"
                "}) }}"
            ),
            "options": {"timeout": 15000},
        },
    },
]

wf["nodes"].extend(new_nodes)

# ── Обновить connections ──────────────────────────────────────────

# Extract Triage → State: assembling_phase_a + Notify: Pipeline Started (параллельно)
# State: assembling_phase_a → Wrap for Fact Extractor
c["Extract Triage"] = {"main": [[
    {"node": "State: assembling_phase_a", "type": "main", "index": 0},
    {"node": "Notify: Pipeline Started",  "type": "main", "index": 0},
]]}
c["State: assembling_phase_a"] = {"main": [[
    {"node": "Wrap for Fact Extractor", "type": "main", "index": 0}
]]}
# Notify не имеет downstream — просто параллельная ветка

# Update Job Status → State: delivered_v1
c["Update Job Status"] = {"main": [[
    {"node": "State: delivered_v1", "type": "main", "index": 0}
]]}

# ── Обновить версию ───────────────────────────────────────────────
wf["name"] = "GLAVA · Phase A — Book Pipeline v9 (State Machine)"

with open(WF_PATH, "w", encoding="utf-8") as f:
    json.dump(wf, f, ensure_ascii=False, indent=2)

print(f"OK — phase-a.json updated to v9")
print(f"Nodes: {len(wf['nodes'])}")

print("\n=== CONNECTION CHECK ===")
print("Extract Triage ->",
      [x["node"] for row in c.get("Extract Triage", {}).get("main", []) for x in row])
print("State: assembling_phase_a ->",
      [x["node"] for row in c.get("State: assembling_phase_a", {}).get("main", []) for x in row])
print("Update Job Status ->",
      [x["node"] for row in c.get("Update Job Status", {}).get("main", []) for x in row])
