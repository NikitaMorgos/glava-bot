"""Сбрасывает всю историю пользователя для повторного теста.
Запуск: python scripts/_reset_dasha.py <telegram_id>
"""
import os, sys
import psycopg2

TELEGRAM_ID = int(sys.argv[1]) if len(sys.argv) > 1 else 577528

conn = psycopg2.connect(os.environ["DATABASE_URL"])
cur = conn.cursor()

# Находим user_id
cur.execute("SELECT id FROM users WHERE telegram_id = %s", (TELEGRAM_ID,))
row = cur.fetchone()
if not row:
    print(f"Пользователь telegram_id={TELEGRAM_ID} не найден"); conn.close(); sys.exit(1)
user_id = row[0]
print(f"user_id={user_id}, telegram_id={TELEGRAM_ID}")

# Удаляем все черновики (кроме одного — сбрасываем до начального состояния)
# Сначала удаляем "лишние" черновики (кроме самого свежего)
cur.execute("""
    DELETE FROM draft_orders
    WHERE user_id = %s
    AND id NOT IN (SELECT id FROM draft_orders WHERE user_id = %s ORDER BY id DESC LIMIT 1)
    RETURNING id
""", (user_id, user_id))
deleted = cur.rowcount
print(f"Удалено старых черновиков: {deleted}")

# Сбрасываем последний черновик
cur.execute("""
    UPDATE draft_orders SET
        status             = 'draft',
        bot_state          = 'no_project',
        email              = NULL,
        characters         = '{}',
        character_relation = NULL,
        narrators          = '[]',
        revision_count     = 0,
        pending_revision   = NULL,
        revision_deadline  = NULL,
        payment_id         = NULL,
        payment_url        = NULL,
        updated_at         = NOW()
    WHERE user_id = %s
    RETURNING id
""", (user_id,))
row = cur.fetchone()
print(f"Черновик сброшен: id={row[0]}" if row else "Нет черновика для сброса")

# Удаляем голосовые, фото, версии книги, джобы
cur.execute("DELETE FROM voice_messages WHERE user_id = %s", (TELEGRAM_ID,))
v = cur.rowcount
cur.execute("DELETE FROM photos WHERE user_id = %s", (TELEGRAM_ID,))
p = cur.rowcount
cur.execute("DELETE FROM book_versions WHERE telegram_id = %s", (TELEGRAM_ID,))
b = cur.rowcount
cur.execute("DELETE FROM pipeline_jobs WHERE telegram_id = %s", (TELEGRAM_ID,))
j = cur.rowcount
print(f"Удалено: голосовых={v}, фото={p}, версий книги={b}, pipeline_jobs={j}")

conn.commit()
conn.close()
print("\nГотово! Пользователь может нажать /start и пройти флоу заново.")
