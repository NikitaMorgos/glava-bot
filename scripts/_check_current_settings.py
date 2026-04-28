"""Check current workflow settings and execution_data for recent execs."""
import requests, json, sqlite3

N8N_API_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI5Njg3OTQzZS1jNDcxLTQ4ZjUtYTFkNC0wY2I2MjVmYzgxOGQiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiOGZkZjhlY2ItMWQ3Yi00NWFhLWEyNmItOGEwNzRlMzYwZjgxIiwiaWF0IjoxNzczOTE1NjE5LCJleHAiOjE3NzY0ODQ4MDB9.u7sguMtwETW7QuonWeemZhzKEasPcXpcw0KFi6XONSM'
BASE = 'http://localhost:5678'
WF_ID = 'Cr3pGd3OWqx5SnER'
headers = {'X-N8N-API-KEY': N8N_API_KEY}

r = requests.get(f'{BASE}/api/v1/workflows/{WF_ID}', headers=headers, timeout=10)
wf = r.json()
print("Settings:", json.dumps(wf.get('settings', {}), indent=2))
print("versionId:", wf.get('versionId'))
print("versionCounter:", wf.get('versionCounter'))

# Check execution_data for exec 70
# First copy fresh DB
import subprocess, os
subprocess.run(['cp', '/opt/glava/n8n-data/.n8n/database.sqlite', '/tmp/n8n2.db'])
conn = sqlite3.connect('/tmp/n8n2.db')
cur = conn.cursor()

cur.execute("SELECT executionId, length(workflowData), length(data), workflowVersionId FROM execution_data WHERE executionId >= 69 ORDER BY executionId DESC")
rows = cur.fetchall()
print(f"\nExecution data for recent execs: {rows}")

# Get exec 70 data
cur.execute("SELECT data FROM execution_data WHERE executionId = 70")
row = cur.fetchone()
if row:
    raw = row[0]
    print(f"Exec 70 data length: {len(raw) if raw else 0}")
    if raw:
        print(f"Raw preview: {raw[:500]}")
else:
    print("No exec_data for exec 70")

conn.close()
