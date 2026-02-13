"""
Скрипт для сброса webhook и подготовки бота к запуску.
Запусти ЭТОТ файл перед main.py, если возникает ошибка Conflict.

Запуск: .\venv\Scripts\python.exe fix_webhook.py
"""

import asyncio
import sys
from dotenv import load_dotenv
load_dotenv()

import os
token = os.getenv("BOT_TOKEN")
if not token:
    print("Ошибка: BOT_TOKEN не найден в .env")
    sys.exit(1)

async def fix():
    from telegram import Bot
    bot = Bot(token=token)
    await bot.delete_webhook(drop_pending_updates=True)
    print("Webhook удалён, pending updates сброшены.")
    print("Подожди 10 секунд, затем запусти: .\\venv\\Scripts\\python.exe main.py")

if __name__ == "__main__":
    asyncio.run(fix())
