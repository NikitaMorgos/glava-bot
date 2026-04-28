"""Add 'integrity' and 'photos' issues to appropriate categories."""
with open('/opt/glava/scripts/test_stage4_karakulina.py', 'r', encoding='utf-8') as f:
    src = f.read()

OLD = '''BUILDER_ISSUES = {
    "pagination", "toc_page_numbers", "font_not_embedded", "font_rendering",
    "margin_overflow", "orphan_widow", "photo_not_loaded", "headers_footers",
    "toc", "page_numbers",
}'''

NEW = '''BUILDER_ISSUES = {
    "pagination", "toc_page_numbers", "font_not_embedded", "font_rendering",
    "margin_overflow", "orphan_widow", "photo_not_loaded", "headers_footers",
    "toc", "page_numbers",
    "integrity",  # e.g. PDF too few pages vs page_map
}'''

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    print("BUILDER_ISSUES patch OK")
else:
    print("ERROR: pattern not found!")

# Also improve heuristic: add "integrity", "страниц" keywords
OLD_HEU = '''    for kw in ("шрифт", "font", "номер", "numer", "paginat", "toc", "оглавлени",
               "колонтитул", "header", "footer", "margin", "поле"):'''
NEW_HEU = '''    for kw in ("шрифт", "font", "номер", "numer", "paginat", "toc", "оглавлени",
               "колонтитул", "header", "footer", "margin", "поле",
               "страниц", "integrity", "placeholder"):'''

if OLD_HEU in src:
    src = src.replace(OLD_HEU, NEW_HEU, 1)
    print("Heuristic patch OK")
else:
    print("ERROR: heuristic pattern not found!")

with open('/opt/glava/scripts/test_stage4_karakulina.py', 'w', encoding='utf-8') as f:
    f.write(src)

import subprocess
r = subprocess.run(['python3', '-m', 'py_compile',
                   '/opt/glava/scripts/test_stage4_karakulina.py'],
                  capture_output=True, text=True)
print("Syntax:", "OK" if r.returncode == 0 else r.stderr)
