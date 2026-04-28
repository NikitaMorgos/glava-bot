#!/usr/bin/env python3
import requests
import os
import sys
sys.path.insert(0, '/opt/glava')
from dotenv import load_dotenv
load_dotenv('/opt/glava/.env')

N8N_KEY = os.environ.get('N8N_API_KEY', '')
BASE = 'http://localhost:5678/api/v1'

headers = {'X-N8N-API-KEY': N8N_KEY}

r = requests.get(f'{BASE}/executions?limit=10', headers=headers)
if r.status_code != 200:
    print(f'Error: {r.status_code} {r.text[:300]}')
    sys.exit(1)

data = r.json()
executions = data.get('data', [])
print(f'Total executions returned: {len(executions)}')
print()
for e in executions:
    eid = e.get('id')
    status = e.get('status')
    started = e.get('startedAt', '')
    stopped = e.get('stoppedAt', 'still running')
    wf_name = e.get('workflowData', {}).get('name', 'unknown')
    print(f'exec={eid} [{status}] wf={wf_name} started={started} stopped={stopped}')
