"""Grep for error keywords in raw n8n execution data."""
import sqlite3, re

conn = sqlite3.connect('/tmp/n8n4.db')
cur = conn.cursor()
cur.execute("SELECT executionId, data FROM execution_data WHERE executionId = 66")
row = cur.fetchone()
conn.close()

if not row:
    print("No data")
    exit()

raw = row[1]
print(f"Exec 66 raw data ({len(raw)} bytes)")

# Find ALL quoted strings that contain error-related words
patterns = [
    r'"([^"]{10,300}(?:rror|ailed|xception|nvalid|orrupt|denied|timeout|refused)[^"]{0,200})"',
    r'"(Cannot[^"]{0,200})"',
    r'"(Unable[^"]{0,200})"',
    r'"(TypeError[^"]{0,200})"',
    r'"(SyntaxError[^"]{0,200})"',
    r'"(ReferenceError[^"]{0,200})"',
]

found = set()
for pattern in patterns:
    matches = re.findall(pattern, raw, re.IGNORECASE)
    for m in matches:
        if m not in found and len(m) > 20:
            found.add(m)
            print(f"\nFOUND: {m[:400]}")

if not found:
    # Just show 500 chars around "error" keyword
    idx = raw.lower().find('"error"')
    if idx != -1:
        print(f"\nContext around 'error': {raw[idx:idx+500]}")
    
    # Show the raw data between indices 60-100 (where error data usually lives)
    import json
    data = json.loads(raw)
    print(f"\nArray has {len(data)} items")
    print(f"Items 0-5:")
    for i in range(min(6, len(data))):
        print(f"  [{i}]: {str(data[i])[:150]}")
