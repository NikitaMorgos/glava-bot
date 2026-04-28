"""Monitor latest n8n execution."""
import requests, json, time, sys

N8N_API_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI5Njg3OTQzZS1jNDcxLTQ4ZjUtYTFkNC0wY2I2MjVmYzgxOGQiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiOGZkZjhlY2ItMWQ3Yi00NWFhLWEyNmItOGEwNzRlMzYwZjgxIiwiaWF0IjoxNzczOTE1NjE5LCJleHAiOjE3NzY0ODQ4MDB9.u7sguMtwETW7QuonWeemZhzKEasPcXpcw0KFi6XONSM'
WF_ID = 'Cr3pGd3OWqx5SnER'
BASE = 'http://localhost:5678'
headers = {'X-N8N-API-KEY': N8N_API_KEY}

r = requests.get(f'{BASE}/api/v1/executions?workflowId={WF_ID}&limit=3',
                 headers=headers, timeout=10)
executions = r.json().get('data', [])
print(f"Last {len(executions)} executions:")
for ex in executions:
    eid = ex['id']
    status = ex.get('status', '?')
    started = ex.get('startedAt', '')
    stopped = ex.get('stoppedAt', '')
    print(f"  id={eid} status={status} started={started} stopped={stopped}")

if executions:
    latest = executions[0]
    eid = latest['id']
    status = latest.get('status')
    print(f"\nLatest execution: {eid} / {status}")

    if status in ('running', 'waiting'):
        print("Still running... check back in a few minutes.")
    else:
        # Get details
        r2 = requests.get(f'{BASE}/api/v1/executions/{eid}', headers=headers, timeout=10)
        ex_detail = r2.json()
        data = ex_detail.get('data') or {}
        result_data = data.get('resultData') or {}
        run_data = result_data.get('runData') or {}

        # Check key nodes
        key_nodes = ['Fact Extractor', 'Ghostwriter', 'Extract Book Draft',
                     'Extract from Proofreader', 'Extract from Photo Editor',
                     'Send Bio PDF to Telegram']
        print("\nKey nodes status:")
        for node in key_nodes:
            nd = run_data.get(node, [{}])
            if nd:
                nd_data = nd[0] if isinstance(nd, list) else nd
                error = nd_data.get('error')
                output = nd_data.get('data', {})
                if isinstance(output, dict):
                    main = output.get('main', [[]])
                    items = main[0] if main else []
                    item_count = len(items)
                else:
                    item_count = '?'
                print(f"  {node}: items={item_count}" + (f" ERROR={error}" if error else ""))
            else:
                print(f"  {node}: NOT RUN")

        # Check bio_text from Proofreader
        proofreader_data = run_data.get('Extract from Proofreader', [{}])
        if proofreader_data:
            pd = proofreader_data[0] if isinstance(proofreader_data, list) else proofreader_data
            items = (pd.get('data', {}).get('main', [[]])[0] or [])
            if items:
                bio_text = items[0].get('json', {}).get('bio_text', '')
                print(f"\nbio_text length: {len(bio_text)}")
                print(f"bio_text preview: {bio_text[:300]}")

        # Check photo_layout from Photo Editor
        pe_data = run_data.get('Extract from Photo Editor', [{}])
        if pe_data:
            pd = pe_data[0] if isinstance(pe_data, list) else pe_data
            items = (pd.get('data', {}).get('main', [[]])[0] or [])
            if items:
                layout = items[0].get('json', {}).get('photo_layout', [])
                print(f"\nphoto_layout count: {len(layout)}")
                if layout:
                    print(f"First photo: {json.dumps(layout[0])[:200]}")
