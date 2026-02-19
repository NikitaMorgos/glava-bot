"""
Применяет миграцию v3 (state machine).
Запуск: python run_v3_migration.py
"""
import config
import psycopg2
from pathlib import Path

sql_path = Path(__file__).parent / "sql" / "init_v3_state_machine.sql"
sql = sql_path.read_text(encoding="utf-8")

# Убираем только строки-комментарии, разбиваем по ;
lines = [l for l in sql.split("\n") if not l.strip().startswith("--")]
sql_clean = "\n".join(lines)
statements = [s.strip() for s in sql_clean.split(";") if s.strip()]

conn = psycopg2.connect(config.DATABASE_URL)
conn.autocommit = True
cur = conn.cursor()
for i, stmt in enumerate(statements):
    try:
        cur.execute(stmt)
        preview = stmt[:70].replace("\n", " ")
        print(f"OK {i+1}: {preview}...")
    except Exception as e:
        print(f"ОШИБКА {i+1}: {e}")
        print(f"  SQL: {stmt[:100]}...")
cur.close()
conn.close()
print("Миграция v3 завершена.")
