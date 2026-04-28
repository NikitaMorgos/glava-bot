"""Simple search for error text in n8n execution data."""
import sqlite3, json

conn = sqlite3.connect('/tmp/n8n4.db')
cur = conn.cursor()

# Get ALL execution data at once
cur.execute("SELECT executionId, data FROM execution_data ORDER BY executionId DESC LIMIT 10")
rows = cur.fetchall()
conn.close()

for exec_id, raw in rows:
    if not raw:
        continue
    # Search for common error keywords
    if any(kw in raw for kw in ['Error', 'error', 'message', 'OPENAI', 'openai', 'stack']):
        print(f"\n=== Exec {exec_id} ===")
        # Parse as flat JSON and find string values that look like errors
        try:
            data = json.loads(raw)
            # Flatten to find error strings
            def find_strings(obj, depth=0):
                if depth > 5:
                    return
                if isinstance(obj, str) and len(obj) > 50:
                    # Check if it looks like an error message
                    lower = obj.lower()
                    if any(kw in lower for kw in ['error', 'failed', 'unauthorized', 'invalid', 'not found', 'timeout', 'cannot', 'unable']):
                        print(f"  STRING: {obj[:300]}")
                elif isinstance(obj, dict):
                    for k, v in obj.items():
                        if k in ('message', 'description', 'error', 'stack', 'name') and isinstance(v, str) and v:
                            print(f"  {k}: {v[:300]}")
                        else:
                            find_strings(v, depth+1)
                elif isinstance(obj, list):
                    for item in obj[:20]:
                        find_strings(item, depth+1)
            
            find_strings(data)
        except Exception as e:
            # Just search text
            for kw in ['Error', 'error', 'failed', 'stack']:
                idx = raw.find(kw)
                if idx != -1:
                    print(f"  Found '{kw}' at {idx}: ...{raw[max(0,idx-20):idx+200]}...")
                    break
        break
