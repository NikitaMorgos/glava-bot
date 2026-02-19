"""
Конфигурация бота.
Все настройки берутся из переменных окружения.
Файл .env загружается автоматически (если есть).
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Загружаем .env из папки проекта (надёжно при любом cwd)
load_dotenv(Path(__file__).resolve().parent / ".env")


def get_env(key: str, default: str = "") -> str:
    """Безопасно читает переменную окружения."""
    value = os.getenv(key, default)
    required = ("BOT_TOKEN", "DATABASE_URL", "S3_BUCKET_NAME", "S3_ACCESS_KEY", "S3_SECRET_KEY")
    if not value and key in required:
        raise ValueError(f"Не задана обязательная переменная: {key}. Проверь .env файл.")
    return value


# Токен бота (получить у @BotFather в Telegram)
BOT_TOKEN = get_env("BOT_TOKEN")

# Подключение к PostgreSQL
# Neon pooler не сохраняет DDL — используем прямое подключение
_raw_url = get_env("DATABASE_URL")
DATABASE_URL = _raw_url.replace("-pooler", "") if "pooler" in _raw_url else _raw_url

# S3-совместимое хранилище
S3_ENDPOINT_URL = get_env("S3_ENDPOINT_URL", "https://s3.amazonaws.com")
S3_ACCESS_KEY = get_env("S3_ACCESS_KEY")
S3_SECRET_KEY = get_env("S3_SECRET_KEY")
S3_BUCKET_NAME = get_env("S3_BUCKET_NAME")
S3_REGION = get_env("S3_REGION", "us-east-1")

# Сколько голосовых показывать в /list
LIST_LIMIT = int(os.getenv("LIST_LIMIT", "5"))

# Yandex SpeechKit (опционально, для транскрибации)
# API-ключ сервисного аккаунта: Консоль → Сервисные аккаунты → glava-bot → Создать API-ключ
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY", "")

# HuggingFace (опционально, для диаризации — pyannote speaker-diarization-3.0)
# Токен: https://hf.co/settings/tokens ; принять условия pyannote/segmentation-3.0 и speaker-diarization-3.0
HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN", "")

# Транскрибер: mymeet | plaud | speechkit (по умолчанию первый с валидным ключом)
TRANSCRIBER = os.getenv("TRANSCRIBER", "").strip().lower() or None

# mymeet.ai — транскрипция (research-interview), API: mymeet.ai/contact
MYMEET_API_KEY = os.getenv("MYMEET_API_KEY", "")

# Plaud AI — транскрипция с диаризацией
PLAUD_API_TOKEN = os.getenv("PLAUD_API_TOKEN", "")
PLAUD_OWNER_ID = os.getenv("PLAUD_OWNER_ID", "glava_default")

# OpenAI — обработка транскрипта в биографический текст
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Pre-pay: цена за 1 персонажа (в копейках). 990 руб = 99000
PRICE_PER_CHARACTER = int(os.getenv("PRICE_PER_CHARACTER", "99000"))
