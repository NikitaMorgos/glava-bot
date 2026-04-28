"""Check live workflow settings and try to trigger manually via n8n manual execution."""
import requests, json

N8N_API_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI5Njg3OTQzZS1jNDcxLTQ4ZjUtYTFkNC0wY2I2MjVmYzgxOGQiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiOGZkZjhlY2ItMWQ3Yi00NWFhLWEyNmItOGEwNzRlMzYwZjgxIiwiaWF0IjoxNzczOTE1NjE5LCJleHAiOjE3NzY0ODQ4MDB9.u7sguMtwETW7QuonWeemZhzKEasPcXpcw0KFi6XONSM'
BASE = 'http://localhost:5678'
WF_ID = 'Cr3pGd3OWqx5SnER'
headers = {'X-N8N-API-KEY': N8N_API_KEY}

r = requests.get(f'{BASE}/api/v1/workflows/{WF_ID}', headers=headers, timeout=10)
wf = r.json()

print("=== WORKFLOW SETTINGS ===")
print(json.dumps(wf.get('settings', {}), indent=2))

print("\n=== WORKFLOW TOP-LEVEL FIELDS ===")
for k, v in wf.items():
    if k not in ('nodes', 'connections'):
        print(f"  {k}: {str(v)[:100]}")

# Check the Webhook node carefully
print("\n=== WEBHOOK NODE FULL PARAMS ===")
for n in wf.get('nodes', []):
    if n.get('name') == 'Webhook':
        print(json.dumps(n, ensure_ascii=False, indent=2))
        break

# Try manual execution
print("\n=== TRYING MANUAL EXECUTION ===")
r2 = requests.post(f'{BASE}/api/v1/workflows/{WF_ID}/run',
                   headers=headers,
                   json={
                       'startNodes': [{'name': 'Webhook', 'sourceData': None}],
                       'runData': {},
                       'pinData': {}
                   },
                   timeout=15)
print(f"Manual run: {r2.status_code}")
print(r2.text[:300])
