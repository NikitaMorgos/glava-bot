import json
wf = json.load(open('n8n-workflows/phase-a.json', encoding='utf-8'))
targets = {'Wrap for Proofreader', 'Extract from Proofreader', 'Call Orch: Literary Edit', 'Call Orch: Fact Check'}
for n in wf['nodes']:
    if n['name'] in targets:
        params = n.get('parameters', {})
        body = params.get('body', '') or params.get('jsCode', '') or params.get('url', '')
        print("=== " + n['name'] + " ===")
        print(body[:1000])
        print()
