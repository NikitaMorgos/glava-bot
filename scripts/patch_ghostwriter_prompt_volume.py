# -*- coding: utf-8 -*-
"""
Добавляет в промпт ghostwriter требования по минимальному объёму глав и полноте фактов.

Запуск (с сервера или локально при доступе к БД):
  cd /opt/glava && set -a && source .env && set +a && .venv/bin/python scripts/patch_ghostwriter_prompt_volume.py

Повторный запуск безопасен: если блок «ОБЪЁМ И ПОЛНОТА» уже есть — скрипт выходит без изменений.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

ADDENDUM = """

ОБЪЁМ И ПОЛНОТА (обязательно):
- Если во входных transcripts и fact_map достаточно материала, суммарный объём текста во всех главах — не менее 6000–9000 символов (примерно 900–1300 слов). Не останавливайся на кратком пересказе.
- Каждая из 4 глав — не менее 1200–2200 символов (примерно 200–350 слов), пока хватает фактов в источниках; не сокращай искусственно.
- Опирайся на ВСЕ существенные факты из fact_map и transcripts: даты, места, имена родственников, война и фронт, награды, переезды (в т.ч. зарубежные годы), работа, быт, характер, отношения с семьёй, досуг, политические/мировоззренческие детали, если они есть в источнике.
- Не своди развёрнутые эпизоды из транскрипта к одной общей фразе — переноси конкретику в повествование.
- historical_context используй для атмосферы и привязки к эпохе, но не вместо фактов из интервью.
"""


def main() -> None:
    from admin import db_admin as dba

    row = dba.get_prompt("ghostwriter")
    if not row or not (row.get("prompt_text") or "").strip():
        print("Ошибка: промпт ghostwriter не найден в БД.")
        sys.exit(1)

    text = row["prompt_text"].strip()
    if "ОБЪЁМ И ПОЛНОТА" in text:
        print("Промпт ghostwriter уже содержит блок объёма — пропуск.")
        return

    new_text = text + ADDENDUM
    dba.save_prompt("ghostwriter", new_text, author="patch_ghostwriter_prompt_volume")
    print("OK: сохранена новая версия промпта ghostwriter с требованиями по объёму.")


if __name__ == "__main__":
    main()
