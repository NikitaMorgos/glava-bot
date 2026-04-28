"""
Download live n8n workflow, apply minimal patches, upload back.
This is safer than using our local JSON file which may have format differences.
"""
import requests, json, time

N8N_API_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI5Njg3OTQzZS1jNDcxLTQ4ZjUtYTFkNC0wY2I2MjVmYzgxOGQiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiOGZkZjhlY2ItMWQ3Yi00NWFhLWEyNmItOGEwNzRlMzYwZjgxIiwiaWF0IjoxNzczOTE1NjE5LCJleHAiOjE3NzY0ODQ4MDB9.u7sguMtwETW7QuonWeemZhzKEasPcXpcw0KFi6XONSM'
BASE = 'http://localhost:5678'
WF_ID = 'Cr3pGd3OWqx5SnER'
headers = {'X-N8N-API-KEY': N8N_API_KEY, 'Content-Type': 'application/json'}

# 1. Download current live workflow
print("1. Downloading live workflow...")
r = requests.get(f'{BASE}/api/v1/workflows/{WF_ID}', headers=headers, timeout=10)
wf = r.json()
existing_active = wf.get('active', False)
print(f"   Got workflow: {wf.get('name')}, nodes: {len(wf.get('nodes', []))}, active: {existing_active}")

# Save backup
with open('/tmp/phase-a-live-backup.json', 'w') as f:
    json.dump(wf, f, ensure_ascii=False, indent=2)
print("   Backup saved to /tmp/phase-a-live-backup.json")

nodes = wf.get('nodes', [])
changes = []

# 2. Apply patches
for n in nodes:
    name = n.get('name', '')
    params = n.get('parameters', {})

    # Fix 1: Extract from Photo Editor
    if name == 'Extract from Photo Editor':
        code = params.get('jsCode', '')
        if 'p.photos || []' in code and 'p.processed_photos' not in code:
            params['jsCode'] = code.replace(
                'photo_layout = p.photos || []',
                'photo_layout = p.processed_photos || p.photos || []'
            )
            changes.append(f'{name}: fixed p.processed_photos')

    # Fix 2: Send Bio PDF to Telegram - add photo_layout inside JSON.stringify
    if name == 'Send Bio PDF to Telegram':
        body = params.get('body', '')
        if 'photo_layout' not in body and 'JSON.stringify' in body:
            # Insert photo_layout before the closing }) }}
            new_body = body.replace(
                ' }) }}',
                ", photo_layout: $('Extract from Photo Editor').first().json.photo_layout || [] }) }}"
            )
            if new_body != body:
                params['body'] = new_body
                changes.append(f'{name}: added photo_layout to body')

print(f"\n2. Patches applied: {changes}")

# 3. Upload back (minimal payload - only name, nodes, connections, settings)
print("\n3. Deactivating...")
r = requests.post(f'{BASE}/api/v1/workflows/{WF_ID}/deactivate', headers=headers, timeout=10)
print(f"   Deactivate: {r.status_code}")
time.sleep(2)

print("4. Uploading patched workflow...")
update_payload = {
    'name': wf.get('name'),
    'nodes': nodes,
    'connections': wf.get('connections', {}),
    'settings': wf.get('settings', {}),
}
r = requests.put(f'{BASE}/api/v1/workflows/{WF_ID}',
                 headers=headers, json=update_payload, timeout=30)
print(f"   Upload: {r.status_code}")
if r.status_code != 200:
    print(f"   Error: {r.text[:500]}")
else:
    updated = r.json()
    print(f"   Updated nodes: {len(updated.get('nodes', []))}")

time.sleep(2)
print("5. Reactivating...")
r = requests.post(f'{BASE}/api/v1/workflows/{WF_ID}/activate', headers=headers, timeout=10)
print(f"   Activate: {r.status_code}")

time.sleep(3)
print("6. Testing webhook...")
r = requests.post('http://localhost:5678/webhook/glava/phase-a',
                  json={'telegram_id': 577528, 'draft_id': 8,
                        'character_name': 'Test', 'transcript': 'тестовый текст', 'photo_count': 5},
                  timeout=10)
print(f"   Webhook: {r.status_code} {r.text[:100]}")
