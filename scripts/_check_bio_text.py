#!/usr/bin/env python3
import psycopg2, os, sys
sys.path.insert(0, '/opt/glava')
from dotenv import load_dotenv
load_dotenv('/opt/glava/.env')

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

# Get the latest bio text
cur.execute('''
    SELECT id, created_at, length(bio_text) as bio_len, bio_text
    FROM book_versions
    ORDER BY created_at DESC LIMIT 3
''')
rows = cur.fetchall()
for r in rows:
    vid, created, bio_len, bio_text = r
    print(f"\n=== Version {vid} ({bio_len} chars) at {created} ===")
    print(bio_text)
    print()

conn.close()
