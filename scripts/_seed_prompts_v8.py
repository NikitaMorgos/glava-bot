# -*- coding: utf-8 -*-
"""Сидирует промпт cover_designer для v8."""
import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
import psycopg2, psycopg2.extras

DB_URL = os.environ.get("DATABASE_URL", "")
if not DB_URL:
    print("ERROR: DATABASE_URL not set"); sys.exit(1)

PROMPTS = {
    "cover_designer": """Ты Дизайнер обложки семейной книги.

На основе информации о герое и историческом периоде создай концепцию обложки — тёплую, личную, достойную.

Верни только валидный JSON без пояснений:
{
  "title": "Заголовок книги (имя героя или поэтичное название, максимум 5-6 слов)",
  "subtitle": "Подзаголовок (например: Семейная биография или История жизни)",
  "tagline": "Короткая фраза 6-10 слов — суть жизни героя (тёплая, не пафосная)",
  "image_description": "Описание образа для обложки в 2-3 предложения (что должно быть изображено, настроение, детали)",
  "visual_style": "warm" | "classic" | "vintage" | "modern",
  "color_palette": "Описание цветовой гаммы (2-3 цвета и их настроение)",
  "design_notes": "Заметки по оформлению: шрифты, расположение элементов (1-2 предложения)"
}

Правила:
- Заголовок — всегда имя героя (если неизвестно — поэтичное название эпохи)
- Tagline должна быть на русском, живой и тёплой, не клише
- Описание образа должно быть конкретным: реалистичные детали (руки, пейзаж, предмет эпохи)
- Стиль соответствует эпохе: vintage для советского времени, warm для современного
- Всегда возвращай валидный JSON"""
}

conn = psycopg2.connect(DB_URL, cursor_factory=psycopg2.extras.RealDictCursor)
try:
    cur = conn.cursor()
    for role, text in PROMPTS.items():
        cur.execute(
            "SELECT version FROM prompts WHERE role = %s AND is_active = TRUE ORDER BY version DESC LIMIT 1",
            (role,)
        )
        existing = cur.fetchone()
        if existing:
            print(f"  {role}: уже есть (v{existing['version']}), пропускаем")
            continue
        cur.execute(
            "INSERT INTO prompts (role, version, prompt_text, is_active, updated_by) VALUES (%s, 1, %s, TRUE, 'seed_v8')",
            (role, text)
        )
        print(f"  {role}: добавлен v1")
    conn.commit()
    print("OK")
except Exception as e:
    conn.rollback(); print(f"ERROR: {e}"); raise
finally:
    conn.close()
