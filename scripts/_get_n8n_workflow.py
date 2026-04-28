#!/usr/bin/env python3
"""Download current Phase A workflow from n8n and save to file."""
import requests, os, json, sys
sys.path.insert(0, '/opt/glava')
from dotenv import load_dotenv
load_dotenv('/opt/glava/.env')

N8N_KEY = os.environ.get('N8N_API_KEY', '')
BASE = 'http://localhost:5678/api/v1'
headers = {'X-N8N-API-KEY': N8N_KEY}

# Get all workflows
r = requests.get(f'{BASE}/workflows', headers=headers)
wfs = r.json().get('data', [])
print(f"Found {len(wfs)} workflows:")
for wf in wfs:
    print(f"  id={wf['id']} name={wf['name']} active={wf['active']}")

# Get Phase A workflow (first one or the one named phase-a)
phase_a = None
for wf in wfs:
    if 'phase' in wf['name'].lower() or 'glava' in wf['name'].lower():
        phase_a = wf
        break
if not phase_a:
    phase_a = wfs[0] if wfs else None

if not phase_a:
    print("No workflow found!")
    sys.exit(1)

wf_id = phase_a['id']
print(f"\nDownloading workflow id={wf_id} name={phase_a['name']}")

r = requests.get(f'{BASE}/workflows/{wf_id}', headers=headers)
wf_data = r.json()
nodes = wf_data.get('nodes', [])
print(f"Nodes count: {len(nodes)}")

# Find Ghostwriter-related nodes
for node in nodes:
    name = node.get('name', '')
    ntype = node.get('type', '')
    if any(kw in name.lower() for kw in ['ghostwriter', 'ghost', 'writer', 'bio', 'transcript']):
        print(f"\n--- Node: {name} ({ntype}) ---")
        params = node.get('parameters', {})
        # Print relevant params
        if 'jsCode' in params:
            print("jsCode:", params['jsCode'][:1000])
        if 'body' in params:
            print("body:", json.dumps(params['body'], ensure_ascii=False)[:1000])
        if 'options' in params:
            print("options:", json.dumps(params['options'], ensure_ascii=False)[:500])

# Save full workflow
with open('/tmp/current_phase_a.json', 'w') as f:
    json.dump(wf_data, f, ensure_ascii=False, indent=2)
print(f"\nFull workflow saved to /tmp/current_phase_a.json")
