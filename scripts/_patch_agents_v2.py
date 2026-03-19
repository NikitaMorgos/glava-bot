"""Вставляет строки о bot_v2 в AGENTS.md."""
import pathlib

path = pathlib.Path("AGENTS.md")
content = path.read_text(encoding="utf-8")

marker = "scripts/migrate_admin.py"
insert_after = content.find(marker)
if insert_after < 0:
    print("marker not found"); exit(1)

end_of_line = content.find("\n", insert_after) + 1

new_lines = (
    "| **БД миграция bot v2** | `scripts/migrate_bot_v2.py` — поля `narrators`, `bot_state`, `revision_count`, `pending_revision`, `photo_type` |\n"
    "| **Сид сообщений бота** | `scripts/seed_bot_messages_v2.py` — 34 сообщения всех экранов v2 → `prompts` (ключи `bot_*`) |\n"
)

content = content[:end_of_line] + new_lines + content[end_of_line:]
path.write_text(content, encoding="utf-8")
print("OK")
