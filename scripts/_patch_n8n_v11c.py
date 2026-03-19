# -*- coding: utf-8 -*-
"""
v11c: Переключает Historian с прямого OpenAI на Flask API /api/agents/historian.
      Также обновляет Wrap for Historian и Extract Historian под новый формат.
"""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WF   = os.path.join(ROOT, "n8n-workflows", "phase-a.json")

with open(WF, encoding="utf-8") as f:
    wf = json.load(f)

nodes = wf["nodes"]

for node in nodes:
    name = node.get("name", "")

    # 1. Historian -> теперь вызывает Flask API
    if name == "Historian":
        node["parameters"] = {
            "method": "POST",
            "url": "http://127.0.0.1:5001/api/agents/historian",
            "sendHeaders": True,
            "headerParameters": {"parameters": [
                {"name": "Content-Type", "value": "application/json"}
            ]},
            "sendBody": True,
            "contentType": "raw",
            "rawContentType": "application/json",
            "body": (
                "={{ JSON.stringify({"
                " fact_map: $('Extract Fact Map').first().json.fact_map || {},"
                " triage_result: $('Extract Triage').first().json.triage_result || {},"
                " character_name: $('Webhook').first().json.body.character_name || 'Герой книги',"
                " project_id: String($('Webhook').first().json.body.draft_id || $('Webhook').first().json.body.telegram_id)"
                " }) }}"
            ),
            "options": {"timeout": 120000}
        }
        print("Fixed: Historian -> Flask API")

    # 2. Extract Historian -> читает ответ Flask (уже {historical_context: {...}})
    if name == "Extract Historian":
        node["parameters"] = {
            "jsCode": (
                "const r = $input.first().json;"
                "const historical_context = r.historical_context || {};"
                "return [{ json: { historical_context } }];"
            ),
            "mode": "runOnceForAllItems"
        }
        print("Fixed: Extract Historian")

with open(WF, "w", encoding="utf-8") as f:
    json.dump(wf, f, ensure_ascii=False, indent=2)

print("\nDone v11c.")
