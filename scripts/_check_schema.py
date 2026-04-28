import psycopg2, os

conn = psycopg2.connect(os.environ["DATABASE_URL"])
cur = conn.cursor()

# Проверяем колонки таблицы users
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='users' ORDER BY ordinal_position")
print("users cols:", [r[0] for r in cur.fetchall()])

cur.execute("""
    SELECT d.id, u.username, u.telegram_id, d.status, d.bot_state, d.updated_at
    FROM draft_orders d
    JOIN users u ON u.id = d.user_id
    ORDER BY d.updated_at DESC LIMIT 10
""")
print("\nПоследние 10 черновиков:")
for row in cur.fetchall():
    print(row)
conn.close()
