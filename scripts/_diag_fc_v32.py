import json, glob
files = glob.glob('/opt/glava/exports/karakulina_v32_run_*/karakulina_fc_report_iter3_*.json')
if files:
    r = json.load(open(files[0]))
    errs = [e for e in r.get('errors', []) if e.get('severity') in ('critical', 'major')]
    print(f"verdict: {r.get('verdict')}")
    print(f"critical+major: {len(errs)}")
    for e in errs:
        print(f"  [{e.get('severity')}] {e.get('type','?')} — {e.get('description','')[:80]}")
else:
    print("No fc_report_iter3 found")
