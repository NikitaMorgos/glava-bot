"""
Сид сообщений бота в таблицу prompts (role = bot_<key>).

Запуск: python scripts/seed_bot_messages.py

Вставляет дефолтные тексты из prepay.messages, если записей ещё нет.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

import psycopg2
from prepay import messages as prepay_messages

DB_URL = os.environ.get("DATABASE_URL", "")
if not DB_URL:
    print("ERROR: DATABASE_URL не задан")
    sys.exit(1)

# Ключ → атрибут в prepay.messages
BOT_MESSAGE_MAP = {
    "intro_main": "INTRO_MAIN_MSG",
    "intro_example": "INTRO_EXAMPLE_MSG",
    "intro_price": "INTRO_PRICE_MSG",
    "config_characters": "CONFIG_CHARACTERS_MSG",
    "config_characters_list": "CONFIG_CHARACTERS_LIST_MSG",
    "email_input": "EMAIL_INPUT_MSG",
    "email_error": "EMAIL_ERROR_MSG",
    "order_summary": "ORDER_SUMMARY_MSG",
    "payment_init": "PAYMENT_INIT_MSG",
    "payment_wait": "PAYMENT_WAIT_MSG",
    "payment_still_pending": "PAYMENT_STILL_PENDING_MSG",
    "resume_draft": "RESUME_DRAFT_MSG",
    "resume_payment": "RESUME_PAYMENT_MSG",
    "blocked_media": "BLOCKED_MEDIA_MSG",
    "online_meeting_intro": "ONLINE_MEETING_INTRO_MSG",
    "online_meeting_link_sent": "ONLINE_MEETING_LINK_SENT_MSG",
    "online_meeting_telemost_sent": "ONLINE_MEETING_TELEMOST_SENT_MSG",
    "online_meeting_bad_link": "ONLINE_MEETING_BAD_LINK_MSG",
    "online_meeting_error": "ONLINE_MEETING_ERROR_MSG",
}


def main():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    inserted = 0
    for key, attr in BOT_MESSAGE_MAP.items():
        role = f"bot_{key}"
        text = getattr(prepay_messages, attr, "")
        if not text:
            print(f"  Skip {key}: no attr {attr}")
            continue
        cur.execute("SELECT 1 FROM prompts WHERE role = %s", (role,))
        if cur.fetchone():
            continue
        cur.execute("""
            INSERT INTO prompts (role, version, prompt_text, is_active, updated_at, updated_by)
            VALUES (%s, 1, %s, TRUE, NOW(), 'seed_bot_messages')
        """, (role, text))
        inserted += 1
        print(f"  + {role}")
    conn.commit()
    cur.close()
    conn.close()
    print(f"Готово. Добавлено: {inserted}")


if __name__ == "__main__":
    main()
