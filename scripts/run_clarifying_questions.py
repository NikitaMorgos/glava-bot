"""Генерация уточняющих вопросов по готовому bio-документу (ChatGPT).

Читает bio_from_assembly.txt (или bio_story.txt), вызывает промпт уточняющих вопросов,
сохраняет результат в clarifying_questions.txt в той же папке.

Запуск на сервере (где доступен OpenAI API):
  cd /opt/glava
  source .venv/bin/activate
  python3 scripts/run_clarifying_questions.py
"""
import os
import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root))

# Загрузка .env
for p in [Path.cwd() / ".env", _root / ".env"]:
    if p.exists():
        try:
            raw = p.read_bytes()
            for enc in ("utf-8-sig", "utf-8", "cp1251"):
                try:
                    text = raw.decode(enc)
                    for line in text.replace("\r\n", "\n").split("\n"):
                        s = line.strip()
                        if not s or s.startswith("#"):
                            continue
                        if "OPENAI_API_KEY=" in s and s.index("OPENAI_API_KEY=") == 0:
                            val = s.split("=", 1)[1].strip().strip("'\"")
                            if len(val) > 20:
                                os.environ["OPENAI_API_KEY"] = val
                                break
                    break
                except Exception:
                    continue
        except Exception:
            pass
        break

api_key = os.environ.get("OPENAI_API_KEY", "")
if not api_key:
    print("OPENAI_API_KEY не задан. Добавьте в .env")
    sys.exit(1)

# Папка клиента: та же, что для run_assembly_to_bio
client_dir = _root / "exports" / "client_605154_unknown"
bio_path = client_dir / "bio_from_assembly.txt"
out_path = client_dir / "clarifying_questions.txt"

# Можно указать другой файл bio: python3 scripts/run_clarifying_questions.py путь/к/bio.txt
if len(sys.argv) > 1:
    bio_path = Path(sys.argv[1]).resolve()
    out_path = bio_path.parent / "clarifying_questions.txt"

if not bio_path.exists():
    print("Не найден файл биографии:", bio_path)
    sys.exit(1)

bio_text = bio_path.read_text(encoding="utf-8")
if not bio_text.strip():
    print("Файл биографии пуст:", bio_path)
    sys.exit(1)

print("OpenAI: генерация уточняющих вопросов по bio (1–2 мин)...")
from llm_bio import generate_clarifying_questions

questions_text = generate_clarifying_questions(bio_text, api_key=api_key)
if not questions_text:
    print("Ошибка: LLM вернул пусто")
    sys.exit(1)

out_path.write_text(questions_text, encoding="utf-8")
print("Готово. Результат:", out_path)
print("\n--- Уточняющие вопросы ---\n")
print(questions_text[:3000] if len(questions_text) > 3000 else questions_text)
if len(questions_text) > 3000:
    print("\n... (всего {} символов, см. файл)".format(len(questions_text)))
