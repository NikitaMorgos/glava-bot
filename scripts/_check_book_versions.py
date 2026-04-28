#!/usr/bin/env python3
import psycopg2, os, sys
sys.path.insert(0, '/opt/glava')
from dotenv import load_dotenv
load_dotenv('/opt/glava/.env')

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

# Discover columns first
cur.execute("""
    SELECT column_name FROM information_schema.columns
    WHERE table_name = 'book_versions' ORDER BY ordinal_position
""")
cols = [r[0] for r in cur.fetchall()]
print("book_versions columns:", cols)

cur.execute('''
    SELECT id, created_at, length(bio_text) as bio_len
    FROM book_versions
    ORDER BY created_at DESC LIMIT 6
''')
rows = cur.fetchall()
print(f"\nLatest book versions ({len(rows)}):")
for r in rows:
    print(f"  id={r[0]} bio_len={r[2]} at={r[1]}")

# Check photos count for user
cur.execute('''
    SELECT u.id, u.telegram_id, COUNT(p.id) as photo_cnt
    FROM users u
    LEFT JOIN photos p ON p.user_id = u.id
    WHERE u.telegram_id = 577528
    GROUP BY u.id, u.telegram_id
''')
r = cur.fetchone()
if r:
    print(f"\nUser {r[1]}: {r[2]} photos in DB")

conn.close()
