"""Добавляет --skip-cover-validation флаг и обходит Call2 при use-existing-cover."""
from pathlib import Path

SCRIPT = Path("/opt/glava/scripts/test_stage4_karakulina.py")
src = SCRIPT.read_text(encoding="utf-8")

# 1. Добавить аргумент
old_arg = '    parser.add_argument("--use-existing-cover", default=None,'
new_arg = '''    parser.add_argument("--skip-cover-validation", action="store_true",
                        help="Пропустить Cover Designer Call2 (валидацию портрета)")
    parser.add_argument("--use-existing-cover", default=None,'''
src = src.replace(old_arg, new_arg)

# 2. В секции Call2 — пропускать если skip_cover_validation или use_existing_cover
old_call2 = '        # --- Вызов 2: валидация портрета ---\n        if portrait_bytes:'
new_call2 = '''        # --- Вызов 2: валидация портрета ---
        # Пропускаем если явно указан флаг или если использован готовый портрет
        _skip_val = getattr(args, "skip_cover_validation", False) or bool(getattr(args, "use_existing_cover", None))
        if portrait_bytes and not _skip_val:'''

# Ещё нужно добавить ветку "если пропустили validation — использовать Call1 composition"
src = src.replace(old_call2, new_call2)

# Найдём место после блока Call2 где cover_composition выставляется, чтобы добавить else
old_else_block = "        if portrait_bytes and not _skip_val:"
# Находим блок после call2 — после всего блока if portrait_bytes
# Нужно добавить else: final_cover_composition = cd1_raw.get("cover_composition")
# Ищем строку после закрытия if portrait_bytes

# Вставим после всего if-блока с валидацией
old_after_call2 = '''        print_cover_designer_results(1, cd1_raw, portrait_bytes)

        # --- Вызов 2: валидация портрета ---
        # Пропускаем если явно указан флаг или если использован готовый портрет
        _skip_val = getattr(args, "skip_cover_validation", False) or bool(getattr(args, "use_existing_cover", None))
        if portrait_bytes and not _skip_val:'''

new_after_call2 = '''        print_cover_designer_results(1, cd1_raw, portrait_bytes)

        # --- Вызов 2: валидация портрета ---
        # Пропускаем если явно указан флаг или если использован готовый портрет
        _skip_val = getattr(args, "skip_cover_validation", False) or bool(getattr(args, "use_existing_cover", None))
        if _skip_val:
            print("[COVER_DESIGNER] Вызов 2 пропущен (--skip-cover-validation / --use-existing-cover)")
            final_cover_composition = cd1_raw.get("cover_composition", {})
            cover_composition = final_cover_composition
            cover_portrait = cover_portrait_bytes if portrait_bytes else None
        elif portrait_bytes:'''

src = src.replace(old_after_call2, new_after_call2)

# 3. Теперь нужно убрать/фиксировать отступ остальных ветвей в if portrait_bytes
# После блока if portrait_bytes было: else: (нет портрета) - покрывается.
# Важно что cover_portrait и cover_composition после всего блока выставились правильно.
# Проверим что cover_composition выставляется в нужных местах

print("Результат патча:")
print("  skip-cover-validation в argparse:", '--skip-cover-validation' in src)
print("  _skip_val блок:", '_skip_val' in src)
print("  elif portrait_bytes:", 'elif portrait_bytes:' in src)

SCRIPT.write_text(src, encoding="utf-8")
print("\n[OK] Скрипт обновлён")
