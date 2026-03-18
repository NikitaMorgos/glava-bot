# -*- coding: utf-8 -*-
"""Патч n8n workflow phase-a.json → v6 (review loops via Python orchestrator)."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
WF_PATH = os.path.join(ROOT, "n8n-workflows", "phase-a.json")

with open(WF_PATH, encoding="utf-8") as f:
    wf = json.load(f)

# ── 1. Новые ноды ────────────────────────────────────────────────

FC_WRAP_JS = (
    "const body = $('Webhook').first().json.body;"
    "const fact_map = $('Extract Fact Map').first().json.fact_map;"
    "const book_draft = $('Extract Book Draft').first().json.book_draft;"
    "return [{ json: { payload: JSON.stringify({"
    "  book_draft: book_draft,"
    "  fact_map: fact_map,"
    "  transcripts: [{ interview_id: 'int_001', speaker_name: 'Рассказчик',"
    "                  relation_to_subject: 'родственник', text: body.transcript }],"
    "  project_id: String(body.draft_id || body.telegram_id),"
    "  max_iterations: 3"
    "}) }}];"
)

LE_WRAP_JS = (
    "const body = $('Webhook').first().json.body;"
    "const fc = $('Call Orch: Fact Check').first().json;"
    "return [{ json: { payload: JSON.stringify({"
    "  book_draft: fc.book_draft || {},"
    "  fact_checker_warnings: fc.warnings || [],"
    "  project_id: String(body.draft_id || body.telegram_id),"
    "  max_iterations: 2"
    "}) }}];"
)

LQA_WRAP_JS = (
    "const body = $('Webhook').first().json.body;"
    "const ld = $('Extract from Layout Designer').first().json;"
    "const photo_layout = $('Extract from Photo Editor').first().json.photo_layout || [];"
    "const bio_text = $('Extract from Proofreader').first().json.bio_text || '';"
    "return [{ json: { payload: JSON.stringify({"
    "  layout_spec: ld.layout_spec || {},"
    "  bio_text: bio_text,"
    "  photo_layout: photo_layout,"
    "  project_id: String(body.draft_id || body.telegram_id),"
    "  max_iterations: 3"
    "}) }}];"
)

PR_WRAP_JS = (
    "const body = $('Webhook').first().json.body;"
    "const le = $('Call Orch: Literary Edit').first().json;"
    "const chapters = le.chapters || [];"
    "return [{ json: { wrapped_input: JSON.stringify({"
    "  phase: 'A',"
    "  project_id: String(body.draft_id || body.telegram_id),"
    "  book_text: { chapters: chapters, callouts: [], historical_notes: [] }"
    "}) }}];"
)

new_nodes = [
    {
        "id": "node-wrap-orch-fc",
        "name": "Wrap Orch: Fact Check",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [2250, 300],
        "parameters": {"mode": "runOnceForAllItems", "jsCode": FC_WRAP_JS},
    },
    {
        "id": "node-call-orch-fc",
        "name": "Call Orch: Fact Check",
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4,
        "position": [2500, 300],
        "parameters": {
            "method": "POST",
            "url": "http://127.0.0.1:5001/api/orchestrate/fact-check",
            "sendHeaders": True,
            "headerParameters": {"parameters": [{"name": "Content-Type", "value": "application/json"}]},
            "sendBody": True,
            "contentType": "raw",
            "rawContentType": "application/json",
            "body": "={{ $('Wrap Orch: Fact Check').item.json.payload }}",
            "options": {"timeout": 900000},
        },
    },
    {
        "id": "node-wrap-orch-le",
        "name": "Wrap Orch: Literary Edit",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [2750, 300],
        "parameters": {"mode": "runOnceForAllItems", "jsCode": LE_WRAP_JS},
    },
    {
        "id": "node-call-orch-le",
        "name": "Call Orch: Literary Edit",
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4,
        "position": [3000, 300],
        "parameters": {
            "method": "POST",
            "url": "http://127.0.0.1:5001/api/orchestrate/literary-edit",
            "sendHeaders": True,
            "headerParameters": {"parameters": [{"name": "Content-Type", "value": "application/json"}]},
            "sendBody": True,
            "contentType": "raw",
            "rawContentType": "application/json",
            "body": "={{ $('Wrap Orch: Literary Edit').item.json.payload }}",
            "options": {"timeout": 900000},
        },
    },
    {
        "id": "node-wrap-orch-lqa",
        "name": "Wrap Orch: Layout QA",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [6500, 300],
        "parameters": {"mode": "runOnceForAllItems", "jsCode": LQA_WRAP_JS},
    },
    {
        "id": "node-call-orch-lqa",
        "name": "Call Orch: Layout QA",
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4,
        "position": [6750, 300],
        "parameters": {
            "method": "POST",
            "url": "http://127.0.0.1:5001/api/orchestrate/layout-qa",
            "sendHeaders": True,
            "headerParameters": {"parameters": [{"name": "Content-Type", "value": "application/json"}]},
            "sendBody": True,
            "contentType": "raw",
            "rawContentType": "application/json",
            "body": "={{ $('Wrap Orch: Layout QA').item.json.payload }}",
            "options": {"timeout": 900000},
        },
    },
]

# ── 2. Удалить старые ноды ───────────────────────────────────────
REMOVE_IDS = {
    "node-wrap-fc", "node-get-prompt-fc", "node-fact-checker", "node-extract-fcr",
    "node-wrap-le", "node-get-prompt-le", "node-literary-editor", "node-extract-le",
    "node-wrap-lqa", "node-get-prompt-lqa", "node-layout-qa", "node-extract-lqa",
}
wf["nodes"] = [n for n in wf["nodes"] if n["id"] not in REMOVE_IDS]

# ── 3. Обновить jsCode в Wrap for Proofreader ────────────────────
for n in wf["nodes"]:
    if n["id"] == "node-wrap-pr":
        n["parameters"]["jsCode"] = PR_WRAP_JS
        print(f"  Updated jsCode: {n['name']}")

# ── 4. Обновить Wrap for Producer — читать из Call Orch: Layout QA
for n in wf["nodes"]:
    if n["id"] == "node-wrap-producer":
        old = n["parameters"]["jsCode"]
        n["parameters"]["jsCode"] = old.replace(
            "$('Extract from Layout QA')",
            "$('Call Orch: Layout QA')"
        )
        print(f"  Updated jsCode: {n['name']}")

# ── 5. Добавить новые ноды ────────────────────────────────────────
wf["nodes"].extend(new_nodes)

# ── 6. Обновить connections ──────────────────────────────────────
c = wf["connections"]

c["Extract Book Draft"]["main"] = [[
    {"node": "Wrap Orch: Fact Check", "type": "main", "index": 0},
    {"node": "Wrap for Interview Architect", "type": "main", "index": 0},
]]

c["Wrap Orch: Fact Check"] = {"main": [[{"node": "Call Orch: Fact Check", "type": "main", "index": 0}]]}
c["Call Orch: Fact Check"] = {"main": [[{"node": "Wrap Orch: Literary Edit", "type": "main", "index": 0}]]}
c["Wrap Orch: Literary Edit"] = {"main": [[{"node": "Call Orch: Literary Edit", "type": "main", "index": 0}]]}
c["Call Orch: Literary Edit"] = {"main": [[{"node": "Wrap for Proofreader", "type": "main", "index": 0}]]}

c["Extract from Layout Designer"] = {"main": [[{"node": "Wrap Orch: Layout QA", "type": "main", "index": 0}]]}
c["Wrap Orch: Layout QA"] = {"main": [[{"node": "Call Orch: Layout QA", "type": "main", "index": 0}]]}
c["Call Orch: Layout QA"] = {"main": [[{"node": "Merge: Layout + Questions", "type": "main", "index": 0}]]}

# Удалить старые ключи
for old_key in [
    "Wrap for Fact Checker", "Get Prompt: Fact Checker", "Fact Checker",
    "Extract Fact Checker Result", "Wrap for Literary Editor",
    "Get Prompt: Literary Editor", "Literary Editor", "Extract from Literary Editor",
    "Wrap for Layout QA", "Get Prompt: Layout QA", "Layout QA", "Extract from Layout QA",
]:
    c.pop(old_key, None)

# ── 7. Обновить версию ───────────────────────────────────────────
wf["name"] = "GLAVA · Phase A — Book Pipeline v6 (with review loops)"

with open(WF_PATH, "w", encoding="utf-8") as f:
    json.dump(wf, f, ensure_ascii=False, indent=2)

print(f"\nOK — phase-a.json updated to v6")
print(f"Nodes: {len(wf['nodes'])}")
print(f"Connections: {len(wf['connections'])}")
