"""Fix photo_layout placement inside JSON.stringify in n8n workflow."""
import json

path = '/opt/glava/n8n-workflows/phase-a.json'

with open(path) as f:
    w = json.load(f)

nodes = w.get('nodes', [])

for n in nodes:
    name = n.get('name', '')
    params = n.get('parameters', {})

    if 'Send Bio PDF' in name:
        body = params.get('body', '')
        print(f"Current body:\n{body}\n")

        # The fix: photo_layout ended up OUTSIDE JSON.stringify - need to put it inside
        # Pattern to find and fix:
        # "... || {} }) }},\n  photo_layout: ...\n}}"
        # Should be:
        # "... || {}, photo_layout: ... }) }}"
        if 'photo_layout' in body and '}) }}' not in body:
            # Already correct form OR different structure
            print("Looks OK or unexpected structure")
        elif ') }},\n  photo_layout:' in body or ') }}' + '\n' in body:
            # Extract the photo_layout part
            import re
            # Match pattern: }) }},\n  photo_layout: EXPR\n}}
            m = re.search(r'\}\s*\)\s*\}\s*\}[^}]*photo_layout:\s*(.+?)(?:\n|\}\})', body, re.DOTALL)
            if m:
                photo_expr = m.group(1).strip().rstrip('}')
                # Rebuild: insert photo_layout inside stringify
                new_body = re.sub(
                    r'(cover_spec:[^\}]+\}\s*\))\s*\}\s*\}.*',
                    lambda x: x.group(1).rstrip(')') + f', photo_layout: {photo_expr}' + ') }}',
                    body,
                    flags=re.DOTALL
                )
                print(f"New body:\n{new_body}\n")
                params['body'] = new_body
            else:
                print("Pattern not matched, trying direct reconstruction")
                # Direct fix: rebuild body completely
                # Find where cover_spec value ends and photo_layout begins
                cover_idx = body.find('cover_spec:')
                photo_idx = body.find('photo_layout:')
                stringify_close = body.find('}) }}')

                if cover_idx != -1 and photo_idx != -1 and stringify_close != -1:
                    # Everything from start to stringify_close, then photo_layout, then close
                    photo_expr_start = photo_idx + len('photo_layout: ')
                    photo_expr = body[photo_expr_start:].split('\n')[0].strip().rstrip('}')
                    new_body = body[:stringify_close] + ', photo_layout: ' + photo_expr + ' }) }}'
                    print(f"Rebuilt body:\n{new_body}\n")
                    params['body'] = new_body
        else:
            # Check if photo_layout is inside JSON.stringify correctly
            js_close = body.find('}) }}')
            photo_idx = body.find('photo_layout:')
            if photo_idx != -1 and photo_idx < js_close:
                print("photo_layout is CORRECTLY inside JSON.stringify")
            elif photo_idx != -1 and photo_idx > js_close:
                print("photo_layout is OUTSIDE JSON.stringify - fixing...")
                # Move it inside
                photo_part = body[photo_idx:]
                # Extract photo expression
                photo_expr = photo_part.replace('photo_layout:', '').strip().rstrip('}').strip()
                # Rebuild
                before_close = body[:body.rfind('}) }}')]
                # Remove trailing whitespace and commas from before_close
                before_close = before_close.rstrip().rstrip(',').rstrip()
                new_body = before_close + ', photo_layout: ' + photo_expr + ' }) }}'
                print(f"Fixed body:\n{new_body}\n")
                params['body'] = new_body
            else:
                print("photo_layout not found or structure unexpected")

with open(path, 'w') as f:
    json.dump(w, f, ensure_ascii=False, indent=2)

print("Done.")
