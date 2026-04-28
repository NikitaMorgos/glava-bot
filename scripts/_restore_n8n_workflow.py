"""
Restore n8n workflow from the version that worked (2026-03-19 09:05 UTC),
then apply photo_layout patches on top.
"""
import sqlite3, json, requests, time

N8N_API_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI5Njg3OTQzZS1jNDcxLTQ4ZjUtYTFkNC0wY2I2MjVmYzgxOGQiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiOGZkZjhlY2ItMWQ3Yi00NWFhLWEyNmItOGEwNzRlMzYwZjgxIiwiaWF0IjoxNzczOTE1NjE5LCJleHAiOjE3NzY0ODQ4MDB9.u7sguMtwETW7QuonWeemZhzKEasPcXpcw0KFi6XONSM'
BASE = 'http://localhost:5678'
WF_ID = 'Cr3pGd3OWqx5SnER'
headers = {'X-N8N-API-KEY': N8N_API_KEY, 'Content-Type': 'application/json'}

# 1. Get the WORKING version nodes (f7dc1fc0 = 2026-03-19 09:05 UTC)
print("1. Loading working version from SQLite...")
conn = sqlite3.connect('/tmp/n8n.db')
cur = conn.cursor()
cur.execute("""
    SELECT nodes, connections 
    FROM workflow_history 
    WHERE workflowId = 'Cr3pGd3OWqx5SnER' 
      AND versionId = 'f7dc1fc0-399b-493d-bbb3-ad56b4fb28c8'
""")
row = cur.fetchone()
conn.close()

if not row or not row[0]:
    print("ERROR: Version f7dc1fc0 not found!")
    exit(1)

nodes = json.loads(row[0])
connections = json.loads(row[1] or '{}')
print(f"   Loaded {len(nodes)} nodes from working version")

# 2. Apply our photo patches to the working nodes
changes = []
for n in nodes:
    name = n.get('name', '')
    params = n.get('parameters', {})

    # Fix Extract from Photo Editor
    if name == 'Extract from Photo Editor':
        code = params.get('jsCode', '')
        if 'p.photos || []' in code and 'p.processed_photos' not in code:
            params['jsCode'] = code.replace(
                'photo_layout = p.photos || []',
                'photo_layout = p.processed_photos || p.photos || []'
            )
            changes.append(f'{name}: fixed p.processed_photos')
        elif 'p.processed_photos' in code:
            changes.append(f'{name}: already has p.processed_photos')

    # Fix Send Bio PDF to Telegram
    if name == 'Send Bio PDF to Telegram':
        body = params.get('body', '')
        print(f"   [Send Bio PDF] body preview: {body[:200]}")
        if 'photo_layout' not in body and 'JSON.stringify' in body:
            new_body = body.replace(
                ' }) }}',
                ", photo_layout: $('Extract from Photo Editor').first().json.photo_layout || [] }) }}"
            )
            if new_body != body:
                params['body'] = new_body
                changes.append(f'{name}: added photo_layout')
            else:
                print(f"   WARNING: Could not find ' }}) }}' to replace in body")
        elif 'photo_layout' in body:
            changes.append(f'{name}: already has photo_layout')

print(f"2. Patches applied: {changes}")

# 3. Deactivate current workflow
print("3. Deactivating current workflow...")
r = requests.post(f'{BASE}/api/v1/workflows/{WF_ID}/deactivate', headers=headers, timeout=10)
print(f"   {r.status_code}")
time.sleep(2)

# 4. Upload restored + patched workflow
print("4. Uploading restored workflow...")
update_payload = {
    'name': 'GLAVA · Phase A — Book Pipeline v9 (State Machine)',
    'nodes': nodes,
    'connections': connections,
    'settings': {
        'executionOrder': 'v1',
    },
}
r = requests.put(f'{BASE}/api/v1/workflows/{WF_ID}',
                 headers=headers, json=update_payload, timeout=30)
print(f"   Upload: {r.status_code}")
if r.status_code != 200:
    print(f"   Error: {r.text[:400]}")
else:
    updated = r.json()
    print(f"   Updated nodes: {len(updated.get('nodes', []))}")

time.sleep(2)

# 5. Reactivate
print("5. Reactivating...")
r = requests.post(f'{BASE}/api/v1/workflows/{WF_ID}/activate', headers=headers, timeout=10)
print(f"   {r.status_code}")
time.sleep(3)

# 6. Test
print("6. Testing webhook...")
r = requests.post('http://localhost:5678/webhook/glava/phase-a',
                  json={'telegram_id': 577528, 'draft_id': 8,
                        'character_name': 'Test', 'transcript': 'Тест транскрипт. Короткий.', 'photo_count': 5},
                  timeout=10)
print(f"   {r.status_code}: {r.text[:100]}")
