"""Query n8n SQLite database for execution errors."""
import sqlite3, json

conn = sqlite3.connect('/tmp/n8n.db')
cur = conn.cursor()

# Get recent executions with errors
cur.execute('''
    SELECT id, status, stoppedAt, 
           SUBSTR(data, 1, 2000)
    FROM execution_entity 
    ORDER BY id DESC 
    LIMIT 5
''')

for row in cur.fetchall():
    exec_id, status, stopped, data_str = row
    print(f"\n=== Exec {exec_id} status={status} stopped={stopped} ===")
    if data_str:
        try:
            data = json.loads(data_str)
            result = data.get('resultData', {}) or {}
            error = result.get('error', {})
            if error:
                print("Error:", json.dumps(error, ensure_ascii=False, indent=2)[:500])
            else:
                print("Data keys:", list(data.keys()))
                print("ResultData keys:", list(result.keys()))
        except Exception as e:
            print("Raw data:", data_str[:300])

conn.close()
