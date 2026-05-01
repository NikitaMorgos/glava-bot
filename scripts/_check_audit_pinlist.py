import json, sys
audit = json.load(open('/opt/glava/exports/karakulina_v40b/karakulina_completeness_audit_20260501_075720.json'))
missing = audit.get('log_only_gaps', {}).get('missing_persons', [])
pin_list_flags = [p for p in missing if p.get('was_in_pin_list')]
print(f'log_only missing_persons total: {len(missing)}')
print(f'with was_in_pin_list=True: {len(pin_list_flags)}')
for p in pin_list_flags[:5]:
    name = p.get('mention_in_transcript') or p.get('likely_relation', '')
    reason = p.get('reason_low_confidence', '')[:80]
    print(f'  - {name} | {reason}')
ae = audit.get('auto_enrich', {})
print(f'auto_enrich persons: {len(ae.get("persons", []))}')
for p in ae.get('persons', [])[:5]:
    print(f'  + {p["name"]} ({p.get("relation_to_subject")})')
print('OK')
