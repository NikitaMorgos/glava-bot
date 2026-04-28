"""Decode exec 66 binary data to find the actual error."""
import sqlite3, json

conn = sqlite3.connect('/tmp/n8n4.db')
cur = conn.cursor()

cur.execute("SELECT data FROM execution_data WHERE executionId = 66")
row = cur.fetchone()
conn.close()

if not row or not row[0]:
    print("No data for exec 66")
    exit()

raw = row[0]
print(f"Data length: {len(raw)}")

# Parse the binary format
data = json.loads(raw)
print(f"Array length: {len(data)}")

# Build lookup dict from schema
# Schema: index 0 has {"version":1, "field_name": "index_string", ...}
schema_item = data[0] if isinstance(data[0], dict) else {}
# The schema maps field names to their index positions in the array
# e.g. {"error": "4", "runData": "5", ...}

# Resolve an index reference to actual data
def resolve(obj, data_arr):
    if isinstance(obj, str) and obj.isdigit():
        idx = int(obj)
        if idx < len(data_arr):
            return resolve(data_arr[idx], data_arr)
        return obj
    elif isinstance(obj, dict):
        return {k: resolve(v, data_arr) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [resolve(v, data_arr) for v in obj]
    return obj

# Find error
resultData = data[2]  # {"error": "4", "runData": "5", ...}
print("\nResultData schema:", json.dumps(resultData)[:300])

# Get error (index 4)
error_idx = int(resultData.get('error', '999').strip('"'))
if error_idx < len(data):
    error_raw = data[error_idx]
    print(f"\n=== ERROR (index {error_idx}) ===")
    if isinstance(error_raw, dict):
        print(json.dumps(resolve(error_raw, data), ensure_ascii=False, indent=2)[:2000])
    else:
        print(str(error_raw)[:500])

# Get runData (index 5)  
run_idx = int(resultData.get('runData', '999').strip('"'))
if run_idx < len(data):
    run_raw = data[run_idx]
    print(f"\n=== RUN DATA (index {run_idx}) ===")
    if isinstance(run_raw, dict):
        print("Nodes:", list(run_raw.keys())[:20])
        # Find error in each node
        for node_name, node_data in run_raw.items():
            nd = resolve(node_data, data) if isinstance(node_data, str) else node_data
            if isinstance(nd, list) and nd:
                nd0 = resolve(nd[0], data) if isinstance(nd[0], str) else nd[0]
                if isinstance(nd0, dict):
                    err = nd0.get('error')
                    if err:
                        print(f"\n  {node_name} ERROR:")
                        print(f"    {json.dumps(resolve(err, data), ensure_ascii=False)[:300]}")
    else:
        print(str(run_raw)[:200])
