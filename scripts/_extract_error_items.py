"""Extract specific items from n8n binary exec data."""
import sqlite3, json

conn = sqlite3.connect('/tmp/n8n4.db')
cur = conn.cursor()
cur.execute("SELECT data FROM execution_data WHERE executionId = 66")
row = cur.fetchone()
conn.close()

data = json.loads(row[0])
print(f"Array has {len(data)} items")

# Show items that might contain error info
# Error object (item 4): level=13, description=15, name=18, node=19, message=22, stack=23
important_indices = [6, 13, 14, 15, 16, 18, 19, 22, 23]
for i in important_indices:
    if i < len(data):
        print(f"\n[{i}]: {str(data[i])[:500]}")

# The runData dict (item 5) shows node names → indices
# Let's look at the last node (Notify: Pipeline Started = "29") and items around it
print("\n\n=== Trying to find node errors ===")
run_dict = data[5]  # {"Webhook": "24", "Wrap Triage": "25", ...}
for node_name, idx_str in run_dict.items():
    idx = int(idx_str)
    if idx < len(data):
        node_data = data[idx]
        # node_data should be an array of task data
        print(f"\n{node_name} (idx {idx}): {str(node_data)[:200]}")
