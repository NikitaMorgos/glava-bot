#!/usr/bin/env python3
"""Загружает ogg-файл записи встречи в S3, возвращает URL и запускает транскрипцию AssemblyAI."""
import sys
import os

sys.path.insert(0, "/opt/glava")
from dotenv import load_dotenv
load_dotenv("/opt/glava/.env")

import storage
from assemblyai_client import transcribe_via_assemblyai

ogg_path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/meeting_l8abv5oc.ogg"

print(f"Uploading: {ogg_path}")
key = storage.upload_file(ogg_path, user_id=1)
url = storage.get_presigned_download_url(key)
print(f"S3_KEY: {key}")
print(f"DOWNLOAD_URL: {url}")

api_key = os.getenv("ASSEMBLYAI_API_KEY", "")
if not api_key:
    print("ERROR: ASSEMBLYAI_API_KEY not set")
    sys.exit(1)

print("Starting transcription via AssemblyAI...")
transcript = transcribe_via_assemblyai(audio_path=ogg_path, api_key=api_key, language_code="ru", speaker_labels=True)
if transcript:
    print("\n=== TRANSCRIPTION ===")
    print(transcript)
    out = ogg_path.replace(".ogg", "_transcript.txt")
    with open(out, "w", encoding="utf-8") as f:
        f.write(transcript)
    print(f"\nSaved to: {out}")
else:
    print("ERROR: empty transcript")
