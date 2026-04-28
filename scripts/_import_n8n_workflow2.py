"""Import updated phase-a workflow into n8n via API."""
import json, requests, sys

N8N_API_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI5Njg3OTQzZS1jNDcxLTQ4ZjUtYTFkNC0wY2I2MjVmYzgxOGQiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiOGZkZjhlY2ItMWQ3Yi00NWFhLWEyNmItOGEwNzRlMzYwZjgxIiwiaWF0IjoxNzczOTE1NjE5LCJleHAiOjE3NzY0ODQ4MDB9.u7sguMtwETW7QuonWeemZhzKEasPcXpcw0KFi6XONSM'
BASE = 'http://localhost:5678'
headers = {'X-N8N-API-KEY': N8N_API_KEY, 'Content-Type': 'application/json'}

# List ALL workflows
r = requests.get(f'{BASE}/api/v1/workflows?limit=50', headers=headers, timeout=10)
print('List workflows:', r.status_code)
workflows = r.json().get('data', [])
print(f"Total: {len(workflows)}")
for wf in workflows:
    print(f"  id={wf['id']} name={wf['name']} active={wf.get('active')}")

# Find Phase A by checking webhook path
print("\nSearching for Phase A by webhook...")
phase_a_wf = None
phase_a_id = None

for wf in workflows:
    wf_id = wf['id']
    # Quick check nodes in workflow list (summary)
    nodes = wf.get('nodes', [])
    for node in nodes:
        url = node.get('parameters', {}).get('path', '') or node.get('parameters', {}).get('url', '')
        if 'phase-a' in str(url):
            phase_a_wf = wf
            phase_a_id = wf_id
            print(f"Found via node url: id={wf_id} name={wf['name']}")
            break
    if phase_a_id:
        break

if not phase_a_id:
    # Try fetching each workflow and checking for phase-a webhook
    for wf in workflows:
        wf_id = wf['id']
        r2 = requests.get(f'{BASE}/api/v1/workflows/{wf_id}', headers=headers, timeout=10)
        wf_full = r2.json()
        if 'phase-a' in json.dumps(wf_full):
            phase_a_wf = wf
            phase_a_id = wf_id
            print(f"Found via full scan: id={wf_id} name={wf['name']}")
            break

if not phase_a_id:
    print("Phase A not found!")
    sys.exit(1)

# Get full existing workflow
r = requests.get(f'{BASE}/api/v1/workflows/{phase_a_id}', headers=headers, timeout=10)
existing = r.json()
existing_active = existing.get('active', False)
print(f"\nPhase A: id={phase_a_id} active={existing_active}")
print(f"Nodes: {len(existing.get('nodes', []))}")

# Load our updated workflow file
with open('/opt/glava/n8n-workflows/phase-a.json') as f:
    new_wf = json.load(f)

# Build minimal update payload (avoid extra settings fields)
update_payload = {
    'name': existing.get('name'),
    'nodes': new_wf.get('nodes', []),
    'connections': new_wf.get('connections', {}),
    'settings': {
        'executionOrder': existing.get('settings', {}).get('executionOrder', 'v1'),
    },
}

r = requests.put(f'{BASE}/api/v1/workflows/{phase_a_id}',
                 headers=headers, json=update_payload, timeout=30)
print(f"\nUpdate response: {r.status_code}")
if r.status_code == 200:
    updated = r.json()
    print(f"Updated nodes: {len(updated.get('nodes', []))}")
    for n in updated.get('nodes', []):
        nm = n.get('name', '')
        if 'Photo Editor' in nm or 'Send Bio PDF' in nm:
            print(f"\n  Node: {nm}")
            params = n.get('parameters', {})
            if 'Photo Editor' in nm:
                code = params.get('jsCode', '')
                print(f"    processed_photos: {'processed_photos' in code}")
            if 'Send Bio PDF' in nm:
                body = params.get('body', '')
                in_stringify = body.find('photo_layout') < body.find('}) }}') if '}) }}' in body else False
                print(f"    photo_layout present: {'photo_layout' in body}")
                print(f"    inside JSON.stringify: {in_stringify}")
    print("\nSUCCESS")
    # Reactivate
    if existing_active:
        r2 = requests.post(f'{BASE}/api/v1/workflows/{phase_a_id}/activate',
                           headers=headers, timeout=10)
        print(f"Re-activated: {r2.status_code}")
else:
    print("Error:", r.text[:600])
