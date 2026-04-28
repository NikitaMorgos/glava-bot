#!/usr/bin/env python3
"""List DB tables and find Nikita interview"""
import os, psycopg2
from dotenv import load_dotenv
load_dotenv('/opt/glava/.env')

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

print("=== All tables ===")
cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")
tables = [r[0] for r in cur.fetchall()]
print(tables)

print("\n=== Columns for audio/file related tables ===")
for t in tables:
    if any(x in t.lower() for x in ['file', 'audio', 'record', 'meet', 'transcript', 'upload', 'media']):
        cur.execute(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name='{t}' ORDER BY ordinal_position")
        cols = cur.fetchall()
        print(f"\n-- {t}: {[c[0] for c in cols]}")

conn.close()
