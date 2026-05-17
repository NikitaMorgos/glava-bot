#!/usr/bin/env python3
import os, requests
from dotenv import load_dotenv
load_dotenv('/opt/glava/.env')

api_key = os.environ.get('ASSEMBLYAI_API_KEY', '')
headers = {'authorization': api_key}

# Транскрипт от 3 апреля 2026
transcript_id = 'dec7960b-c4d0-4bad-912e-013a6029b799'
resp = requests.get(
    f'https://api.assemblyai.com/v2/transcript/{transcript_id}',
    headers=headers,
)
t = resp.json()

print(f"ID: {t.get('id')}")
print(f"Status: {t.get('status')}")
print(f"Created: {t.get('created')}")
print(f"Audio duration: {t.get('audio_duration')} сек = {(t.get('audio_duration') or 0)//60} мин")
print(f"Audio URL: {t.get('audio_url')}")
print(f"Transcript начало: {(t.get('text') or '')[:400]}")
