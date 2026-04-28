"""Trigger Phase A via EXTERNAL URL (same as production bot uses)."""
import json, os, sys, requests, psycopg2
sys.path.insert(0, '/opt/glava')
from dotenv import load_dotenv
load_dotenv('/opt/glava/.env')

# External webhook URL (via nginx proxy)
EXTERNAL_URL = 'https://admin.glava.family/n8n/webhook/glava/phase-a'
INTERNAL_URL = 'http://localhost:5678/webhook/glava/phase-a'

transcript = ''
if os.path.exists('/tmp/transcript.txt'):
    with open('/tmp/transcript.txt') as f:
        transcript = f.read().strip()
    print(f"Transcript: {len(transcript)} chars")

payload = {
    'telegram_id': 577528,
    'draft_id': 8,
    'character_name': 'Каракулина Валентина Ивановна',
    'transcript': transcript[:100] if transcript else 'тест',  # short for now
    'photo_count': 23,
    'bot_token': os.environ.get('BOT_TOKEN', ''),
    'admin_api_url': 'http://127.0.0.1:5001/api',
}

print(f"\n--- Testing INTERNAL URL ---")
try:
    r = requests.post(INTERNAL_URL, json=payload, timeout=10)
    print(f"Status: {r.status_code}")
    print(f"Response: {r.text[:200]}")
except Exception as e:
    print(f"Error: {e}")

print(f"\n--- Testing EXTERNAL URL ---")
try:
    r = requests.post(EXTERNAL_URL, json=payload, timeout=15, verify=False)
    print(f"Status: {r.status_code}")
    print(f"Response: {r.text[:200]}")
except Exception as e:
    print(f"Error: {e}")
