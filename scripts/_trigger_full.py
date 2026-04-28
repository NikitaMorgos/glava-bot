"""
Trigger Phase A with FULL payload matching pipeline_n8n.py format.
Includes bot_token, admin_api_url — everything the workflow needs.
"""
import os, sys, requests, psycopg2
sys.path.insert(0, '/opt/glava')
from dotenv import load_dotenv
load_dotenv('/opt/glava/.env')

WEBHOOK = 'http://localhost:5678/webhook/glava/phase-a'

transcript = ''
if os.path.exists('/tmp/transcript.txt'):
    with open('/tmp/transcript.txt') as f:
        transcript = f.read().strip()

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()
cur.execute("""
    SELECT u.id, u.telegram_id, u.username,
           d.id as draft_id,
           COALESCE(d.characters->0->>'name', 'Герой книги') as character_name,
           (SELECT COUNT(*) FROM photos p WHERE p.user_id = u.id) as photo_count
    FROM users u
    JOIN draft_orders d ON d.user_id = u.id AND d.status = 'paid'
    ORDER BY d.created_at DESC LIMIT 1
""")
r = cur.fetchone()
conn.close()

telegram_id, draft_id = r[1], r[3]
character_name = r[4]
photo_count = r[5]

# Full payload like pipeline_n8n.py
payload = {
    'telegram_id': telegram_id,
    'draft_id': draft_id,
    'character_name': character_name,
    'transcript': transcript,
    'photo_count': photo_count,
    'username': r[2] or '',
    'bot_token': os.environ.get('BOT_TOKEN', ''),
    'admin_api_url': os.environ.get('ADMIN_API_BASE_URL', 'http://127.0.0.1:5001/api'),
}

print(f"telegram_id: {telegram_id}")
print(f"draft_id: {draft_id}")
print(f"character: {character_name}")
print(f"photo_count: {photo_count}")
print(f"transcript: {len(transcript)} chars")
print(f"bot_token: {'SET' if payload['bot_token'] else 'MISSING'}")

r = requests.post(WEBHOOK, json=payload, timeout=30)
print(f"\nResponse: {r.status_code} {r.text[:200]}")
