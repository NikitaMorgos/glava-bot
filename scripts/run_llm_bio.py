"""Генерация bio_story.txt из transcript.txt через LLM."""
import os
import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root))

# Сразу читаем .env ДО импорта config
# Пробуем оба пути: cwd (bat делает cd в GLAVA) и корень по __file__
_env_candidates = [Path.cwd() / ".env", _root / ".env"]
_env_abs = None
for p in _env_candidates:
    if p.resolve().exists():
        _env_abs = p.resolve()
        break
if _env_abs is None:
    _env_abs = _root / ".env"
_api_key = ""
if not _env_abs.exists() or not _env_abs.is_file():
    print("Файл .env не найден:", _env_abs)
else:
    try:
        raw = _env_abs.read_bytes()
        # Пробуем кодировки
        for enc in ("utf-8-sig", "utf-8", "cp1251"):
            try:
                text = raw.decode(enc)
                for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
                    s = line.strip()
                    if not s or s[0] == "#":
                        continue
                    idx = s.find("OPENAI_API_KEY=")
                    if idx == 0:
                        _api_key = s[16:].strip().strip("'\"")  # после "OPENAI_API_KEY="
                    elif "=" in s and s.split("=", 1)[0].strip() == "OPENAI_API_KEY":
                        _api_key = s.split("=", 1)[1].strip().strip("'\"")
                    else:
                        continue
                    if len(_api_key) > 20:
                        os.environ["OPENAI_API_KEY"] = _api_key
                        break
                if _api_key:
                    break
            except (UnicodeDecodeError, UnicodeError):
                continue
    except Exception as e:
        print("Ошибка чтения .env:", type(e).__name__, e)

if not _api_key:
    _api_key = os.environ.get("OPENAI_API_KEY", "")
if not _api_key:
    print("OPENAI_API_KEY не найден. Путь:", _env_abs)

from llm_bio import process_transcript_to_bio

client_dir = Path(__file__).resolve().parent.parent / "exports" / "client_605154_ddmika"
transcript_path = client_dir / "transcript.txt"
bio_path = client_dir / "bio_story.txt"

if not transcript_path.exists():
    print("transcript.txt не найден")
    sys.exit(1)

txt = transcript_path.read_text(encoding="utf-8")
# Берём последний блок (новый голос voice_id=6)
if "--- Голосовое (voice_id=6)" in txt:
    block = txt.split("--- Голосовое (voice_id=6)")[-1]
    if "---" in block:
        block = block.split("---")[0]
    block = block.strip()
else:
    block = txt[-15000:]  # последние 15k символов

bio = process_transcript_to_bio(block, api_key=_api_key)
if bio:
    bio_path.write_text(bio, encoding="utf-8")
    print("bio_story.txt создан:", bio_path)
else:
    print("LLM вернул пусто")
