"""Deactivate and reactivate Phase A workflow to clear webhook conflicts."""
import requests, time

N8N_API_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI5Njg3OTQzZS1jNDcxLTQ4ZjUtYTFkNC0wY2I2MjVmYzgxOGQiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiOGZkZjhlY2ItMWQ3Yi00NWFhLWEyNmItOGEwNzRlMzYwZjgxIiwiaWF0IjoxNzczOTE1NjE5LCJleHAiOjE3NzY0ODQ4MDB9.u7sguMtwETW7QuonWeemZhzKEasPcXpcw0KFi6XONSM'
BASE = 'http://localhost:5678'
WF_ID = 'Cr3pGd3OWqx5SnER'
headers = {'X-N8N-API-KEY': N8N_API_KEY}

print("1. Deactivating Phase A...")
r = requests.post(f'{BASE}/api/v1/workflows/{WF_ID}/deactivate', headers=headers, timeout=10)
print(f"   Deactivate: {r.status_code}")

print("2. Waiting 3 seconds...")
time.sleep(3)

print("3. Reactivating Phase A...")
r = requests.post(f'{BASE}/api/v1/workflows/{WF_ID}/activate', headers=headers, timeout=10)
print(f"   Activate: {r.status_code}")

print("4. Waiting 2 seconds...")
time.sleep(2)

print("5. Test webhook with small payload...")
r = requests.post('http://localhost:5678/webhook/glava/phase-a',
                  json={'telegram_id': 577528, 'draft_id': 8, 
                        'character_name': 'Test', 'transcript': 'test', 'photo_count': 5},
                  timeout=10)
print(f"   Webhook test: {r.status_code} {r.text[:200]}")
