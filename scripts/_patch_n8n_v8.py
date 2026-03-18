# -*- coding: utf-8 -*-
"""
Патч n8n workflow phase-a.json → v8.
Добавляет:
  - Cover Designer (параллельно с Proofreader после Literary Edit Loop)
  - Interview Architect улучшенный (использует Triage + Historian контекст)
  - Wrap for Layout Designer + Producer + Send Book PDF обновлены (включают cover_spec)
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
WF_PATH = os.path.join(ROOT, "n8n-workflows", "phase-a.json")

with open(WF_PATH, encoding="utf-8") as f:
    wf = json.load(f)

# ── jsCode строки ─────────────────────────────────────────────────

COVER_WRAP_JS = (
    "const body = $('Webhook').first().json.body;"
    "const fact_map = $('Extract Fact Map').first().json.fact_map;"
    "const historical_context = $('Extract Historian').first().json.historical_context || {};"
    "const triage_result = $('Extract Triage').first().json.triage_result || {};"
    "const subject = fact_map.subject || {};"
    "return [{ json: { wrapped_input: JSON.stringify({"
    "  phase: 'A',"
    "  project_id: String(body.draft_id || body.telegram_id),"
    "  subject: {"
    "    name: body.character_name || subject.name || 'Герой книги',"
    "    birth_year: subject.birth_year || triage_result.birth_year_estimate || null,"
    "    birth_place: subject.birth_place || triage_result.primary_location || null"
    "  },"
    "  period: triage_result.subject_period || null,"
    "  key_themes: triage_result.key_themes || [],"
    "  historical_backdrop: historical_context.historical_backdrop || '',"
    "  period_overview: historical_context.period_overview || '',"
    "  tone: triage_result.language_style || 'warm'"
    "}) }}];"
)

COVER_EXTRACT_JS = (
    "const raw = $input.first().json.choices[0].message.content;"
    "let cover_spec = { title: '', subtitle: 'Семейная биография', tagline: '',"
    "  image_description: '', visual_style: 'warm', color_palette: 'cream_gold' };"
    "const t = raw.trim(); const s = t.indexOf('{'); const e = t.lastIndexOf('}');"
    "if (s !== -1 && e > s) { try { const p = JSON.parse(t.slice(s, e + 1));"
    "  if (p.title || p.subtitle) cover_spec = { ...cover_spec, ...p }; } catch(err) {} }"
    "return [{ json: { cover_spec } }];"
)

# Wrap for Interview Architect — добавляет triage + historian контекст
IA_WRAP_JS_NEW = (
    "const body = $('Webhook').first().json.body;"
    "const fact_map = $('Extract Fact Map').first().json.fact_map;"
    "const book_draft = $('Extract Book Draft').first().json.book_draft;"
    "const triage_result = $('Extract Triage').first().json.triage_result || {};"
    "const historical_context = $('Extract Historian').first().json.historical_context || {};"
    "const subject = fact_map.subject || {};"
    "const chapters_summary = (book_draft.chapters || []).map(ch => ({"
    "  id: ch.id, title: ch.title || '',"
    "  brief_content: (ch.content || '').slice(0, 300) + '...'"
    "}));"
    "const historical_events = (historical_context.key_historical_events || []).slice(0, 5);"
    "return [{ json: { wrapped_input: JSON.stringify({"
    "  project_id: String(body.draft_id || body.telegram_id),"
    "  subject: {"
    "    name: body.character_name || subject.name || 'Герой книги',"
    "    birth_year: subject.birth_year || triage_result.birth_year_estimate || null,"
    "    death_year: subject.death_year || triage_result.death_year_estimate || null,"
    "    birth_place: subject.birth_place || triage_result.primary_location || null"
    "  },"
    "  period: triage_result.subject_period || null,"
    "  key_themes: triage_result.key_themes || [],"
    "  gaps: fact_map.gaps || [],"
    "  timeline: (fact_map.timeline || []).map(ev => ({"
    "    id: ev.id, date: ev.date, title: ev.title, life_period: ev.life_period,"
    "    confidence: ev.confidence"
    "  })),"
    "  persons: (fact_map.persons || []).map(p => ({"
    "    id: p.id, name: p.name, relation_to_subject: p.relation_to_subject"
    "  })),"
    "  locations: (fact_map.locations || []).map(l => ({ id: l.id, name: l.name })),"
    "  conflicts: fact_map.conflicts || [],"
    "  historical_gaps: historical_events.map(ev => ev.event || ''),"
    "  book_chapters_summary: chapters_summary,"
    "  complexity: triage_result.complexity || 'medium'"
    "}) }}];"
)

# Wrap for Layout Designer — добавляет cover_spec
LD_WRAP_JS_NEW = (
    "const body = $('Webhook').first().json.body;"
    "const bio_text = $('Extract from Proofreader').first().json.bio_text || '';"
    "const photo_layout = $('Extract from Photo Editor').first().json.photo_layout || [];"
    "const cover_spec = $('Extract Cover Designer').first().json.cover_spec || {};"
    "return [{ json: { wrapped_input: JSON.stringify({"
    "  phase: 'A',"
    "  project_id: String(body.draft_id || body.telegram_id),"
    "  bio_text_excerpt: bio_text.slice(0, 2000),"
    "  chapters_count: 4,"
    "  photo_placements: photo_layout,"
    "  cover_spec: cover_spec,"
    "  format: 'A5_print_ready',"
    "  style: cover_spec.visual_style || 'warm_book',"
    "  note: 'Создай спецификацию вёрстки PDF на основе обложки и содержания'"
    "}) }}];"
)

# Wrap for Producer — добавляет cover_spec для персонализации сообщения
PRODUCER_WRAP_JS_NEW = (
    "const body = $('Webhook').first().json.body;"
    "const bio_text = $('Extract from Proofreader').first().json.bio_text || '';"
    "const questions_text = $('Extract from Interview Architect').first().json.questions_text || '';"
    "const lqa = $('Call Orch: Layout QA').first().json;"
    "const cover_spec = $('Extract Cover Designer').first().json.cover_spec || {};"
    "const character_name = body.character_name || 'Герой книги';"
    "return [{ json: {"
    "  wrapped_input: JSON.stringify({"
    "    phase: 'A',"
    "    project_id: String(body.draft_id || body.telegram_id),"
    "    character_name: character_name,"
    "    book_title: cover_spec.title || character_name,"
    "    book_subtitle: cover_spec.subtitle || 'Семейная биография',"
    "    book_tagline: cover_spec.tagline || '',"
    "    book_status: 'ready',"
    "    chapters_count: 4,"
    "    book_excerpt: bio_text.slice(0, 400),"
    "    delivery_type: 'phase_a_v1',"
    "    layout_qa_verdict: lqa.verdict || 'pass',"
    "    estimated_pages: (lqa.layout_spec && lqa.layout_spec.estimated_pages) || null"
    "  }),"
    "  bio_text: bio_text,"
    "  questions_text: questions_text,"
    "  character_name: character_name,"
    "  cover_spec: cover_spec"
    "} }];"
)

# ── Новые ноды Cover Designer ─────────────────────────────────────

new_nodes = [
    {
        "id": "node-wrap-cover",
        "name": "Wrap Cover Designer",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [3000, 600],
        "parameters": {"mode": "runOnceForAllItems", "jsCode": COVER_WRAP_JS},
    },
    {
        "id": "node-get-prompt-cover",
        "name": "Get Prompt: Cover Designer",
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4,
        "position": [3250, 600],
        "parameters": {
            "url": "http://127.0.0.1:5001/api/prompts/cover_designer",
            "options": {"timeout": 10000},
        },
    },
    {
        "id": "node-cover-designer",
        "name": "Cover Designer",
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4,
        "position": [3500, 600],
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
                " { role: 'system', content: $('Get Prompt: Cover Designer').item.json.text ||"
                " 'Ты Дизайнер обложки семейной книги. Создай концепцию обложки."
                " Верни только валидный JSON с полями:"
                " title (заголовок книги — имя героя или поэтичное название),"
                " subtitle (подзаголовок, например: Семейная биография),"
                " tagline (короткая фраза 5-10 слов — суть жизни героя),"
                " image_description (описание образа для обложки в 2-3 предложения),"
                " visual_style (warm/classic/modern/vintage),"
                " color_palette (описание цветовой гаммы).' },"
                " { role: 'user', content: $('Wrap Cover Designer').item.json.wrapped_input }"
                " ], temperature: 0.6, max_tokens: 800 }) }}"
            ),
            "options": {"timeout": 60000},
        },
    },
    {
        "id": "node-extract-cover",
        "name": "Extract Cover Designer",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [3750, 600],
        "parameters": {"mode": "runOnceForAllItems", "jsCode": COVER_EXTRACT_JS},
    },
]

# ── Добавить новые ноды ────────────────────────────────────────────
wf["nodes"].extend(new_nodes)

# ── Обновить jsCode существующих нод ─────────────────────────────
for n in wf["nodes"]:
    if n["id"] == "node-wrap-ia":
        n["parameters"]["jsCode"] = IA_WRAP_JS_NEW
        print(f"  Updated: {n['name']}")
    elif n["id"] == "node-wrap-ld":
        n["parameters"]["jsCode"] = LD_WRAP_JS_NEW
        print(f"  Updated: {n['name']}")
    elif n["id"] == "node-wrap-producer":
        n["parameters"]["jsCode"] = PRODUCER_WRAP_JS_NEW
        print(f"  Updated: {n['name']}")

# Обновить Send Book PDF: добавить cover_spec в body
for n in wf["nodes"]:
    if n.get("name") == "Send Book PDF":
        old_body = n["parameters"].get("body", "")
        # Добавляем cover_spec в JSON body
        new_body = old_body.replace(
            "draft_id: $('Webhook').item.json.body.draft_id || 0",
            "draft_id: $('Webhook').item.json.body.draft_id || 0,"
            " cover_spec: $('Wrap for Producer').item.json.cover_spec || {}"
        )
        if new_body != old_body:
            n["parameters"]["body"] = new_body
            print(f"  Updated: {n['name']}")
        else:
            print(f"  WARNING: Send Book PDF body not updated (pattern not found)")

# ── Обновить connections ──────────────────────────────────────────
c = wf["connections"]

# Call Orch: Literary Edit → [Wrap for Proofreader, Wrap Cover Designer] (параллельно)
c["Call Orch: Literary Edit"] = {"main": [[
    {"node": "Wrap for Proofreader", "type": "main", "index": 0},
    {"node": "Wrap Cover Designer", "type": "main", "index": 0},
]]}

# Cover Designer цепочка
c["Wrap Cover Designer"] = {"main": [[{"node": "Get Prompt: Cover Designer", "type": "main", "index": 0}]]}
c["Get Prompt: Cover Designer"] = {"main": [[{"node": "Cover Designer", "type": "main", "index": 0}]]}
c["Cover Designer"] = {"main": [[{"node": "Extract Cover Designer", "type": "main", "index": 0}]]}
# Extract Cover Designer не имеет прямого downstream — данные читаются через $('Extract Cover Designer')
# Но нам нужно что-то запускать после него чтобы Layout Designer был в курсе.
# Оставим без прямого downstream — n8n всё равно выполнит, т.к. он параллельная ветка.

# ── Обновить версию ───────────────────────────────────────────────
wf["name"] = "GLAVA · Phase A — Book Pipeline v8 (Cover Designer + IA improved)"

with open(WF_PATH, "w", encoding="utf-8") as f:
    json.dump(wf, f, ensure_ascii=False, indent=2)

print(f"\nOK — phase-a.json updated to v8")
print(f"Nodes: {len(wf['nodes'])}")
print(f"Connections: {len(wf['connections'])}")

print("\n=== CONNECTION CHECK ===")
print("Call Orch: Literary Edit ->",
      [x["node"] for row in c.get("Call Orch: Literary Edit", {}).get("main", []) for x in row])
print("Cover Designer ->",
      [x["node"] for row in c.get("Cover Designer", {}).get("main", []) for x in row])
