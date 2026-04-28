"""
Adds photo_layout to 'Send Bio PDF to Telegram' node in phase-a.json.
Run on the server: python3 scripts/_fix_n8n_photos.py
"""
import json
import sys

path = '/opt/glava/n8n-workflows/phase-a.json'

with open(path) as f:
    w = json.load(f)

nodes = w.get('nodes', [])
changed = []

for n in nodes:
    name = n.get('name', '')
    params = n.get('parameters', {})

    # Find the Send Bio PDF node and check body
    if 'Send Bio PDF' in name or 'send-book-pdf' in str(params):
        body = params.get('body', '')
        if not body:
            # maybe it's in a different param
            body = params.get('bodyParameters', {})
            print(f"Node '{name}' body type:", type(body))
            print(f"Node '{name}' params keys:", list(params.keys()))
            print("Body preview:", str(body)[:300])
            continue

        print(f"Node '{name}' body preview:", body[:400])
        print()
        if 'photo_layout' not in body:
            # Find a good insertion point
            needle = "cover_spec:"
            if needle in body:
                idx = body.rfind(needle)
                end_of_line = body.find('\n', idx)
                if end_of_line == -1:
                    end_of_line = len(body) - 1
                # Check what's at end of that line
                snippet = body[idx:end_of_line]
                print(f"Found '{needle}' at pos {idx}: {snippet}")
                params['body'] = body[:end_of_line] + ',\n  photo_layout: $(' + "'Extract from Photo Editor'" + ').first().json.photo_layout || []' + body[end_of_line:]
                changed.append(f'{name}: added photo_layout after cover_spec')
            else:
                print(f"WARNING: '{needle}' not found in body, trying closing brace")
                # Find closing }) and insert before it
                close = body.rfind('})')
                if close != -1:
                    params['body'] = body[:close] + ',\n  photo_layout: $(' + "'Extract from Photo Editor'" + ').first().json.photo_layout || []' + body[close:]
                    changed.append(f'{name}: added photo_layout before closing')
        else:
            print(f"Node '{name}': photo_layout already present")

with open(path, 'w') as f:
    json.dump(w, f, ensure_ascii=False, indent=2)

print('\nChanges made:')
for c in changed:
    print(' -', c)
if not changed:
    print('No changes made')
