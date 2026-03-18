# -*- coding: utf-8 -*-
"""
v10: Fix Send Bio PDF node connection + Wrap for Producer bio_text output.

Problems fixed:
1. Connection "Send Bio to Telegram" -> renamed to "Send Bio PDF to Telegram"
2. Wrap for Producer now returns bio_text + questions_text as top-level fields
3. Send Bio PDF body uses Extract from Proofreader for bio_text (more reliable)
"""
import json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WF = os.path.join(ROOT, "n8n-workflows", "phase-a.json")

with open(WF, encoding="utf-8") as f:
    wf = json.load(f)

nodes = wf["nodes"]
connections = wf["connections"]

# ─── 1. Fix Wrap for Producer: also output bio_text + questions_text ───────────
for n in nodes:
    if n.get("name") == "Wrap for Producer":
        old_js = n["parameters"]["jsCode"]
        # Add bio_text and questions_text to the returned json object
        # The jsCode currently ends with: return [{ json: { wrapped_input: ... } }]
        # We change it to return bio_text and questions_text as well
        new_js = old_js.replace(
            "return [{ json: {  wrapped_input: JSON.stringify({",
            "return [{ json: { bio_text, questions_text, wrapped_input: JSON.stringify({"
        )
        if new_js == old_js:
            # Try alternative pattern
            new_js = re.sub(
                r"return \[\{ json: \{(\s*)wrapped_input:",
                r"return [{ json: {\1bio_text,\1questions_text,\1wrapped_input:",
                old_js
            )
        n["parameters"]["jsCode"] = new_js
        print("Fixed: Wrap for Producer (added bio_text + questions_text outputs)")
        break

# ─── 2. Fix Send Bio PDF body: get bio_text from Wrap for Producer ─────────────
for n in nodes:
    if n.get("name") == "Send Bio PDF to Telegram":
        n["parameters"]["body"] = (
            "={{ JSON.stringify({ "
            "telegram_id: $('Webhook').item.json.body.telegram_id, "
            "bio_text: $('Wrap for Producer').item.json.bio_text || $('Extract from Proofreader').first().json.bio_text || '', "
            "character_name: $('Webhook').item.json.body.character_name || 'Герой книги', "
            "draft_id: $('Webhook').item.json.body.draft_id || 0, "
            "cover_spec: $('Extract Cover Designer').first().json.cover_spec || {} "
            "}) }}"
        )
        print("Fixed: Send Bio PDF to Telegram (body with cover_spec)")
        break

# ─── 3. Fix connections: replace "Send Bio to Telegram" with "Send Bio PDF to Telegram" ──
if "Extract from Producer" in connections:
    items = connections["Extract from Producer"]["main"][0]
    replaced = False
    for item in items:
        if item["node"] == "Send Bio to Telegram":
            item["node"] = "Send Bio PDF to Telegram"
            replaced = True
    if replaced:
        print("Fixed: connection 'Send Bio to Telegram' -> 'Send Bio PDF to Telegram'")
    else:
        # Maybe it's missing entirely, add it
        items.append({"node": "Send Bio PDF to Telegram", "type": "main", "index": 0})
        print("Added: connection Extract from Producer -> Send Bio PDF to Telegram")

# ─── 4. Add "Send Bio PDF to Telegram" -> "Update Job Status" connection ───────
if "Send Bio PDF to Telegram" not in connections:
    connections["Send Bio PDF to Telegram"] = {
        "main": [[{"node": "Update Job Status", "type": "main", "index": 0}]]
    }
    print("Added: connection Send Bio PDF to Telegram -> Update Job Status")

# ─── 5. Remove orphan "Send Bio to Telegram" from connections if still there ───
if "Send Bio to Telegram" in connections:
    del connections["Send Bio to Telegram"]
    print("Removed: orphan 'Send Bio to Telegram' connection entry")

with open(WF, "w", encoding="utf-8") as f:
    json.dump(wf, f, ensure_ascii=False, indent=2)

print("Done — phase-a.json v10 saved")
