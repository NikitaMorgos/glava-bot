"""Check execution details for last n8n run."""
import requests, json

N8N_API_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI5Njg3OTQzZS1jNDcxLTQ4ZjUtYTFkNC0wY2I2MjVmYzgxOGQiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiOGZkZjhlY2ItMWQ3Yi00NWFhLWEyNmItOGEwNzRlMzYwZjgxIiwiaWF0IjoxNzczOTE1NjE5LCJleHAiOjE3NzY0ODQ4MDB9.u7sguMtwETW7QuonWeemZhzKEasPcXpcw0KFi6XONSM'
BASE = 'http://localhost:5678'
headers = {'X-N8N-API-KEY': N8N_API_KEY}

r = requests.get(f'{BASE}/api/v1/executions/64', headers=headers, timeout=15)
ex = r.json()
print("Status:", ex.get('status'))
print("Mode:", ex.get('mode'))

data = ex.get('data') or {}
result = data.get('resultData') or {}
error = result.get('error') or data.get('error')
if error:
    print("\nTop-level error:")
    print(json.dumps(error, ensure_ascii=False, indent=2)[:1000])

run_data = result.get('runData') or {}
print(f"\nNodes that ran: {list(run_data.keys())}")

for node, node_data in run_data.items():
    if isinstance(node_data, list) and node_data:
        nd = node_data[0]
        err = nd.get('error')
        if err:
            print(f"\n[ERROR in {node}]:")
            print(json.dumps(err, ensure_ascii=False)[:500])
