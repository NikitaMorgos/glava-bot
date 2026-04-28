"""
Re-trigger Phase A with saved transcript for current user.
Reads transcript from /tmp/transcript.txt if it exists,
otherwise uses the latest voice message from DB.
"""
import json, os, sys, requests, psycopg2
sys.path.insert(0, '/opt/glava')
from dotenv import load_dotenv
load_dotenv('/opt/glava/.env')

WEBHOOK_URL = os.environ.get('N8N_WEBHOOK_PHASE_A', 'http://localhost:5678/webhook/glava/phase-a')
# Use internal URL to bypass nginx
WEBHOOK_INTERNAL = 'http://localhost:5678/webhook/glava/phase-a'

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

# Find the user (Dmitriy / test user with photos)
cur.execute("""
    SELECT u.id, u.telegram_id, u.username,
           d.id as draft_id,
           COALESCE(d.characters->0->>'name', 'Герой книги') as character_name,
           d.status,
           (SELECT COUNT(*) FROM photos p WHERE p.user_id = u.id) as photo_count,
           (SELECT COUNT(*) FROM voice_messages v WHERE v.user_id = u.id) as voice_count
    FROM users u
    JOIN draft_orders d ON d.user_id = u.id AND d.status = 'paid'
    ORDER BY d.created_at DESC
    LIMIT 5
""")
rows = cur.fetchall()
print("Paid users with drafts:")
for r in rows:
    print(f"  telegram_id={r[1]} username={r[2]} draft_id={r[3]} "
          f"character={r[4]} photos={r[6]} voices={r[7]}")

# Use first user with photos
target = None
for r in rows:
    if r[6] > 0:  # has photos
        target = r
        break
if not target:
    target = rows[0] if rows else None

if not target:
    print("No target user found!")
    sys.exit(1)

telegram_id = target[1]
draft_id = target[3]
character_name = target[4] or 'Герой книги'
print(f"\nUsing: telegram_id={telegram_id} draft_id={draft_id} character={character_name}")

# Try to get transcript from file or DB
transcript = ''
if os.path.exists('/tmp/transcript.txt'):
    with open('/tmp/transcript.txt') as f:
        transcript = f.read().strip()
    print(f"Using transcript from file: {len(transcript)} chars")
else:
    cur.execute("""
        SELECT transcript FROM voice_messages
        WHERE user_id = (SELECT id FROM users WHERE telegram_id = %s)
          AND transcript IS NOT NULL AND transcript != ''
        ORDER BY created_at DESC LIMIT 1
    """, (telegram_id,))
    row = cur.fetchone()
    if row:
        transcript = row[0]
        print(f"Using transcript from DB: {len(transcript)} chars")

if not transcript:
    print("No transcript available! Cannot trigger Phase A.")
    sys.exit(1)

conn.close()

# Trigger Phase A
payload = {
    'telegram_id': telegram_id,
    'draft_id': draft_id,
    'character_name': character_name,
    'transcript': transcript,
    'photo_count': target[6],
}
print(f"\nTriggering Phase A: {WEBHOOK_INTERNAL}")
print(f"Payload size: {len(json.dumps(payload))} bytes")
print(f"Transcript preview: {transcript[:200]}...")

r = requests.post(WEBHOOK_INTERNAL, json=payload, timeout=30)
print(f"\nResponse: {r.status_code}")
print(r.text[:500])
