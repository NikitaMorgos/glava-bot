"""
Патч для test_stage4_karakulina.py и pipeline_config.json.
Изменения:
  1. pipeline_config.json — новые версии промптов
  2. DEFAULT_FACT_MAP → test_fact_map_karakulina_v5.json
  3. Добавить --use-existing-cover аргумент
  4. validate_layout_output — поддержка нового JSON-формата (pages[])
  5. В main(): обработка --use-existing-cover, пропуск Replicate
  6. После Layout Designer: запуск build_karakulina_pdf.py
"""
import json
import re
from pathlib import Path

ROOT = Path("/opt/glava")
PROMPTS_CFG = ROOT / "prompts" / "pipeline_config.json"
SCRIPT = ROOT / "scripts" / "test_stage4_karakulina.py"

# ──────────────────────────────────────────────────────────
# 1. pipeline_config.json
# ──────────────────────────────────────────────────────────
cfg = json.loads(PROMPTS_CFG.read_text(encoding="utf-8"))

updates = {
    "cover_designer":       ("13_cover_designer_v3.md",        "Даша v7 — 9 правил без дублей, nano-banana-2"),
    "interview_architect":  ("11_interview_architect_v3.md",   "Даша v4 — без дублей, gaps может быть пустым"),
    "layout_designer":      ("08_layout_designer_v2.md",       "Даша v6 — JSON output, правила 10+11 (Linux шрифты)"),
}
from datetime import datetime
ts = datetime.now().strftime("%d.%m.%Y %H:%M")
for key, (pfile, note) in updates.items():
    if key not in cfg:
        cfg[key] = {}
    cfg[key]["prompt_file"] = pfile
    cfg[key]["_notes"] = note
    cfg[key]["_last_uploaded"] = ts
    cfg[key]["_uploaded_filename"] = pfile

PROMPTS_CFG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"[OK] pipeline_config.json обновлён: cover_designer→v3, interview_architect→v3, layout_designer→v2")

# ──────────────────────────────────────────────────────────
# 2–6. Патч test_stage4_karakulina.py
# ──────────────────────────────────────────────────────────
src = SCRIPT.read_text(encoding="utf-8")
orig = src

# 2. DEFAULT_FACT_MAP
src = src.replace(
    'DEFAULT_FACT_MAP = ROOT / "exports" / "karakulina_historian_extended_20260327_183739.json"',
    'DEFAULT_FACT_MAP = ROOT / "exports" / "test_fact_map_karakulina_v5.json"',
)

# 3. Добавить --use-existing-cover аргумент
old_arg = '    parser.add_argument("--skip-layout", action="store_true",\n                        help="Запустить только Арт-директора")'
new_arg = old_arg + """
    parser.add_argument("--use-existing-cover", default=None,
                        help="Путь к существующему портрету обложки (пропускает Replicate-генерацию)")"""
src = src.replace(old_arg, new_arg)

# 4. validate_layout_output — поддержка нового формата
old_validate = '''def validate_layout_output(response: dict) -> dict | None:
    """Проверяет наличие layout_code и page_map."""
    if not isinstance(response, dict):
        return None
    layout_code = response.get("layout_code", {})
    if not layout_code.get("code"):
        print("[VALIDATE-LAYOUT] ❌ layout_code.code отсутствует")
        return None
    page_map = response.get("page_map", [])
    if not page_map:
        print("[VALIDATE-LAYOUT] ⚠️  page_map пуст")
    style_guide = response.get("style_guide", {})
    total_pages = response.get("technical_notes", {}).get("total_pages", 0)
    print(f"[VALIDATE-LAYOUT] ✅ layout_code: {len(layout_code.get('code', ''))} симв. | "
          f"page_map: {len(page_map)} стр. | total_pages: {total_pages}")
    return response'''

new_validate = '''def validate_layout_output(response: dict) -> dict | None:
    """Проверяет структуру Layout Designer. Поддерживает оба формата:
       новый (pages[]) и старый (layout_code.code).
    """
    if not isinstance(response, dict):
        return None
    # Новый формат v2: pages[] + style_guide
    pages = response.get("pages", [])
    if pages:
        page_map = response.get("page_map", [])
        total_pages = response.get("technical_notes", {}).get("total_pages", 0)
        print(f"[VALIDATE-LAYOUT] ✅ pages: {len(pages)} | page_map: {len(page_map)} | total_pages: {total_pages}")
        return response
    # Старый формат: layout_code.code (fallback)
    layout_code = response.get("layout_code", {})
    if layout_code.get("code"):
        page_map = response.get("page_map", [])
        total_pages = response.get("technical_notes", {}).get("total_pages", 0)
        print(f"[VALIDATE-LAYOUT] ✅ layout_code (old fmt): {len(layout_code.get('code',''))} симв. | "
              f"page_map: {len(page_map)} | total_pages: {total_pages}")
        return response
    print("[VALIDATE-LAYOUT] ❌ Нет ни pages[], ни layout_code.code")
    return None'''

src = src.replace(old_validate, new_validate)

# 5. Обработка --use-existing-cover: вставить ДО секции "ШАГ 0: COVER DESIGNER"
old_cover_marker = '    cover_composition = None\n    cover_portrait = None\n\n    # ─── API клиент ───'
new_cover_marker = '''    cover_composition = None
    cover_portrait = None

    # ─── Предзагрузка существующего портрета обложки ───
    _preloaded_portrait_bytes: bytes | None = None
    _preloaded_portrait_path: Path | None = None
    if getattr(args, "use_existing_cover", None):
        _ppath = Path(args.use_existing_cover)
        if _ppath.exists():
            _preloaded_portrait_bytes = _ppath.read_bytes()
            _preloaded_portrait_path = _ppath
            print(f"[COVER] Используем существующий портрет: {_ppath.name} ({len(_preloaded_portrait_bytes)} байт)")
        else:
            print(f"[WARN] --use-existing-cover: файл не найден: {_ppath}")

    # ─── API клиент ───'''
src = src.replace(old_cover_marker, new_cover_marker)

# Пропускать Replicate если portrait уже загружен
old_replicate_start = '        if image_gen_prompt and os.environ.get("REPLICATE_API_TOKEN"):'
new_replicate_start = '''        # Если портрет передан через --use-existing-cover — пропускаем Replicate
        if _preloaded_portrait_bytes:
            portrait_bytes = _preloaded_portrait_bytes
            cover_portrait_path = _preloaded_portrait_path
            cover_portrait_bytes = _preloaded_portrait_bytes
            print(f"[COVER] Используем предзагруженный портрет, пропускаем Replicate")
        elif image_gen_prompt and os.environ.get("REPLICATE_API_TOKEN"):'''

src = src.replace(old_replicate_start, new_replicate_start)

# Нужно сдвинуть else-ветку на один уровень (добавить elif)
# Ищем конец Replicate-блока и добавляем else для нового условия
old_no_token = '''        else:
            if not image_gen_prompt:
                print("[REPLICATE] Пропуск: нет image_gen_prompt от Cover Designer")
            else:
                print("[REPLICATE] Пропуск: REPLICATE_API_TOKEN не задан")'''
new_no_token = '''        else:
            if not image_gen_prompt:
                print("[REPLICATE] Пропуск: нет image_gen_prompt от Cover Designer")
            else:
                print("[REPLICATE] Пропуск: REPLICATE_API_TOKEN не задан")
'''
# Только заменяем если нашли (может не быть точного совпадения)
if old_no_token in src:
    src = src.replace(old_no_token, new_no_token)

# 6. После save_code_file в layout-цикле — добавить вызов build_pdf
old_save_code = '''        code_path = save_code_file(layout_result, f"{args.prefix}_iter{qa_iteration}", ts)
        if code_path:
            print(f"[SAVED] layout_code: {code_path.name}")
            print(f"        Запуск: {layout_result.get('layout_code', {}).get('build_command', '?')}")'''

new_save_code = '''        code_path = save_code_file(layout_result, f"{args.prefix}_iter{qa_iteration}", ts)
        if code_path:
            print(f"[SAVED] layout_code: {code_path.name}")
            print(f"        Запуск: {layout_result.get('layout_code', {}).get('build_command', '?')}")

        # Если Layout Designer вернул JSON (новый формат) — собираем PDF через build_karakulina_pdf.py
        if layout_result.get("pages"):
            import subprocess as _sp
            build_script = ROOT / "scripts" / "build_karakulina_pdf.py"
            if build_script.exists():
                print(f"\\n[BUILD_PDF] Запускаем {build_script.name} (Layout Designer → JSON → PDF)...")
                _result = _sp.run(
                    ["/opt/glava/venv/bin/python3", str(build_script)],
                    cwd=str(ROOT), capture_output=True, text=True, timeout=120,
                )
                if _result.returncode == 0:
                    print(f"[BUILD_PDF] ✅ PDF собран успешно")
                    for line in _result.stdout.strip().splitlines()[-5:]:
                        print(f"  {line}")
                else:
                    print(f"[BUILD_PDF] ⚠️  Ошибка сборки PDF (rc={_result.returncode})")
                    print(_result.stderr[-500:] if _result.stderr else "(нет stderr)")
            else:
                print(f"[BUILD_PDF] Скрипт не найден: {build_script}")'''

src = src.replace(old_save_code, new_save_code)

# Проверяем что изменения применились
changes = {
    "DEFAULT_FACT_MAP → v5": 'test_fact_map_karakulina_v5.json' in src,
    "--use-existing-cover arg": 'use-existing-cover' in src,
    "validate_layout_output (pages[])": 'pages = response.get("pages", [])' in src,
    "_preloaded_portrait_bytes": '_preloaded_portrait_bytes' in src,
    "build_karakulina_pdf.py call": 'build_karakulina_pdf.py' in src,
}
for name, ok in changes.items():
    print(f"  {'✅' if ok else '❌'} {name}")

if all(changes.values()):
    SCRIPT.write_text(src, encoding="utf-8")
    print(f"\n[OK] test_stage4_karakulina.py обновлён ({len(src)} байт)")
else:
    print("\n[WARN] Не все изменения применились — проверьте вручную!")
    SCRIPT.write_text(src, encoding="utf-8")  # всё равно сохраняем
