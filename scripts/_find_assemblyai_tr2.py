#!/usr/bin/env python3
"""Ищет в AssemblyAI транскрипты апреля 2026 — там должно быть аудио TR2"""
import os, requests
from dotenv import load_dotenv
load_dotenv('/opt/glava/.env')

api_key = os.environ.get('ASSEMBLYAI_API_KEY', '')
if not api_key:
    print("ASSEMBLYAI_API_KEY не найден")
    exit(1)

headers = {'authorization': api_key}

# Листинг последних транскриптов
resp = requests.get(
    'https://api.assemblyai.com/v2/transcript',
    headers=headers,
    params={'limit': 50},
)
data = resp.json()
transcripts = data.get('transcripts', [])
print(f"Всего транскриптов в ответе: {len(transcripts)}")

for t in transcripts:
    tid = t.get('id')
    status = t.get('status')
    created = t.get('created')
    duration = t.get('audio_duration')
    audio_url = t.get('audio_url', '')
    mins = int(duration or 0) // 60 if duration else 0

    # Фильтруем длинные (>20 мин) записи
    if (duration or 0) > 1200:
        print(f"\nid={tid} status={status} created={created} dur={mins}мин")
        print(f"  audio_url: {audio_url[:120]}")
