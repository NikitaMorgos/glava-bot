# -*- coding: utf-8 -*-
"""
v11: Добавляет Historian в Phase A workflow.

Цепочка: Extract Fact Map -> Wrap for Historian -> Get Prompt: Historian
       -> Historian -> Extract Historian -> Wrap for Ghostwriter

(Wrap for Ghostwriter уже ссылается на $('Extract Historian'), нужно только добавить ноды)
"""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WF   = os.path.join(ROOT, "n8n-workflows", "phase-a.json")

with open(WF, encoding="utf-8") as f:
    wf = json.load(f)

nodes       = wf["nodes"]
connections = wf["connections"]

# ── Новые ноды историка ─────────────────────────────────────────────────────
historian_nodes = [
    {
        "parameters": {
            "jsCode": (
                "const body = $('Webhook').first().json.body;"
                "const fact_map = $('Extract Fact Map').first().json.fact_map;"
                "const triage = $('Extract Triage').first().json.triage_result || {};"
                "return [{ json: { wrapped_input: JSON.stringify({"
                "  phase: 'A',"
                "  project_id: String(body.draft_id || body.telegram_id),"
                "  character_name: body.character_name || 'Герой книги',"
                "  pipeline_variant: triage.pipeline_variant || 'standard',"
                "  subject_period: triage.subject_period || 'советский',"
                "  timeline: (fact_map && fact_map.timeline) || [],"
                "  subject: (fact_map && fact_map.subject) || {},"
                "  task: 'Добавь исторический контекст: что происходило в стране и мире в ключевые периоды жизни героя. Помоги читателю понять эпоху.'"
                "}) } }];"
            ),
            "mode": "runOnceForAllItems"
        },
        "id": "node-wrap-historian",
        "name": "Wrap for Historian",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [1250, 600]
    },
    {
        "parameters": {
            "url": "http://127.0.0.1:5001/api/prompts/historian",
            "options": {"timeout": 10000}
        },
        "id": "node-get-prompt-historian",
        "name": "Get Prompt: Historian",
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4,
        "position": [1500, 600]
    },
    {
        "parameters": {
            "method": "POST",
            "url": "https://api.openai.com/v1/chat/completions",
            "sendHeaders": True,
            "headerParameters": {"parameters": [
                {"name": "Authorization", "value": "={{ 'Bearer ' + $env.OPENAI_API_KEY }}"},
                {"name": "Content-Type",  "value": "application/json"}
            ]},
            "sendBody": True,
            "contentType": "raw",
            "rawContentType": "application/json",
            "body": (
                "={{ JSON.stringify({ model: 'gpt-4o-mini', messages: ["
                "{ role: 'system', content: $('Get Prompt: Historian').item.json.text || "
                "'Ты Историк. На основе карты фактов определи исторический контекст жизни героя. "
                "Верни JSON: {\"historical_context\": {\"era_overview\": \"краткий обзор эпохи\", "
                "\"key_events\": [{\"year\": 1960, \"event\": \"описание\"}], "
                "\"social_context\": \"социальный контекст\", \"cultural_notes\": \"культурные особенности\"}}' },"
                "{ role: 'user', content: $('Wrap for Historian').item.json.wrapped_input }"
                "], temperature: 0.3, max_tokens: 2000 }) }}"
            ),
            "options": {"timeout": 60000}
        },
        "id": "node-historian",
        "name": "Historian",
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4,
        "position": [1750, 600]
    },
    {
        "parameters": {
            "jsCode": (
                "const raw = $input.first().json.choices[0].message.content || '';"
                "let historical_context = {};"
                "const t = raw.trim();"
                "const s = t.indexOf('{'); const e = t.lastIndexOf('}');"
                "if (s !== -1 && e > s) {"
                "  try { const p = JSON.parse(t.slice(s, e+1));"
                "    historical_context = p.historical_context || p;"
                "  } catch(err) { historical_context = { era_overview: raw.slice(0, 500) }; }"
                "}"
                "return [{ json: { historical_context } }];"
            ),
            "mode": "runOnceForAllItems"
        },
        "id": "node-extract-historian",
        "name": "Extract Historian",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [2000, 600]
    }
]

# Добавляем ноды если их нет
existing_names = {n["name"] for n in nodes}
added = 0
for node in historian_nodes:
    if node["name"] not in existing_names:
        nodes.append(node)
        added += 1
        print(f"Added node: {node['name']}")
    else:
        print(f"Skip (exists): {node['name']}")

# ── Подключаем в connections ─────────────────────────────────────────────────

# Extract Fact Map -> Wrap for Historian (дополнительный выход, параллельно с Wrap for Ghostwriter)
if "Extract Fact Map" in connections:
    items = connections["Extract Fact Map"]["main"][0]
    existing_targets = {item["node"] for item in items}
    if "Wrap for Historian" not in existing_targets:
        items.append({"node": "Wrap for Historian", "type": "main", "index": 0})
        print("Connected: Extract Fact Map -> Wrap for Historian")
else:
    connections["Extract Fact Map"] = {
        "main": [[{"node": "Wrap for Historian", "type": "main", "index": 0}]]
    }
    print("Created connection: Extract Fact Map -> Wrap for Historian")

# Historian chain connections
historian_chain = [
    ("Wrap for Historian",      "Get Prompt: Historian"),
    ("Get Prompt: Historian",   "Historian"),
    ("Historian",               "Extract Historian"),
    ("Extract Historian",       "Wrap for Ghostwriter"),
]
for src, dst in historian_chain:
    if src not in connections:
        connections[src] = {"main": [[{"node": dst, "type": "main", "index": 0}]]}
        print(f"Created connection: {src} -> {dst}")
    else:
        targets = {i["node"] for i in connections[src]["main"][0]}
        if dst not in targets:
            connections[src]["main"][0].append({"node": dst, "type": "main", "index": 0})
            print(f"Connected: {src} -> {dst}")
        else:
            print(f"Already connected: {src} -> {dst}")

# ── Убираем прямую связь Extract Fact Map -> Wrap for Ghostwriter ─────────────
# (теперь идёт через Historian)
if "Extract Fact Map" in connections:
    before = len(connections["Extract Fact Map"]["main"][0])
    connections["Extract Fact Map"]["main"][0] = [
        i for i in connections["Extract Fact Map"]["main"][0]
        if i["node"] != "Wrap for Ghostwriter"
    ]
    after = len(connections["Extract Fact Map"]["main"][0])
    if before != after:
        print("Removed direct: Extract Fact Map -> Wrap for Ghostwriter")

with open(WF, "w", encoding="utf-8") as f:
    json.dump(wf, f, ensure_ascii=False, indent=2)

print(f"\nDone v11. Added {added} nodes.")
