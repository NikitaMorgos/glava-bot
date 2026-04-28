"""Check binary_data table and n8n error log for recent execs."""
import sqlite3, json, subprocess

subprocess.run(['cp', '/opt/glava/n8n-data/.n8n/database.sqlite', '/tmp/n8n3.db'])
conn = sqlite3.connect('/tmp/n8n3.db')
cur = conn.cursor()

# Check binary_data table structure
cur.execute("PRAGMA table_info(binary_data)")
cols = [r[1] for r in cur.fetchall()]
print("binary_data columns:", cols)

# Recent entries
cur.execute("SELECT * FROM binary_data ORDER BY id DESC LIMIT 5")
rows = cur.fetchall()
print(f"\nRecent binary_data entries: {len(rows)}")
for r in rows:
    print(f"  {[str(v)[:100] for v in r]}")

# Check execution_entity for status and error info
cur.execute("PRAGMA table_info(execution_entity)")
ee_cols = [r[1] for r in cur.fetchall()]
print(f"\nexecution_entity columns: {ee_cols}")

cur.execute("SELECT * FROM execution_entity WHERE id >= 69 ORDER BY id DESC LIMIT 5")
rows = cur.fetchall()
for r in rows:
    row_dict = dict(zip(ee_cols, r))
    print(f"\nExec {row_dict['id']}: status={row_dict['status']}, stopped={row_dict['stoppedAt']}")
    print(f"  All fields: {json.dumps({k: str(v)[:50] for k,v in row_dict.items()})}")

# Check if there are error messages in execution_metadata
cur.execute("PRAGMA table_info(execution_metadata)")
meta_cols = [r[1] for r in cur.fetchall()]
print(f"\nexecution_metadata columns: {meta_cols}")
cur.execute("SELECT * FROM execution_metadata WHERE executionId >= 69 ORDER BY executionId DESC LIMIT 5")
meta_rows = cur.fetchall()
print(f"Metadata for recent execs: {meta_rows}")

conn.close()
