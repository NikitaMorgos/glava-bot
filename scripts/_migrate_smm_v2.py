"""Run SMM v2 migration: create new tables."""
from smm.db_smm import ensure_tables
ensure_tables()
print("OK: SMM v2 tables created/migrated")
