#!/usr/bin/env python3
import os, psycopg2
from dotenv import load_dotenv
load_dotenv('/opt/glava/.env')

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

print("=== Все записи после 1 апреля 2026 ===")
cur.execute("""
    SELECT id, user_id, created_at, duration, storage_key,
           LEFT(COALESCE(transcript,''), 300) as preview
    FROM voice_messages
    WHERE created_at >= '2026-04-01'
    ORDER BY created_at
""")
rows = cur.fetchall()
print(f"Записей: {len(rows)}")
for r in rows:
    vm_id, user_id, created_at, duration, key, preview = r
    mins = (duration or 0) // 60
    print(f"\nid={vm_id} user={user_id} {str(created_at)[:16]} dur={mins}мин key={key}")
    print(f"  {repr(preview[:250])}")

# Также ищем по содержанию транскрипта — ключевая фраза из TR2
print("\n\n=== Поиск по ключевым словам TR2 (огурцы, Нинвана, счётчик) ===")
cur.execute("""
    SELECT id, user_id, created_at, duration, storage_key,
           LEFT(transcript, 200) as start,
           LENGTH(transcript) as tr_len
    FROM voice_messages
    WHERE transcript ILIKE '%огурц%'
       OR transcript ILIKE '%Нинван%'
       OR transcript ILIKE '%счётчик%'
    ORDER BY created_at
""")
rows2 = cur.fetchall()
print(f"Совпадений: {len(rows2)}")
for r in rows2:
    vm_id, user_id, created_at, duration, key, start, tr_len = r
    mins = (duration or 0) // 60
    print(f"\nid={vm_id} user={user_id} {str(created_at)[:10]} dur={mins}мин tr_len={tr_len} key={key}")

conn.close()
