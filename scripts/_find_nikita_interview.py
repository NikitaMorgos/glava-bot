#!/usr/bin/env python3
"""Find Nikita/Tatiana interview in DB and filesystem"""
import os, sys, psycopg2
from dotenv import load_dotenv
load_dotenv('/opt/glava/.env')

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

print("=== Recent files (last 30 days) ===")
cur.execute("""
    SELECT id, user_id, created_at, file_type, file_size,
           LEFT(COALESCE(transcription_text,''), 120) as preview
    FROM user_files
    WHERE created_at > NOW() - INTERVAL '30 days'
    ORDER BY created_at DESC
    LIMIT 30
""")
for r in cur.fetchall():
    print(r)

print("\n=== Recent meetings ===")
try:
    cur.execute("""
        SELECT id, user_id, created_at, meeting_url, status,
               LEFT(COALESCE(transcript_text,''), 120) as preview
        FROM meetings
        WHERE created_at > NOW() - INTERVAL '30 days'
        ORDER BY created_at DESC
        LIMIT 20
    """)
    for r in cur.fetchall():
        print(r)
except Exception as e:
    print(f"meetings table error: {e}")

print("\n=== Users named Nikita/Tatiana ===")
cur.execute("""
    SELECT id, telegram_id, first_name, last_name, username, created_at
    FROM users
    WHERE LOWER(first_name) LIKE '%никита%'
       OR LOWER(first_name) LIKE '%татьяна%'
       OR LOWER(username) LIKE '%nikita%'
    ORDER BY created_at DESC
    LIMIT 10
""")
for r in cur.fetchall():
    print(r)

conn.close()
