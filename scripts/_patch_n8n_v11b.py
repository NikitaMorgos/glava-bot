# -*- coding: utf-8 -*-
"""
v11b: Исправляет ноду Historian в Phase A.

Проблема: в workflow два историка:
  - "Historian Agent" (старый, с параметрами, ссылается на несуществующий "Wrap Historian")
  - "Historian" (новый от v11, пустой - без параметров, падает с invalid syntax)

Решение:
  1. Удалить "Historian Agent" (дубль)
  2. Заполнить "Historian" правильными параметрами (тело OpenAI запроса)
"""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WF   = os.path.join(ROOT, "n8n-workflows", "phase-a.json")

with open(WF, encoding="utf-8") as f:
    wf = json.load(f)

nodes = wf["nodes"]
connections = wf["connections"]

# Правильное тело запроса для Historian (без фигурных скобок в fallback-промпте)
HISTORIAN_BODY = (
    "={{ JSON.stringify({"
    " model: 'gpt-4o-mini',"
    " messages: ["
    "   { role: 'system', content: $('Get Prompt: Historian').item.json.text"
    "     || 'Ty Istorik. Na osnove faktov o geroe opishi istoricheskiy kontekst ego epokhi."
    "        Verni tolko validy JSON: period_overview, key_historical_events, cultural_context,"
    "        political_context, everyday_life_notes, historical_backdrop.' },"
    "   { role: 'user', content: $('Wrap for Historian').item.json.wrapped_input }"
    " ],"
    " temperature: 0.3,"
    " max_tokens: 3000"
    "}) }}"
)

# 1. Удаляем "Historian Agent" (дубль)
before = len(nodes)
nodes[:] = [n for n in nodes if n.get("name") != "Historian Agent"]
if len(nodes) < before:
    print("Removed: Historian Agent")

# Удаляем его из connections тоже
if "Historian Agent" in connections:
    del connections["Historian Agent"]
    print("Removed connections: Historian Agent")

# 2. Заполняем "Historian" правильными параметрами
for node in nodes:
    if node.get("name") == "Historian":
        node["parameters"] = {
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
            "body": HISTORIAN_BODY,
            "options": {"timeout": 120000}
        }
        print("Fixed parameters: Historian")
        break

# 3. Убеждаемся что связь Get Prompt: Historian -> Historian есть
if "Get Prompt: Historian" not in connections:
    connections["Get Prompt: Historian"] = {
        "main": [[{"node": "Historian", "type": "main", "index": 0}]]
    }
    print("Created connection: Get Prompt: Historian -> Historian")
else:
    targets = {i["node"] for i in connections["Get Prompt: Historian"]["main"][0]}
    if "Historian" not in targets:
        connections["Get Prompt: Historian"]["main"][0].append(
            {"node": "Historian", "type": "main", "index": 0}
        )
        print("Added connection: Get Prompt: Historian -> Historian")
    else:
        print("OK: Get Prompt: Historian -> Historian")

# 4. Historian -> Extract Historian
if "Historian" not in connections:
    connections["Historian"] = {
        "main": [[{"node": "Extract Historian", "type": "main", "index": 0}]]
    }
    print("Created connection: Historian -> Extract Historian")

with open(WF, "w", encoding="utf-8") as f:
    json.dump(wf, f, ensure_ascii=False, indent=2)

print("\nDone v11b.")
