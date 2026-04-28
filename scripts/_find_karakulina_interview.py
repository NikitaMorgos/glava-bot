#!/usr/bin/env python3
"""Find Karakulina interviews - voice messages and projects"""
import os, psycopg2, json
from dotenv import load_dotenv
load_dotenv('/opt/glava/.env')

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

print("=== recent voice_messages (last 30 days) ===")
cur.execute("""
    SELECT id, user_id, project_id, hero_id, narrator_id, 
           created_at, duration, interview_round,
           LEFT(COALESCE(transcript,''), 150) as transcript_preview,
           storage_key
    FROM voice_messages
    WHERE created_at > NOW() - INTERVAL '30 days'
    ORDER BY created_at DESC
    LIMIT 30
""")
for r in cur.fetchall():
    print(r)

print("\n=== projects ===")
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='projects' ORDER BY ordinal_position")
cols = [c[0] for c in cur.fetchall()]
print("columns:", cols)

cur.execute("""
    SELECT id, hero_id, user_id, status, created_at, updated_at
    FROM projects
    ORDER BY created_at DESC
    LIMIT 20
""")
for r in cur.fetchall():
    print(r)

print("\n=== heroes ===")
cur.execute("""
    SELECT id, user_id, name, created_at
    FROM heroes
    ORDER BY created_at DESC
    LIMIT 20
""")
for r in cur.fetchall():
    print(r)

print("\n=== pipeline_jobs (recent) ===")
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='pipeline_jobs' ORDER BY ordinal_position")
print("pipeline_jobs cols:", [c[0] for c in cur.fetchall()])
cur.execute("""
    SELECT id, project_id, status, stage, created_at, updated_at
    FROM pipeline_jobs
    ORDER BY created_at DESC
    LIMIT 10
""")
for r in cur.fetchall():
    print(r)

conn.close()
