"""Compare node IDs between n8n live workflow and local JSON file."""
import requests, json

N8N_API_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI5Njg3OTQzZS1jNDcxLTQ4ZjUtYTFkNC0wY2I2MjVmYzgxOGQiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiOGZkZjhlY2ItMWQ3Yi00NWFhLWEyNmItOGEwNzRlMzYwZjgxIiwiaWF0IjoxNzczOTE1NjE5LCJleHAiOjE3NzY0ODQ4MDB9.u7sguMtwETW7QuonWeemZhzKEasPcXpcw0KFi6XONSM'
BASE = 'http://localhost:5678'
WF_ID = 'Cr3pGd3OWqx5SnER'
headers = {'X-N8N-API-KEY': N8N_API_KEY}

# Get live workflow
r = requests.get(f'{BASE}/api/v1/workflows/{WF_ID}', headers=headers, timeout=10)
live = r.json()
live_nodes = {n['id']: n['name'] for n in live.get('nodes', [])}
live_connections = live.get('connections', {})

# Get local workflow
with open('/opt/glava/n8n-workflows/phase-a.json') as f:
    local = json.load(f)
local_nodes = {n['id']: n['name'] for n in local.get('nodes', [])}
local_connections = local.get('connections', {})

print("=== NODE IDs COMPARISON ===")
print(f"Live nodes: {len(live_nodes)}, Local nodes: {len(local_nodes)}")

# Check IDs in live connections vs live nodes
live_node_ids = set(live_nodes.keys())
missing_from_connections = []
for src_name, conns in live_connections.items():
    if src_name not in {n['name'] for n in live.get('nodes', [])}:
        missing_from_connections.append(f"Source '{src_name}' not in live nodes")
    for port, targets in conns.items():
        for target_list in targets:
            for target in target_list:
                target_id = target.get('node')
                if target_id and target_id not in live_node_ids:
                    missing_from_connections.append(f"Target id '{target_id}' not in live node IDs")

if missing_from_connections:
    print("\nBROKEN connections:")
    for m in missing_from_connections[:20]:
        print(f"  {m}")
else:
    print("\nAll connections look valid")

# Show first few nodes from live vs local
print("\n=== LIVE NODES (first 10) ===")
for nid, name in list(live_nodes.items())[:10]:
    print(f"  {nid[:8]}... = {name}")

print("\n=== LOCAL NODES (first 10) ===")
for nid, name in list(local_nodes.items())[:10]:
    print(f"  {nid[:8]}... = {name}")

# Check if IDs match
live_ids = set(live_nodes.keys())
local_ids = set(local_nodes.keys())
only_in_live = live_ids - local_ids
only_in_local = local_ids - live_ids
print(f"\nIDs only in live (n8n has but local JSON doesn't): {len(only_in_live)}")
print(f"IDs only in local (local JSON has but n8n doesn't): {len(only_in_local)}")
if only_in_live:
    print("Only in live:", [(i[:8], live_nodes[i]) for i in list(only_in_live)[:5]])
if only_in_local:
    print("Only in local:", [(i[:8], local_nodes[i]) for i in list(only_in_local)[:5]])
