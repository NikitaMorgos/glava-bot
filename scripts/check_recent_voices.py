#!/usr/bin/env python3
"""Проверка недавних голосовых (вчера и позавчера): пришли ли, есть ли транскрипт."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import db

def main():
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT v.id, v.duration, v.created_at, v.transcript IS NOT NULL as has_transcript,
                       u.telegram_id, u.username
                FROM voice_messages v
                JOIN users u ON v.user_id = u.id
                WHERE v.created_at >= NOW() - INTERVAL '3 days'
                ORDER BY v.created_at DESC, v.duration DESC NULLS LAST
            """)
            rows = cur.fetchall()
            cols = ["id", "duration", "created_at", "has_transcript", "telegram_id", "username"]

    if not rows:
        print("За последние 3 дня голосовых не найдено.")
        return

    print("Голосовые за последние 3 дня (по убыванию даты, длинные сверху):\n")
    for r in rows:
        d = dict(zip(cols, r))
        dur = f"{d['duration']} сек" if d["duration"] else "?"
        ts = d["created_at"].strftime("%d.%m %H:%M") if d["created_at"] else "?"
        transcript = "✓" if d["has_transcript"] else "—"
        print(f"  {ts}  |  {dur:>8}  | transcript: {transcript}  |  user {d['telegram_id']} @{d['username'] or '-'}")

    # Крупные без транскрипта
    no_transcript = [r for r in rows if not r[3] and (r[1] or 0) > 60]
    if no_transcript:
        print("\n!! Krupnye (>60 sek) bez transkripta:")
        for r in no_transcript:
            d = dict(zip(cols, r))
            print(f"  id={d['id']}  {d['duration']} сек  user {d['telegram_id']}")


if __name__ == "__main__":
    main()
