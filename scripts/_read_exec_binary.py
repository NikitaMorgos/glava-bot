"""Read n8n execution data from SQLite (binary format)."""
import sqlite3, json, zlib, base64

conn = sqlite3.connect('/tmp/n8n.db')
cur = conn.cursor()

# Get the columns for execution_data
cur.execute("PRAGMA table_info(execution_data)")
cols = [r[1] for r in cur.fetchall()]
print("execution_data columns:", cols)

# Get recent execution data for exec 68 and 69
cur.execute("SELECT * FROM execution_data WHERE executionId >= 68 ORDER BY executionId DESC LIMIT 3")
rows = cur.fetchall()
for row in rows:
    print(f"\n--- executionId={row[0]} ---")
    # Try to decompress/decode each field
    for i, col in enumerate(cols):
        val = row[i]
        if val is None:
            continue
        if isinstance(val, bytes):
            try:
                decoded = zlib.decompress(val)
                print(f"  {col} (zlib, {len(decoded)}b): {decoded[:200]}")
            except:
                try:
                    print(f"  {col} (bytes, {len(val)}b): {val[:100]}")
                except:
                    pass
        elif isinstance(val, str) and len(val) > 0:
            # Try JSON parse with n8n binary format
            try:
                data = json.loads(val)
                if isinstance(data, list) and len(data) > 2:
                    # n8n binary format: [schema, ...chunks]
                    schema = data[0]
                    # Find error
                    error_str = None
                    for chunk in data[1:]:
                        if isinstance(chunk, dict) and 'error' in chunk:
                            error_str = chunk['error']
                        if isinstance(chunk, str) and ('error' in chunk.lower() or 'Error' in chunk):
                            error_str = chunk[:500]
                    if error_str:
                        print(f"  {col}: FOUND ERROR: {str(error_str)[:300]}")
                    else:
                        print(f"  {col} (json list, {len(data)} items, {len(val)}b)")
                else:
                    print(f"  {col}: {str(data)[:150]}")
            except:
                print(f"  {col} (str, {len(val)}b): {val[:100]}")

conn.close()
