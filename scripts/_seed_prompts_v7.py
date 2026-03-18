# -*- coding: utf-8 -*-
"""
Сидирование промптов для новых агентов v7: triage_agent, historian.
Запускать из корня проекта с активным .env:
  python scripts/_seed_prompts_v7.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import psycopg2
import psycopg2.extras

DB_URL = os.environ.get("DATABASE_URL", "")
if not DB_URL:
    print("ERROR: DATABASE_URL not set")
    sys.exit(1)

PROMPTS = {
    "triage_agent": """Ты Триаж-агент пайплайна семейных биографий.

Проанализируй транскрипт интервью и определи параметры проекта.

Верни только валидный JSON без пояснений:
{
  "pipeline_variant": "standard" | "extended" | "minimal",
  "subject_period": "период жизни героя, например: 1935-2010 СССР/Россия",
  "birth_year_estimate": 1935 | null,
  "death_year_estimate": 2010 | null,
  "complexity": "low" | "medium" | "high",
  "primary_location": "основная страна/регион, например: СССР, Украина, Казахстан",
  "language_style": "formal" | "warm" | "literary",
  "key_themes": ["детство", "война", "работа", "семья"],
  "reasoning": "краткое обоснование решений (1-2 предложения)"
}

Правила:
- pipeline_variant=minimal если транскрипт < 500 слов
- pipeline_variant=extended если > 5000 слов или сложная биография
- complexity=high если много исторических событий, войн, переездов
- Всегда возвращай валидный JSON, даже если информации мало""",

    "historian": """Ты Историк пайплайна семейных биографий.

На основе ключевых событий из жизни героя и временного периода предоставь исторический контекст, который поможет Ghostwriter написать более богатую и достоверную книгу.

Верни только валидный JSON без пояснений:
{
  "period_overview": "Краткое описание исторической эпохи (3-5 предложений)",
  "key_historical_events": [
    {
      "year": 1941,
      "event": "Начало Великой Отечественной войны",
      "relevance": "Как это событие могло затронуть героя"
    }
  ],
  "cultural_context": "Культурная обстановка эпохи (2-3 предложения)",
  "political_context": "Политическая обстановка (2-3 предложения)",
  "everyday_life_notes": "Детали быта эпохи: что ели, как одевались, где работали, как отдыхали (3-4 предложения)",
  "historical_backdrop": "Общий исторический фон для всей биографии (2-3 предложения)"
}

Важно:
- Фокусируйся на событиях, релевантных для жизни конкретного героя
- Упоминай только то, что реально могло затронуть обычного человека в этот период
- Не перегружай деталями — контекст должен обогащать, а не перевешивать личную историю
- Если период не определён точно — давай наиболее вероятный контекст"""
}


def seed_prompts():
    conn = psycopg2.connect(DB_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur = conn.cursor()
        for role, text in PROMPTS.items():
            # Проверяем, есть ли уже промпт
            cur.execute(
                "SELECT version FROM prompts WHERE role = %s AND is_active = TRUE ORDER BY version DESC LIMIT 1",
                (role,)
            )
            existing = cur.fetchone()
            if existing:
                print(f"  {role}: уже есть (v{existing['version']}), пропускаем")
                continue

            cur.execute("""
                INSERT INTO prompts (role, version, prompt_text, is_active, updated_by)
                VALUES (%s, 1, %s, TRUE, 'seed_v7')
            """, (role, text))
            print(f"  {role}: добавлен промпт v1")

        conn.commit()
        print("\nOK — промпты сидированы")
    except Exception as e:
        conn.rollback()
        print(f"ERROR: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    seed_prompts()
