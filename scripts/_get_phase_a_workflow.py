#!/usr/bin/env python3
"""Download Phase A workflow from n8n and inspect Ghostwriter data flow."""
import requests, os, json, sys
sys.path.insert(0, '/opt/glava')
from dotenv import load_dotenv
load_dotenv('/opt/glava/.env')

N8N_KEY = os.environ.get('N8N_API_KEY', '')
BASE = 'http://localhost:5678/api/v1'
headers = {'X-N8N-API-KEY': N8N_KEY}

WF_ID = 'Cr3pGd3OWqx5SnER'  # Phase A
r = requests.get(f'{BASE}/workflows/{WF_ID}', headers=headers)
wf_data = r.json()
nodes = wf_data.get('nodes', [])
print(f"Phase A workflow: {wf_data.get('name')}")
print(f"Nodes count: {len(nodes)}")
print(f"\nAll node names:")
for n in nodes:
    print(f"  - {n.get('name')} ({n.get('type')})")

# Find nodes that process/pass transcript
print("\n=== Ghostwriter / Transcript nodes ===")
for node in nodes:
    name = node.get('name', '').lower()
    ntype = node.get('type', '')
    params = node.get('parameters', {})

    if any(kw in name for kw in ['ghostwriter', 'ghost', 'transcript', 'orchestrat', 'historian', 'bio']):
        print(f"\n--- {node.get('name')} ({ntype}) ---")
        if 'jsCode' in params:
            print("jsCode:", params['jsCode'][:2000])
        if 'body' in params:
            body = params['body']
            if isinstance(body, dict):
                print("body:", json.dumps(body, ensure_ascii=False)[:2000])
            else:
                print("body:", str(body)[:2000])
        if 'url' in params:
            print("url:", params['url'])
        if 'method' in params:
            print("method:", params['method'])

# Save full workflow
with open('/tmp/phase_a_full.json', 'w') as f:
    json.dump(wf_data, f, ensure_ascii=False, indent=2)
print(f"\n\nFull workflow saved to /tmp/phase_a_full.json ({len(json.dumps(wf_data))} chars)")
