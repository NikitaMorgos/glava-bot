"""Check n8n live workflow connections and look for issues."""
import requests, json

N8N_API_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI5Njg3OTQzZS1jNDcxLTQ4ZjUtYTFkNC0wY2I2MjVmYzgxOGQiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiOGZkZjhlY2ItMWQ3Yi00NWFhLWEyNmItOGEwNzRlMzYwZjgxIiwiaWF0IjoxNzczOTE1NjE5LCJleHAiOjE3NzY0ODQ4MDB9.u7sguMtwETW7QuonWeemZhzKEasPcXpcw0KFi6XONSM'
BASE = 'http://localhost:5678'
WF_ID = 'Cr3pGd3OWqx5SnER'
headers = {'X-N8N-API-KEY': N8N_API_KEY}

r = requests.get(f'{BASE}/api/v1/workflows/{WF_ID}', headers=headers, timeout=10)
wf = r.json()

# All node names
node_names = {n['name'] for n in wf.get('nodes', [])}
connections = wf.get('connections', {})

print("=== CONNECTION SOURCE NODES ===")
for src in connections:
    in_nodes = src in node_names
    if not in_nodes:
        print(f"  MISSING source: '{src}'")

print("\n=== CONNECTION TARGETS ===")
missing_targets = []
for src, conns in connections.items():
    for port, targets in conns.items():
        for target_list in targets:
            for target in target_list:
                t_name = target.get('node', '')
                if t_name and t_name not in node_names:
                    missing_targets.append(f"  '{src}' -> '{t_name}'")

if missing_targets:
    print("BROKEN targets:")
    for m in missing_targets:
        print(m)
else:
    print("All targets valid!")

# Show Webhook node connections
print("\n=== WEBHOOK CONNECTIONS ===")
wh_conns = connections.get('Webhook', {})
print(json.dumps(wh_conns, ensure_ascii=False, indent=2))

# Check what comes after Webhook
print("\n=== NODES AFTER WEBHOOK ===")
for port, targets in wh_conns.items():
    for tlist in targets:
        for t in tlist:
            print(f"  → {t.get('node')} (type={t.get('type')})")

# Also check if 'Wrap Triage' exists in the workflow
print(f"\n'Wrap Triage' in nodes: {'Wrap Triage' in node_names}")
print(f"'Wrap for Fact Extractor' in nodes: {'Wrap for Fact Extractor' in node_names}")
