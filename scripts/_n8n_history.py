"""Get workflow history versions and execution error from n8n SQLite."""
import sqlite3, json, sys

conn = sqlite3.connect('/tmp/n8n.db')
cur = conn.cursor()

# 1. Get execution error for exec 68
print("=== EXECUTION DATA FOR RECENT FAILURES ===")
cur.execute("""
    SELECT ee.id, ee.status, ee.stoppedAt, 
           SUBSTR(ed.data, 1, 1500)
    FROM execution_entity ee
    JOIN execution_data ed ON ed.executionId = ee.id
    WHERE ee.id >= 64
    ORDER BY ee.id DESC
""")
for r in cur.fetchall():
    print(f"\nExec {r[0]} status={r[1]} stopped={r[2]}")
    raw = r[3]
    try:
        data = json.loads(raw) if raw else {}
        result = data.get('resultData') or data.get('data', {}).get('resultData', {}) or {}
        error = result.get('error') or data.get('error') or {}
        if error:
            print("Error:", json.dumps(error, ensure_ascii=False)[:600])
        else:
            print("Data keys:", list(data.keys()))
            if isinstance(data, dict) and 'resultData' in data:
                print("ResultData:", str(data['resultData'])[:300])
    except Exception as e:
        print("Parse error:", e, "raw:", raw[:200])

# 2. List workflow history versions
print("\n=== WORKFLOW HISTORY (Phase A) ===")
cur.execute("""
    SELECT wh.versionId, wh.createdAt, wh.authors
    FROM workflow_history wh
    WHERE wh.workflowId = 'Cr3pGd3OWqx5SnER'
    ORDER BY wh.createdAt DESC
    LIMIT 20
""")
versions = cur.fetchall()
for v in versions:
    print(f"  versionId={v[0]} created={v[1]} authors={v[2]}")

# 3. Get the LAST WORKING version (before 05:34 UTC = before our update)
# The update was at 05:34:53 UTC on 2026-03-20
# Exec 63 succeeded at 17:12 UTC on 2026-03-19
# So we want a version from AFTER 2026-03-19 and BEFORE 2026-03-20T05:34
print("\n=== LOOKING FOR VERSION FROM 2026-03-19 ===")
cur.execute("""
    SELECT wh.versionId, wh.createdAt, wh.authors,
           SUBSTR(wh.nodes, 1, 200)
    FROM workflow_history wh
    WHERE wh.workflowId = 'Cr3pGd3OWqx5SnER'
      AND wh.createdAt < '2026-03-20T05:34:00'
      AND wh.createdAt >= '2026-03-19T00:00:00'
    ORDER BY wh.createdAt DESC
    LIMIT 5
""")
prev_versions = cur.fetchall()
if prev_versions:
    print(f"Found {len(prev_versions)} versions from 2026-03-19")
    target = prev_versions[0]
    print(f"Best candidate: versionId={target[0]} created={target[1]}")
    print(f"Nodes preview: {target[3]}")
    
    # Get full nodes and connections for this version
    cur.execute("""
        SELECT nodes, connections
        FROM workflow_history
        WHERE workflowId = 'Cr3pGd3OWqx5SnER' AND versionId = ?
    """, (target[0],))
    full = cur.fetchone()
    if full and full[0]:
        print(f"Full nodes length: {len(full[0])}")
        print(f"Full connections length: {len(full[1] or '')}")
        # Save for restoration
        with open('/tmp/phase-a-prev-nodes.json', 'w') as f:
            f.write(full[0])
        with open('/tmp/phase-a-prev-connections.json', 'w') as f:
            f.write(full[1] or '{}')
        print("Saved to /tmp/phase-a-prev-nodes.json and /tmp/phase-a-prev-connections.json")
else:
    print("No versions found from 2026-03-19")
    # Show all available
    cur.execute("""
        SELECT versionId, createdAt
        FROM workflow_history
        WHERE workflowId = 'Cr3pGd3OWqx5SnER'
        ORDER BY createdAt DESC
        LIMIT 5
    """)
    print("Available versions:")
    for r in cur.fetchall():
        print(f"  {r[0]} {r[1]}")

conn.close()
