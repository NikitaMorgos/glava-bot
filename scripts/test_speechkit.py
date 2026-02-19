#!/usr/bin/env python3
"""Тест SpeechKit — выводит точную ошибку."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import db
from transcribe import transcribe_via_speechkit

def main():
    _, voices, _ = db.get_user_all_data(605154)
    if not voices:
        print("No voices for user 605154")
        return
    v = voices[0]
    sk = v["storage_key"]
    ap = Path("exports/client_605154_ddmika/voice/001.mp3")
    print(f"storage_key: {sk}")
    print(f"audio_path exists: {ap.exists()}")
    print("Calling SpeechKit...")
    try:
        text = transcribe_via_speechkit(sk, audio_path=str(ap) if ap.exists() else None)
        print(f"OK, len={len(text)}")
        print(text[:500] if text else "(empty)")
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
