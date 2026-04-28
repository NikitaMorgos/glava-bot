"""Check n8n Webhook trigger node config and execution error details."""
import requests, json

N8N_API_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI5Njg3OTQzZS1jNDcxLTQ4ZjUtYTFkNC0wY2I2MjVmYzgxOGQiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiOGZkZjhlY2ItMWQ3Yi00NWFhLWEyNmItOGEwNzRlMzYwZjgxIiwiaWF0IjoxNzczOTE1NjE5LCJleHAiOjE3NzY0ODQ4MDB9.u7sguMtwETW7QuonWeemZhzKEasPcXpcw0KFi6XONSM'
BASE = 'http://localhost:5678'
WF_ID = 'Cr3pGd3OWqx5SnER'
headers = {'X-N8N-API-KEY': N8N_API_KEY}

# Get workflow details
r = requests.get(f'{BASE}/api/v1/workflows/{WF_ID}', headers=headers, timeout=10)
wf = r.json()

# Find Webhook node
for node in wf.get('nodes', []):
    if node.get('type') == 'n8n-nodes-base.webhook' or 'Webhook' in node.get('name', ''):
        if 'phase' in str(node.get('parameters', '')).lower() or node.get('name') == 'Webhook':
            print(f"Node name: {node['name']}")
            print(f"Type: {node['type']}")
            print(f"Parameters: {json.dumps(node.get('parameters', {}), indent=2, ensure_ascii=False)}")
            print()

# Check exec 66 error
print("=== Execution 66 error ===")
r = requests.get(f'{BASE}/api/v1/executions/66', headers=headers, timeout=10)
ex = r.json()
print("Status:", ex.get('status'))
data = ex.get('data') or {}
result = data.get('resultData') or {}
error = result.get('error') or {}
if error:
    print("Error:", json.dumps(error, ensure_ascii=False, indent=2)[:1000])
run_data = result.get('runData') or {}
print("Nodes ran:", list(run_data.keys()))
