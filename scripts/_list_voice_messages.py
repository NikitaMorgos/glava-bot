#!/usr/bin/env python3
"""Выводит все voice_messages с превью транскрипта"""
import os, psycopg2
from dotenv import load_dotenv
load_dotenv('/opt/glava/.env')

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()
cur.execute("""
    SELECT id, user_id, hero_id, narrator_id, created_at, duration,
           storage_key,
           LEFT(COALESCE(transcript,''), 200) as preview
    FROM voice_messages
    ORDER BY id
""")
for r in cur.fetchall():
    vm_id, user_id, hero_id, narrator_id, created_at, duration, key, preview = r
    mins = (duration or 0) // 60
    print(f"id={vm_id} user={user_id} hero={hero_id} narrator={narrator_id} dur={mins}min created={str(created_at)[:10]}")
    print(f"  key={key}")
    print(f"  preview={repr(preview[:150])}")
    print()
conn.close()
