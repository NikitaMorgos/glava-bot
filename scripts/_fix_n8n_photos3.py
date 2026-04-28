"""Directly rebuild Send Bio PDF body with photo_layout INSIDE JSON.stringify."""
import json

path = '/opt/glava/n8n-workflows/phase-a.json'

with open(path) as f:
    w = json.load(f)

for n in w.get('nodes', []):
    if 'Send Bio PDF' not in n.get('name', ''):
        continue

    params = n['parameters']
    # Set body to the correct expression with photo_layout inside JSON.stringify
    params['body'] = (
        "={{ JSON.stringify({ "
        "telegram_id: $('Webhook').item.json.body.telegram_id, "
        "bio_text: $('Wrap for Producer').item.json.bio_text || $('Extract from Proofreader').first().json.bio_text || '', "
        "character_name: $('Webhook').item.json.body.character_name || '\u0413\u0435\u0440\u043e\u0439 \u043a\u043d\u0438\u0433\u0438', "
        "draft_id: $('Webhook').item.json.body.draft_id || 0, "
        "cover_spec: $('Extract Cover Designer').first().json.cover_spec || {}, "
        "photo_layout: $('Extract from Photo Editor').first().json.photo_layout || [] "
        "}) }}"
    )
    print("Updated body:")
    print(params['body'])
    break

with open(path, 'w') as f:
    json.dump(w, f, ensure_ascii=False, indent=2)

print("\nDone.")
