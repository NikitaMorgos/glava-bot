"""Query n8n SQLite for schema and execution errors."""
import sqlite3, json

conn = sqlite3.connect('/tmp/n8n.db')
cur = conn.cursor()

# Get schema
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [r[0] for r in cur.fetchall()]
print("Tables:", tables)

# Get execution_entity columns
if 'execution_entity' in tables:
    cur.execute("PRAGMA table_info(execution_entity)")
    cols = [r[1] for r in cur.fetchall()]
    print("Columns:", cols)

    # Query recent executions
    cur.execute(f"SELECT id, status, stoppedAt, SUBSTR(workflowData, 1, 200) FROM execution_entity ORDER BY id DESC LIMIT 5")
    rows = cur.fetchall()
    for r in rows:
        print(f"\nExec {r[0]}: status={r[1]} stopped={r[2]}")
        print(f"  wfData preview: {r[3]}")
elif 'execution_annotations' in tables:
    cur.execute("PRAGMA table_info(execution_annotations)")
    cols2 = [r[1] for r in cur.fetchall()]
    print("Annotation cols:", cols2)

conn.close()
