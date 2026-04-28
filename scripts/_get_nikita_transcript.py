#!/usr/bin/env python3
"""Get full transcripts of Karakulina interviews + search filesystem for meeting recordings"""
import os, psycopg2
from dotenv import load_dotenv
load_dotenv('/opt/glava/.env')

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

print("=== FULL transcript vm_id=7 (2393s, user_id=2) ===")
cur.execute("SELECT transcript, duration, created_at, storage_key FROM voice_messages WHERE id=7")
row = cur.fetchone()
print(f"Duration: {row[1]}s ({row[1]//60} min), created: {row[2]}, key: {row[3]}")
print("--- TRANSCRIPT ---")
print(row[0])

print("\n\n=== FULL transcript vm_id=8 (814s, user_id=2) ===")
cur.execute("SELECT transcript, duration, created_at, storage_key FROM voice_messages WHERE id=8")
row = cur.fetchone()
print(f"Duration: {row[1]}s ({row[1]//60} min), created: {row[2]}, key: {row[3]}")
print("--- TRANSCRIPT ---")
print(row[0])

print("\n\n=== ALL voice_messages for user_id=2 (all time) ===")
cur.execute("""
    SELECT id, created_at, duration, interview_round,
           LEFT(COALESCE(transcript,''), 80) as preview,
           storage_key
    FROM voice_messages
    WHERE user_id=2
    ORDER BY created_at DESC
""")
for r in cur.fetchall():
    print(r)

print("\n\n=== project_states columns ===")
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='project_states' ORDER BY ordinal_position")
cols = [c[0] for c in cur.fetchall()]
print("cols:", cols)

conn.close()
