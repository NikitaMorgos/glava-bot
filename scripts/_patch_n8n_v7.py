# -*- coding: utf-8 -*-
"""
Патч n8n workflow phase-a.json → v7.
Добавляет:
  - Triage Agent (перед Fact Extractor): определяет период, сложность, вариант пайплайна
  - Historian Agent (между Fact Extractor и Ghostwriter): добавляет исторический контекст
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
WF_PATH = os.path.join(ROOT, "n8n-workflows", "phase-a.json")

with open(WF_PATH, encoding="utf-8") as f:
    wf = json.load(f)

# ── jsCode strings ───────────────────────────────────────────────

TRIAGE_WRAP_JS = (
    "const body = $('Webhook').first().json.body;"
    "return [{ json: { wrapped_input: JSON.stringify({"
    "  phase: 'A',"
    "  character_name: body.character_name || 'Неизвестно',"
    "  transcript_length: (body.transcript || '').length,"
    "  transcript_excerpt: (body.transcript || '').slice(0, 3000),"
    "  photo_count: body.photo_count || 0,"
    "  known_birth_year: body.known_birth_year || null,"
    "  known_details: body.known_details || null"
    "}) }}];"
)

TRIAGE_EXTRACT_JS = (
    "const raw = $input.first().json.choices[0].message.content;"
    "let triage_result = { pipeline_variant: 'standard', subject_period: null,"
    "  birth_year_estimate: null, complexity: 'medium', primary_location: null };"
    "const t = raw.trim(); const s = t.indexOf('{'); const e = t.lastIndexOf('}');"
    "if (s !== -1 && e > s) { try { const p = JSON.parse(t.slice(s, e + 1));"
    "  if (p.pipeline_variant || p.complexity) triage_result = p; } catch(err) {} }"
    "return [{ json: { triage_result } }];"
)

HISTORIAN_WRAP_JS = (
    "const body = $('Webhook').first().json.body;"
    "const fact_map = $('Extract Fact Map').first().json.fact_map;"
    "const triage_result = $('Extract Triage').first().json.triage_result || {};"
    "const subject = fact_map.subject || {};"
    "const timeline = (fact_map.timeline || []).slice(0, 20);"
    "const locations = (fact_map.locations || []).map(l => l.name);"
    "return [{ json: { wrapped_input: JSON.stringify({"
    "  phase: 'A',"
    "  project_id: String(body.draft_id || body.telegram_id),"
    "  subject: {"
    "    name: body.character_name || subject.name || 'Неизвестно',"
    "    birth_year: subject.birth_year || triage_result.birth_year_estimate || null,"
    "    birth_place: subject.birth_place || triage_result.primary_location || null,"
    "    known_period: triage_result.subject_period || null"
    "  },"
    "  key_life_events: timeline.map(ev => ({ date: ev.date, event: ev.title || ev.event || '' })),"
    "  locations: locations,"
    "  complexity: triage_result.complexity || 'medium'"
    "}) }}];"
)

HISTORIAN_EXTRACT_JS = (
    "const raw = $input.first().json.choices[0].message.content;"
    "let historical_context = {};"
    "const t = raw.trim(); const s = t.indexOf('{'); const e = t.lastIndexOf('}');"
    "if (s !== -1 && e > s) { try { historical_context = JSON.parse(t.slice(s, e + 1)); } catch(err) {} }"
    "return [{ json: { historical_context } }];"
)

# Updated Wrap for Fact Extractor — now reads triage context
FE_WRAP_JS_NEW = (
    "const body = $('Webhook').first().json.body;"
    "const triage_result = $('Extract Triage').first().json.triage_result || {};"
    "return [{ json: { wrapped_input: JSON.stringify({"
    "  phase: 'A',"
    "  project_id: String(body.draft_id || body.telegram_id),"
    "  pipeline_variant: triage_result.pipeline_variant || 'standard',"
    "  subject: {"
    "    name: body.character_name || 'Герой книги',"
    "    known_birth_year: body.known_birth_year || triage_result.birth_year_estimate || null,"
    "    known_details: body.known_details || null"
    "  },"
    "  interview: {"
    "    id: 'int_001',"
    "    speaker: { name: 'Рассказчик', relation_to_subject: 'родственник' },"
    "    transcript: body.transcript"
    "  },"
    "  existing_facts: null"
    "}) }}];"
)

# Updated Wrap for Ghostwriter — now reads historian + triage context
GW_WRAP_JS_NEW = (
    "const body = $('Webhook').first().json.body;"
    "const fact_map = $('Extract Fact Map').first().json.fact_map;"
    "const historical_context = $('Extract Historian').first().json.historical_context || {};"
    "const triage_result = $('Extract Triage').first().json.triage_result || {};"
    "return [{ json: { wrapped_input: JSON.stringify({"
    "  phase: 'A',"
    "  project_id: String(body.draft_id || body.telegram_id),"
    "  pipeline_variant: triage_result.pipeline_variant || 'standard',"
    "  subject: {"
    "    name: body.character_name || (fact_map.subject && fact_map.subject.name) || 'Герой книги'"
    "  },"
    "  fact_map: fact_map,"
    "  historical_context: historical_context,"
    "  transcripts: [{ interview_id: 'int_001', speaker_name: 'Рассказчик',"
    "    relation_to_subject: 'родственник', text: body.transcript }]"
    "}) }}];"
)

# ── Новые ноды ───────────────────────────────────────────────────

new_nodes = [
    # ── Triage Agent ─────────────────────────────────────────────
    {
        "id": "node-wrap-triage",
        "name": "Wrap Triage",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [-1000, 300],
        "parameters": {"mode": "runOnceForAllItems", "jsCode": TRIAGE_WRAP_JS},
    },
    {
        "id": "node-get-prompt-triage",
        "name": "Get Prompt: Triage",
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4,
        "position": [-750, 300],
        "parameters": {
            "url": "http://127.0.0.1:5001/api/prompts/triage_agent",
            "options": {"timeout": 10000},
        },
    },
    {
        "id": "node-triage-agent",
        "name": "Triage Agent",
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4,
        "position": [-500, 300],
        "parameters": {
            "method": "POST",
            "url": "https://api.openai.com/v1/chat/completions",
            "sendHeaders": True,
            "headerParameters": {"parameters": [
                {"name": "Authorization", "value": "={{ 'Bearer ' + $env.OPENAI_API_KEY }}"},
                {"name": "Content-Type", "value": "application/json"},
            ]},
            "sendBody": True,
            "contentType": "raw",
            "rawContentType": "application/json",
            "body": (
                "={{ JSON.stringify({ model: 'gpt-4o-mini', messages: ["
                " { role: 'system', content: $('Get Prompt: Triage').item.json.text ||"
                " 'Ты Триаж-агент. Проанализируй транскрипт и определи:"
                " 1) pipeline_variant (standard/extended/minimal),"
                " 2) subject_period (например \"1940-1980 СССР\"),"
                " 3) birth_year_estimate (число или null),"
                " 4) complexity (low/medium/high),"
                " 5) primary_location (страна/город или null)."
                " Верни только валидный JSON с этими полями и кратким reasoning.' },"
                " { role: 'user', content: $('Wrap Triage').item.json.wrapped_input }"
                " ], temperature: 0.1, max_tokens: 1000 }) }}"
            ),
            "options": {"timeout": 60000},
        },
    },
    {
        "id": "node-extract-triage",
        "name": "Extract Triage",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [-250, 300],
        "parameters": {"mode": "runOnceForAllItems", "jsCode": TRIAGE_EXTRACT_JS},
    },

    # ── Historian Agent ───────────────────────────────────────────
    {
        "id": "node-wrap-historian",
        "name": "Wrap Historian",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [1250, 600],
        "parameters": {"mode": "runOnceForAllItems", "jsCode": HISTORIAN_WRAP_JS},
    },
    {
        "id": "node-get-prompt-historian",
        "name": "Get Prompt: Historian",
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4,
        "position": [1500, 600],
        "parameters": {
            "url": "http://127.0.0.1:5001/api/prompts/historian",
            "options": {"timeout": 10000},
        },
    },
    {
        "id": "node-historian-agent",
        "name": "Historian Agent",
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4,
        "position": [1750, 600],
        "parameters": {
            "method": "POST",
            "url": "https://api.openai.com/v1/chat/completions",
            "sendHeaders": True,
            "headerParameters": {"parameters": [
                {"name": "Authorization", "value": "={{ 'Bearer ' + $env.OPENAI_API_KEY }}"},
                {"name": "Content-Type", "value": "application/json"},
            ]},
            "sendBody": True,
            "contentType": "raw",
            "rawContentType": "application/json",
            "body": (
                "={{ JSON.stringify({ model: 'gpt-4o-mini', messages: ["
                " { role: 'system', content: $('Get Prompt: Historian').item.json.text ||"
                " 'Ты Историк. На основе жизненных событий и периода героя дай исторический контекст:"
                " что происходило в стране и мире в ключевые моменты его жизни."
                " Верни только валидный JSON с полями:"
                " period_overview (string), key_historical_events (array of {year, event, relevance}),"
                " cultural_context (string), political_context (string),"
                " everyday_life_notes (string), historical_backdrop (string).' },"
                " { role: 'user', content: $('Wrap Historian').item.json.wrapped_input }"
                " ], temperature: 0.3, max_tokens: 3000 }) }}"
            ),
            "options": {"timeout": 120000},
        },
    },
    {
        "id": "node-extract-historian",
        "name": "Extract Historian",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [2000, 600],
        "parameters": {"mode": "runOnceForAllItems", "jsCode": HISTORIAN_EXTRACT_JS},
    },
]

# ── Добавить новые ноды ───────────────────────────────────────────
wf["nodes"].extend(new_nodes)

# ── Обновить jsCode в существующих нодах ─────────────────────────
for n in wf["nodes"]:
    if n["id"] == "node-wrap-fe":
        n["parameters"]["jsCode"] = FE_WRAP_JS_NEW
        print(f"  Updated: {n['name']}")
    elif n["id"] == "node-wrap-gw":
        n["parameters"]["jsCode"] = GW_WRAP_JS_NEW
        print(f"  Updated: {n['name']}")

# ── Обновить connections ──────────────────────────────────────────
c = wf["connections"]

# Webhook → Wrap Triage (вместо Wrap for Fact Extractor)
c["Webhook"] = {"main": [[{"node": "Wrap Triage", "type": "main", "index": 0}]]}

# Цепочка Triage
c["Wrap Triage"] = {"main": [[{"node": "Get Prompt: Triage", "type": "main", "index": 0}]]}
c["Get Prompt: Triage"] = {"main": [[{"node": "Triage Agent", "type": "main", "index": 0}]]}
c["Triage Agent"] = {"main": [[{"node": "Extract Triage", "type": "main", "index": 0}]]}
c["Extract Triage"] = {"main": [[{"node": "Wrap for Fact Extractor", "type": "main", "index": 0}]]}

# Extract Fact Map → Wrap Historian + Wrap for Photo Editor (убрать Wrap for Ghostwriter)
c["Extract Fact Map"] = {"main": [[
    {"node": "Wrap Historian", "type": "main", "index": 0},
    {"node": "Wrap for Photo Editor", "type": "main", "index": 0},
]]}

# Цепочка Historian → Wrap for Ghostwriter
c["Wrap Historian"] = {"main": [[{"node": "Get Prompt: Historian", "type": "main", "index": 0}]]}
c["Get Prompt: Historian"] = {"main": [[{"node": "Historian Agent", "type": "main", "index": 0}]]}
c["Historian Agent"] = {"main": [[{"node": "Extract Historian", "type": "main", "index": 0}]]}
c["Extract Historian"] = {"main": [[{"node": "Wrap for Ghostwriter", "type": "main", "index": 0}]]}

# ── Обновить версию ───────────────────────────────────────────────
wf["name"] = "GLAVA · Phase A — Book Pipeline v7 (Triage + Historian)"

with open(WF_PATH, "w", encoding="utf-8") as f:
    json.dump(wf, f, ensure_ascii=False, indent=2)

print(f"\nOK — phase-a.json updated to v7")
print(f"Nodes: {len(wf['nodes'])}")
print(f"Connections: {len(wf['connections'])}")

# ── Проверка ─────────────────────────────────────────────────────
print("\n=== CONNECTION CHECK ===")
print("Webhook ->", [x["node"] for row in c.get("Webhook", {}).get("main", []) for x in row])
print("Extract Triage ->", [x["node"] for row in c.get("Extract Triage", {}).get("main", []) for x in row])
print("Extract Fact Map ->", [x["node"] for row in c.get("Extract Fact Map", {}).get("main", []) for x in row])
print("Extract Historian ->", [x["node"] for row in c.get("Extract Historian", {}).get("main", []) for x in row])
print("Wrap for Ghostwriter ->", [x["node"] for row in c.get("Wrap for Ghostwriter", {}).get("main", []) for x in row])
