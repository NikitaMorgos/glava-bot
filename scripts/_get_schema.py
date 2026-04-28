import psycopg2, os, sys
sys.path.insert(0, '/opt/glava')
from dotenv import load_dotenv
load_dotenv('/opt/glava/.env')
conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='draft_orders' ORDER BY ordinal_position")
print("draft_orders columns:", [r[0] for r in cur.fetchall()])
conn.close()
