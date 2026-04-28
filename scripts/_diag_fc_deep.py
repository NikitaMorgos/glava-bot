import json

r = json.load(open('/tmp/fc_iter3_v32.json', encoding='utf-8'))
print(f"verdict: {r.get('verdict')}")
print(f"errors: {len(r.get('errors', []))}")
print()

# Show full summary/assessment
summary = r.get('summary', {})
print("Summary overall_assessment:")
print(summary.get('overall_assessment', 'N/A'))
print()

# Check warnings (not errors)
warnings = r.get('warnings', [])
print(f"Warnings ({len(warnings)}):")
for w in warnings:
    print(f"  {w}")
print()

# Check top-level keys
print("Top-level keys:", list(r.keys()))
print()

# Dump checks performed
checks = r.get('checks_performed', [])
if checks:
    print("Checks performed:")
    for c in checks[:10]:
        print(f"  {c}")

# Look for timeline reference
full_text = json.dumps(r, ensure_ascii=False)
if 'timeline' in full_text.lower():
    import re
    matches = re.findall(r'.{50}timeline.{50}', full_text, re.IGNORECASE)
    print("\ntimeline mentions in report:")
    for m in matches[:5]:
        print(f"  ...{m}...")
else:
    print("NO 'timeline' mention in fc_iter3 report at all!")

if 'historical_notes' in full_text.lower():
    print("\nhistorical_notes mentioned in report")
else:
    print("NO 'historical_notes' in fc_iter3 report!")

if 'раздражал' in full_text:
    print("\nраздражал mentioned in report!")
else:
    print("NO 'раздражал' in fc_iter3 report")
