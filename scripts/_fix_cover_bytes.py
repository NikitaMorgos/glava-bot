"""Фикс: cover_portrait должен быть строкой-путём, не bytes."""
from pathlib import Path

SCRIPT = Path("/opt/glava/scripts/test_stage4_karakulina.py")
src = SCRIPT.read_text(encoding="utf-8")

# В блоке _skip_val cover_portrait выставляется в bytes — надо str(path)
old_line = "            cover_portrait = cover_portrait_bytes if portrait_bytes else None"
new_line = "            cover_portrait = str(cover_portrait_path) if cover_portrait_path else None"

if old_line in src:
    src = src.replace(old_line, new_line)
    print("✅ Фикс применён: cover_portrait = str(path)")
else:
    print("❌ Строка не найдена — ищем вариант...")
    # Попробуем другой вариант
    import re
    # Найдём строки с cover_portrait = cover_portrait_bytes в контексте _skip_val
    matches = [(m.start(), m.group()) for m in re.finditer(r'cover_portrait = cover_portrait_bytes[^\n]*', src)]
    for pos, match in matches:
        ctx = src[max(0,pos-200):pos+100]
        print(f"  Найдено: {match!r}")
        print(f"  Контекст: ...{ctx[-100:]}...")

SCRIPT.write_text(src, encoding="utf-8")
print("[OK] Скрипт сохранён")
