#!/usr/bin/env python3
import os, sys, json
sys.path.insert(0, "/opt/glava")
from dotenv import load_dotenv
load_dotenv("/opt/glava/.env")
import httpx

key = os.getenv("ASSEMBLYAI_API_KEY", "")
tid = "dec7960b-c4d0-4bad-912e-013a6029b799"
r = httpx.get(f"https://api.assemblyai.com/v2/transcript/{tid}",
              headers={"authorization": key}, timeout=30)
d = r.json()
print("STATUS:", d.get("status"))
dur = d.get("audio_duration") or 0
print(f"DURATION: {dur:.0f} сек ({dur/60:.1f} мин)")

utterances = d.get("utterances") or []
if utterances:
    out = []
    for u in utterances:
        out.append(f"Спикер {u['speaker']}: {u['text']}")
    transcript = "\n".join(out)
else:
    transcript = d.get("text") or ""

print("\n=== ТРАНСКРИПТ ===")
print(transcript[:5000])

out_path = "/tmp/karakulina_meeting_transcript.txt"
with open(out_path, "w", encoding="utf-8") as f:
    f.write(transcript)
print(f"\nСохранён: {out_path}")
