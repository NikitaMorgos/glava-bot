import json

# Full diagnosis of FC iter3
r = json.load(open('/tmp/fc_iter3_v32.json', encoding='utf-8'))
print(f"=== FC iter3 verdict: {r.get('verdict')} ===")
print(f"Total errors: {len(r.get('errors', []))}")
print()

for e in r.get('errors', []):
    print(f"[{e.get('severity','?')}] type={e.get('type','?')} chapter={e.get('chapter_id','?')}")
    print(f"  desc: {e.get('description','')[:150]}")
    print()

# Check if timeline checked
summary = r.get('summary', {})
print("Summary:", json.dumps(summary, ensure_ascii=False, indent=2)[:500])

# Check explicit chapter_checks
chapter_checks = r.get('chapter_checks', {})
ch01 = chapter_checks.get('ch_01', {})
if ch01:
    print("\nch_01 check:", json.dumps(ch01, ensure_ascii=False, indent=2)[:300])

# Check notes/observations
notes = r.get('notes', '')
if notes:
    print(f"\nNotes: {str(notes)[:300]}")
