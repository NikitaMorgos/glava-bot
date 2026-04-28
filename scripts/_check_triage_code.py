"""Check Wrap Triage code node in live n8n workflow."""
import requests, json

N8N_API_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI5Njg3OTQzZS1jNDcxLTQ4ZjUtYTFkNC0wY2I2MjVmYzgxOGQiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiOGZkZjhlY2ItMWQ3Yi00NWFhLWEyNmItOGEwNzRlMzYwZjgxIiwiaWF0IjoxNzczOTE1NjE5LCJleHAiOjE3NzY0ODQ4MDB9.u7sguMtwETW7QuonWeemZhzKEasPcXpcw0KFi6XONSM'
BASE = 'http://localhost:5678'
WF_ID = 'Cr3pGd3OWqx5SnER'
headers = {'X-N8N-API-KEY': N8N_API_KEY}

r = requests.get(f'{BASE}/api/v1/workflows/{WF_ID}', headers=headers, timeout=10)
wf = r.json()

# Check exec 67 full result
r2 = requests.get(f'{BASE}/api/v1/executions/67', headers=headers, timeout=15)
ex = r2.json()
data = ex.get('data', {}) or {}
result = data.get('resultData', {}) or {}
run_data = result.get('runData', {}) or {}
print("=== Exec 67 run data keys:", list(run_data.keys()))
full_error = result.get('error', {})
if full_error:
    print("\nTop error:", json.dumps(full_error, ensure_ascii=False, indent=2)[:2000])

# Check all code nodes
print("\n=== CODE NODES IN WORKFLOW ===")
for n in wf.get('nodes', []):
    if n.get('type') == 'n8n-nodes-base.code':
        code = n.get('parameters', {}).get('jsCode', '')
        print(f"\n[{n['name']}]")
        print(code[:300])
        print("...")

# Check Wrap Triage specifically
for n in wf.get('nodes', []):
    if 'Triage' in n.get('name', ''):
        print(f"\n=== WRAP TRIAGE ===")
        print(json.dumps(n.get('parameters', {}), ensure_ascii=False, indent=2)[:1000])
