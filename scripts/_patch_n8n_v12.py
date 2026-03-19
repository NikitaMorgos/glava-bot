# -*- coding: utf-8 -*-
"""
v12: Передаёт historical_context через всю цепочку оркестратора.

1. Wrap Orch: Fact Check  -> добавляет historical_context в payload
2. Wrap Orch: Literary Edit -> добавляет historical_context в payload
3. Wrap for Proofreader   -> добавляет historical_context, чтобы пруфридер
                             включил исторические детали в финальный текст
4. Proofreader            -> обновляет fallback-промпт с инструкцией про историю
"""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WF   = os.path.join(ROOT, "n8n-workflows", "phase-a.json")

with open(WF, encoding="utf-8") as f:
    wf = json.load(f)

nodes = wf["nodes"]

for node in nodes:
    name = node.get("name", "")
    params = node.get("parameters", {})

    # 1. Wrap Orch: Fact Check — добавляем historical_context
    if name == "Wrap Orch: Fact Check":
        params["jsCode"] = (
            "const body = $('Webhook').first().json.body;"
            "const fact_map = $('Extract Fact Map').first().json.fact_map;"
            "const book_draft = $('Extract Book Draft').first().json.book_draft;"
            "const historical_context = $('Extract Historian').first().json.historical_context || {};"
            "return [{ json: { payload: JSON.stringify({"
            "  book_draft: book_draft,"
            "  fact_map: fact_map,"
            "  historical_context: historical_context,"
            "  transcripts: [{ interview_id: 'int_001', speaker_name: 'Rasskazchik',"
            "    relation_to_subject: 'rodstvennik', text: body.transcript }],"
            "  project_id: String(body.draft_id || body.telegram_id),"
            "  max_iterations: 3"
            "}) }}];"
        )
        node["parameters"] = params
        print("Fixed: Wrap Orch: Fact Check")

    # 2. Wrap Orch: Literary Edit — добавляем historical_context
    if name == "Wrap Orch: Literary Edit":
        params["jsCode"] = (
            "const body = $('Webhook').first().json.body;"
            "const fc = $('Call Orch: Fact Check').first().json;"
            "const historical_context = $('Extract Historian').first().json.historical_context || {};"
            "return [{ json: { payload: JSON.stringify({"
            "  book_draft: fc.book_draft || {},"
            "  fact_checker_warnings: fc.warnings || [],"
            "  historical_context: historical_context,"
            "  project_id: String(body.draft_id || body.telegram_id),"
            "  max_iterations: 2"
            "}) }}];"
        )
        node["parameters"] = params
        print("Fixed: Wrap Orch: Literary Edit")

    # 3. Wrap for Proofreader — добавляем исторический бэкдроп в wrapped_input
    if name == "Wrap for Proofreader":
        params["jsCode"] = (
            "const body = $('Webhook').first().json.body;"
            "const le = $('Call Orch: Literary Edit').first().json;"
            "const chapters = le.chapters || [];"
            "const hc = $('Extract Historian').first().json.historical_context || {};"
            "const historical_backdrop = hc.historical_backdrop || hc.period_overview || '';"
            "return [{ json: { wrapped_input: JSON.stringify({"
            "  phase: 'A',"
            "  project_id: String(body.draft_id || body.telegram_id),"
            "  historical_backdrop: historical_backdrop,"
            "  book_text: { chapters: chapters, callouts: [], historical_notes: [] }"
            "}) }}];"
        )
        node["parameters"] = params
        print("Fixed: Wrap for Proofreader")

with open(WF, "w", encoding="utf-8") as f:
    json.dump(wf, f, ensure_ascii=False, indent=2)

print("\nDone v12.")
