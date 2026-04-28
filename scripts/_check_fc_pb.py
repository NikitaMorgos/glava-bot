import json
r = json.load(open('/tmp/fc_pb_iter2.json', encoding='utf-8'))
errs = [e for e in r.get('errors', []) if e.get('severity') in ('critical', 'major')]
print(f"verdict: {r.get('verdict')}")
print(f"critical+major: {len(errs)}")
for e in errs[:5]:
    print(f"  [{e.get('severity')}] {e.get('type','?')} - {e.get('description','')[:80]}")
