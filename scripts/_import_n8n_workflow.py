"""Import updated phase-a workflow into n8n via API."""
import json, requests, sys

N8N_API_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI5Njg3OTQzZS1jNDcxLTQ4ZjUtYTFkNC0wY2I2MjVmYzgxOGQiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiOGZkZjhlY2ItMWQ3Yi00NWFhLWEyNmItOGEwNzRlMzYwZjgxIiwiaWF0IjoxNzczOTE1NjE5LCJleHAiOjE3NzY0ODQ4MDB9.u7sguMtwETW7QuonWeemZhzKEasPcXpcw0KFi6XONSM'
BASE = 'http://localhost:5678'
headers = {'X-N8N-API-KEY': N8N_API_KEY, 'Content-Type': 'application/json'}

# 1. Find Phase A workflow
r = requests.get(f'{BASE}/api/v1/workflows', headers=headers, timeout=10)
print('List workflows:', r.status_code)
workflows = r.json().get('data', [])
phase_a_wf = None
for wf in workflows:
    name = wf.get('name', '')
    print(f"  id={wf['id']} name={name} active={wf.get('active')}")
    if 'phase' in name.lower() and 'a' in name.lower():
        phase_a_wf = wf
        break

if not phase_a_wf:
    # Try by webhook path
    for wf in workflows:
        wf_id = wf['id']
        r2 = requests.get(f'{BASE}/api/v1/workflows/{wf_id}', headers=headers, timeout=10)
        if 'glava/phase-a' in str(r2.json()):
            phase_a_wf = wf
            break

if not phase_a_wf:
    print("Phase A workflow not found!")
    sys.exit(1)

wf_id = phase_a_wf['id']
wf_name = phase_a_wf.get('name', '')
wf_active = phase_a_wf.get('active', False)
print(f"\nFound Phase A: id={wf_id} name={wf_name} active={wf_active}")

# 2. Get full workflow
r = requests.get(f'{BASE}/api/v1/workflows/{wf_id}', headers=headers, timeout=10)
existing = r.json()
print("Current workflow nodes count:", len(existing.get('nodes', [])))

# 3. Load updated workflow
with open('/opt/glava/n8n-workflows/phase-a.json') as f:
    new_wf = json.load(f)

# 4. Merge: keep existing settings (id, name, active, settings, etc.)
# but update nodes and connections
update_payload = {
    'name': existing.get('name', new_wf.get('name', 'Phase A')),
    'nodes': new_wf.get('nodes', []),
    'connections': new_wf.get('connections', {}),
    'settings': existing.get('settings', new_wf.get('settings', {})),
    'staticData': existing.get('staticData'),
}

r = requests.put(f'{BASE}/api/v1/workflows/{wf_id}', headers=headers,
                 json=update_payload, timeout=30)
print(f"\nUpdate response: {r.status_code}")
if r.status_code == 200:
    updated = r.json()
    print("Updated nodes count:", len(updated.get('nodes', [])))
    # Check our nodes
    for n in updated.get('nodes', []):
        if 'Photo Editor' in n.get('name', '') or 'Send Bio PDF' in n.get('name', ''):
            print(f"  Node: {n['name']}")
            if 'Photo Editor' in n['name']:
                code = n.get('parameters', {}).get('jsCode', '')
                print(f"    processed_photos in code: {'processed_photos' in code}")
            if 'Send Bio PDF' in n['name']:
                body = n.get('parameters', {}).get('body', '')
                print(f"    photo_layout in body: {'photo_layout' in body}")
                print(f"    photo_layout inside stringify: {body.find('photo_layout') < body.find('}) }}')}")
    print("\nSUCCESS")
else:
    print("Error:", r.text[:500])
    # Re-activate if needed
if wf_active:
    r2 = requests.post(f'{BASE}/api/v1/workflows/{wf_id}/activate', headers=headers, timeout=10)
    print(f"Re-activate: {r2.status_code}")
