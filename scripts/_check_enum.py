import psycopg2, os
conn = psycopg2.connect(os.environ["DATABASE_URL"])
cur = conn.cursor()
cur.execute("SELECT enum_range(NULL::draft_order_status)")
print("draft_order_status values:", cur.fetchone())
conn.close()
