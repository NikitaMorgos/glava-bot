"""Deep check of n8n execution failures."""
import sqlite3, json, subprocess

subprocess.run(['cp', '/opt/glava/n8n-data/.n8n/database.sqlite', '/tmp/n8n4.db'])
conn = sqlite3.connect('/tmp/n8n4.db')
cur = conn.cursor()

# Execution entity for recent execs
cur.execute("PRAGMA table_info(execution_entity)")
ee_cols = [r[1] for r in cur.fetchall()]

cur.execute("SELECT * FROM execution_entity WHERE id >= 68 ORDER BY id DESC LIMIT 5")
rows = cur.fetchall()
print("=== Recent executions ===")
for r in rows:
    d = dict(zip(ee_cols, r))
    print(f"Exec {d['id']}: status={d['status']} stopped={d['stoppedAt']} mode={d.get('mode','?')}")

# Check settings table
cur.execute("SELECT * FROM settings WHERE key LIKE '%binary%' OR key LIKE '%execution%'")
settings = cur.fetchall()
print("\n=== n8n settings ===")
for s in settings:
    print(f"  {s[0]}: {str(s[1])[:100]}")

# Check workflow entity for current settings
cur.execute("SELECT id, name, active, SUBSTR(settings, 1, 500) FROM workflow_entity WHERE id = 'Cr3pGd3OWqx5SnER'")
wf = cur.fetchone()
if wf:
    print(f"\n=== Workflow settings ===")
    print(f"id={wf[0]} name={wf[1]} active={wf[2]}")
    print(f"settings: {wf[3]}")

# Check execution_data for exec 68 (4 second failure)
cur.execute("SELECT executionId, workflowVersionId, length(data), SUBSTR(data, 1, 2000) FROM execution_data WHERE executionId = 68")
ed = cur.fetchone()
if ed:
    print(f"\n=== Exec 68 execution_data ===")
    print(f"versionId={ed[1]} data_len={ed[2]}")
    raw = ed[3]
    if raw:
        # Try to parse the n8n binary format
        try:
            data = json.loads(raw)
            if isinstance(data, list) and len(data) > 1:
                print("Binary format (indices):")
                # The error object is usually referenced by index "4"
                schema = data[0]
                if isinstance(schema, dict):
                    print("Schema:", json.dumps(schema)[:500])
                # Look for error in subsequent items
                for i, item in enumerate(data[1:], 1):
                    if isinstance(item, dict):
                        print(f"  Item {i}:", json.dumps(item)[:300])
                    elif isinstance(item, str) and len(item) > 0:
                        print(f"  Item {i} (str):", item[:300])
        except Exception as e:
            print(f"Parse error: {e}")
            print(f"Raw: {raw[:500]}")
else:
    print("\nNo execution_data for exec 68")
    # Check exec 66
    cur.execute("SELECT executionId, workflowVersionId, length(data), SUBSTR(data, 1, 3000) FROM execution_data WHERE executionId = 66")
    ed66 = cur.fetchone()
    if ed66:
        print(f"\n=== Exec 66 execution_data ===")
        print(f"versionId={ed66[1]} data_len={ed66[2]}")
        raw = ed66[3]
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                print(f"List length: {len(data)}")
                for i, item in enumerate(data):
                    if isinstance(item, dict):
                        print(f"  [{i}]: {json.dumps(item)[:400]}")
                    elif isinstance(item, str):
                        print(f"  [{i}] str: {item[:200]}")
        except Exception as e:
            print(f"Parse: {e}")
            print(raw[:500])

conn.close()
