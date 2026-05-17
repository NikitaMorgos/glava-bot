#!/usr/bin/env python3
import os, requests
from dotenv import load_dotenv
load_dotenv('/opt/glava/.env')

api_key = os.environ.get('ASSEMBLYAI_API_KEY', '')
headers = {'authorization': api_key}

# Листаем все страницы
next_url = 'https://api.assemblyai.com/v2/transcript?limit=50'
all_transcripts = []
while next_url:
    resp = requests.get(next_url, headers=headers)
    data = resp.json()
    batch = data.get('transcripts', [])
    all_transcripts.extend(batch)
    nxt = data.get('page_details', {}).get('next_url')
    if not nxt or nxt == next_url or len(all_transcripts) > 500:
        break
    next_url = nxt

print(f"Итого транскриптов: {len(all_transcripts)}")
print()

for t in sorted(all_transcripts, key=lambda x: x.get('created',''), reverse=True):
    tid = t.get('id')
    status = t.get('status')
    created = str(t.get('created',''))[:10]
    duration = t.get('audio_duration') or 0
    mins = int(duration) // 60
    audio_url = t.get('audio_url', '')
    print(f"{created}  {mins:3d}мин  {status:<12}  {tid}  {audio_url[:80]}")
