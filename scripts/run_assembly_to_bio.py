"""Прогон транскрипта AssemblyAI через промпт обработки (формирование документа).

Внимание: вызов идёт в OpenAI API (ChatGPT). Из РФ доступ часто блокируется или
обрывается (WinError 10054). Запускайте скрипт на сервере за рубежом или с VPN.
Подробнее: docs/OPENAI_ACCESS.md
"""
import os
import sys
import time
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

# Краткая подсказка при запуске (не ошибка)
print("OpenAI: запрос пойдёт в api.openai.com. Ожидайте ответа 1–3 мин.")

from llm_bio import process_transcript_to_bio

# Транскрипт Assembly и выход
client_dir = _root / "exports" / "client_605154_unknown"
transcript_path = client_dir / "transcript_assemblyai_diarized.txt"
out_path = client_dir / "bio_from_assembly.txt"

if not transcript_path.exists():
    print("Не найден:", transcript_path)
    sys.exit(1)

# Сохраняем предыдущее bio для сравнения
if out_path.exists():
    old_path = client_dir / "bio_from_assembly_old.txt"
    old_path.write_text(out_path.read_text(encoding="utf-8"), encoding="utf-8")
    print("Предыдущее bio сохранено для сравнения:", old_path)

transcript_full = transcript_path.read_text(encoding="utf-8")
# Для длинных транскриптов можно взять часть (API иногда обрывает соединение)
use_len = int(os.environ.get("BIO_TRANSCRIPT_MAX_CHARS", "0")) or len(transcript_full)
if use_len < len(transcript_full):
    transcript = transcript_full[:use_len] + "\n\n[... транскрипт сокращён ...]"
else:
    transcript = transcript_full
print("Транскрипт: {} символов. Вызов ChatGPT (промпт формирования документа)...".format(len(transcript)))

bio = None
for attempt in range(2):
    bio = process_transcript_to_bio(transcript, api_key=api_key)
    if bio:
        break
    if attempt == 0:
        print("Повтор через 5 сек...")
        time.sleep(5)
if not bio:
    print("Ошибка: LLM вернул пусто")
    sys.exit(1)

out_path.write_text(bio, encoding="utf-8")
print("Результат сохранён:", out_path)

# Копируем новое bio в client_605154_ddmika для сравнения рядом со старым
ddmika_dir = _root / "exports" / "client_605154_ddmika"
if ddmika_dir.exists():
    ddmika_bio = ddmika_dir / "bio_from_assembly_new.txt"
    ddmika_bio.write_text(bio, encoding="utf-8")
    print("Копия для сравнения:", ddmika_bio)

print("\n--- Начало результата ---\n")
print(bio[:6000] if len(bio) > 6000 else bio)
if len(bio) > 6000:
    print("\n... (всего {} символов, см. файл)".format(len(bio)))
