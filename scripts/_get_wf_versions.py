"""Try n8n version history API to find previous working version."""
import requests, json

N8N_API_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI5Njg3OTQzZS1jNDcxLTQ4ZjUtYTFkNC0wY2I2MjVmYzgxOGQiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiOGZkZjhlY2ItMWQ3Yi00NWFhLWEyNmItOGEwNzRlMzYwZjgxIiwiaWF0IjoxNzczOTE1NjE5LCJleHAiOjE3NzY0ODQ4MDB9.u7sguMtwETW7QuonWeemZhzKEasPcXpcw0KFi6XONSM'
BASE = 'http://localhost:5678'
WF_ID = 'Cr3pGd3OWqx5SnER'
headers = {'X-N8N-API-KEY': N8N_API_KEY}

# Try various version history endpoints
endpoints = [
    f'{BASE}/api/v1/workflows/{WF_ID}/history',
    f'{BASE}/rest/workflows/{WF_ID}/history',
    f'{BASE}/rest/workflow-history/{WF_ID}',
]

for ep in endpoints:
    try:
        r = requests.get(ep, headers=headers, timeout=5)
        print(f"GET {ep}: {r.status_code}")
        if r.status_code == 200:
            print(r.text[:500])
    except Exception as e:
        print(f"Error: {e}")

# Try the REST API (not v1)
print("\n=== REST API ===")
r = requests.get(f'{BASE}/rest/workflows/{WF_ID}',
                 headers={'X-N8N-API-KEY': N8N_API_KEY,
                          'Cookie': ''},
                 timeout=10)
print(f"REST workflow: {r.status_code}")

# Check if there's a backup in /opt/glava
import os
backups = []
for dirpath, dirnames, filenames in os.walk('/opt/glava'):
    for f in filenames:
        if 'phase-a' in f.lower() and f.endswith('.json'):
            backups.append(os.path.join(dirpath, f))

print("\n=== PHASE-A JSON FILES ===")
for b in backups:
    print(f"  {b} ({os.path.getsize(b)} bytes, modified: {os.path.getmtime(b):.0f})")
