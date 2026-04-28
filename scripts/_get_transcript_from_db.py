#!/usr/bin/env python3
"""Получает полный транскрипт пользователя из БД и сохраняет в файл."""
import sys, os
sys.path.insert(0, '/opt/glava')
from dotenv import load_dotenv
load_dotenv('/opt/glava/.env')
import psycopg2

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

# Покажем всех пользователей с транскриптами
cur.execute("""
    SELECT u.telegram_id, u.username, COUNT(vm.id) as cnt,
           SUM(LENGTH(vm.transcript)) as total_len
    FROM voice_messages vm
    JOIN users u ON u.id = vm.user_id
    WHERE vm.transcript IS NOT NULL AND LENGTH(vm.transcript) > 50
    GROUP BY u.telegram_id, u.username
    ORDER BY total_len DESC NULLS LAST
    LIMIT 10
""")
rows = cur.fetchall()
print("Пользователи с транскриптами:")
for r in rows:
    print(f"  tg={r[0]}  @{r[1]}  vm_count={r[2]}  total_len={r[3]}")

# Берём самого богатого на транскрипты
if not rows:
    print("Нет транскриптов в БД")
    sys.exit(1)

tg_id = rows[0][0]
print(f"\nВыбран: tg_id={tg_id}")

cur.execute("""
    SELECT vm.id, vm.created_at, LENGTH(vm.transcript), LEFT(vm.transcript, 80)
    FROM voice_messages vm
    JOIN users u ON u.id = vm.user_id
    WHERE u.telegram_id = %s AND vm.transcript IS NOT NULL AND LENGTH(vm.transcript) > 50
    ORDER BY vm.created_at
""", (tg_id,))
vms = cur.fetchall()
print(f"\nГолосовые ({len(vms)} шт.):")
for vm in vms:
    print(f"  id={vm[0]}  {vm[1]}  len={vm[2]}  preview: {repr(vm[3][:60])}")

# Собираем полный транскрипт
cur.execute("""
    SELECT vm.id, vm.created_at, vm.transcript
    FROM voice_messages vm
    JOIN users u ON u.id = vm.user_id
    WHERE u.telegram_id = %s AND vm.transcript IS NOT NULL AND LENGTH(vm.transcript) > 50
    ORDER BY vm.created_at
""", (tg_id,))
parts = []
for vm in cur.fetchall():
    parts.append(f"--- Голосовое (voice_id={vm[0]}) {vm[1]} ---\n{vm[2]}")

full_transcript = "\n\n".join(parts)
print(f"\nИтого: {len(full_transcript)} символов")

out = '/opt/glava/transcript_karakulina_db.txt'
with open(out, 'w', encoding='utf-8') as f:
    f.write(full_transcript)
print(f"Сохранён: {out}")

conn.close()
