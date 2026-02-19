"""Проверка чтения .env — запусти и скинь вывод."""
import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
_env = _root / ".env"

print("Корень проекта:", _root)
print("Путь к .env:", _env)
print("Файл существует:", _env.exists())

if _env.exists():
    print("Размер файла:", _env.stat().st_size, "байт")
    raw = _env.read_bytes()
    print("Первые 50 байт (hex):", raw[:50].hex())
    for enc in ("utf-8-sig", "utf-8", "cp1251"):
        try:
            text = raw.decode(enc)
            lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
            print(f"Кодировка {enc}: {len(lines)} строк")
            for i, line in enumerate(lines):
                s = line.strip()
                if "OPENAI_API_KEY" in s and not s.startswith("#"):
                    val_len = len(s.split("=", 1)[1].strip()) if "=" in s else 0
                    print(f"  Строка {i+1}: OPENAI_API_KEY=... (длина значения: {val_len})")
            break
        except Exception as e:
            print(f"  {enc}: ошибка {e}")
