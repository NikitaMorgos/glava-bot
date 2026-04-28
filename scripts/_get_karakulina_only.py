#!/usr/bin/env python3
"""Выгружает транскрипт ТОЛЬКО по Каракулиной (voice_id=5) из БД."""
import sys, os
sys.path.insert(0, '/opt/glava')
from dotenv import load_dotenv
load_dotenv('/opt/glava/.env')
import psycopg2

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

cur.execute("""
    SELECT id, created_at, LENGTH(transcript), LEFT(transcript, 100)
    FROM voice_messages
    WHERE user_id = (SELECT id FROM users WHERE telegram_id = 214712093)
    ORDER BY created_at
""")
rows = cur.fetchall()
print("Все голосовые пользователя:")
for r in rows:
    print(f"  id={r[0]}  {r[1]}  len={r[2]}  preview: {repr(r[3])}")

# Берём только voice_id=5 (Каракулина)
cur.execute("SELECT transcript FROM voice_messages WHERE id = 5")
row = cur.fetchone()
if not row or not row[0]:
    print("Транскрипт voice_id=5 не найден!")
    sys.exit(1)

transcript = row[0]
print(f"\nТранскрипт voice_id=5: {len(transcript)} символов")
print("Начало:", repr(transcript[:200]))

out = '/opt/glava/transcript_karakulina_only.txt'
with open(out, 'w', encoding='utf-8') as f:
    f.write(transcript)
print(f"\nСохранён: {out}")
conn.close()
