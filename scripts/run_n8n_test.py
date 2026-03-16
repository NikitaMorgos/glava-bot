#!/usr/bin/env python3
"""
Тестовый прогон Phase A через n8n webhook.

Запуск на сервере:
    cd /opt/glava && source venv/bin/activate
    python scripts/run_n8n_test.py [TELEGRAM_ID]

Если TELEGRAM_ID не указан — берётся из .env (TEST_TELEGRAM_ID) или запрашивается.
Сообщения придут в Telegram на указанный chat_id.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from pipeline_n8n import trigger_phase_a

# Короткий тестовый транскрипт — достаточно для прогона всех агентов
TEST_TRANSCRIPT = """
Рассказчик: Мой дедушка Иван Петрович родился в 1936 году в деревне под Москвой. 
Он работал инженером на заводе, женился на бабушке Марии в 1960 году. 
У них родилось трое детей — мой папа, дядя Сергей и тётя Ольга. 
Дедушка любил рыбалку и играл на гармошке. Умер в 2012 году, мы его очень любим.
"""


def main():
    webhook = os.environ.get("N8N_WEBHOOK_PHASE_A", "").strip()
    if not webhook:
        print("Ошибка: N8N_WEBHOOK_PHASE_A не задан в .env")
        sys.exit(1)

    bot_token = os.environ.get("BOT_TOKEN", "")
    if not bot_token:
        print("Ошибка: BOT_TOKEN не задан в .env")
        sys.exit(1)

    telegram_id = None
    if len(sys.argv) > 1:
        try:
            telegram_id = int(sys.argv[1])
        except ValueError:
            print("Использование: python scripts/run_n8n_test.py [TELEGRAM_ID]")
            sys.exit(1)
    else:
        telegram_id = os.environ.get("TEST_TELEGRAM_ID")
        if telegram_id:
            telegram_id = int(telegram_id)
        else:
            print("Укажи свой Telegram ID (число) — туда придут сообщения:")
            print("  python scripts/run_n8n_test.py 123456789")
            print("Или добавь TEST_TELEGRAM_ID в .env")
            sys.exit(1)

    print(f"Webhook: {webhook}")
    print(f"Telegram ID: {telegram_id}")
    print(f"Транскрипт: {len(TEST_TRANSCRIPT.strip())} символов")
    print("-" * 50)
    print("Запуск Phase A...")

    ok = trigger_phase_a(
        telegram_id=telegram_id,
        transcript=TEST_TRANSCRIPT.strip(),
        character_name="Иван Петрович",
        draft_id=0,
        username="test",
    )

    if ok:
        print("OK — пайплайн запущен. Сообщения придут в Telegram через 1–3 минуты.")
        print("Проверь Executions в n8n, если что-то пошло не так.")
    else:
        print("Ошибка — webhook не принял запрос. Проверь логи и n8n.")
        sys.exit(1)


if __name__ == "__main__":
    main()
