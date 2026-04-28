"""
Минимальный патч: передаём styles как параметр в add_photo.
"""
import os, subprocess
from pathlib import Path

os.chdir('/opt/glava')
code = Path('/tmp/karakulina_builtin_fonts.py').read_text(encoding='utf-8')

# 1. Подпись функции: добавляем параметр styles=None
code = code.replace(
    'def add_photo(story, photo_id, layout, caption, width_mm=None):\n',
    'def add_photo(story, photo_id, layout, caption, width_mm=None, _styles=None):\n'
    '    if _styles is None:\n'
    '        from reportlab.lib.styles import getSampleStyleSheet\n'
    '        _styles = getSampleStyleSheet()\n'
)

# 2. Внутри add_photo заменяем styles[ на _styles[
# Находим тело функции и правим в нём
import re
def replace_in_func(code, func_name, old, new):
    """Replace 'old' with 'new' only inside the named function body."""
    pattern = rf'(def {re.escape(func_name)}\(.*?(?=\ndef |\Z))'
    m = re.search(pattern, code, flags=re.DOTALL)
    if m:
        body = m.group(1).replace(old, new)
        code = code[:m.start()] + body + code[m.end():]
    return code

code = replace_in_func(code, 'add_photo', "styles['Caption']", "_styles['Caption']")
code = replace_in_func(code, 'add_photo', 'styles["Caption"]', '_styles["Caption"]')

# 3. В create_book: передаём styles во все вызовы add_photo
code = re.sub(
    r'add_photo\(story,\s*([^)]+)\)',
    lambda m: f"add_photo(story, {m.group(1)}, _styles=styles)",
    code
)

dst = Path('/tmp/karakulina_final2.py')
dst.write_text(code, encoding='utf-8')

import py_compile, sys
try:
    py_compile.compile(str(dst), doraise=True)
    print('Синтаксис OK')
except py_compile.PyCompileError as e:
    print(f'Ошибка: {e}'); sys.exit(1)

print('Строю PDF...')
result = subprocess.run(
    ['/opt/glava/.venv/bin/python', str(dst)],
    capture_output=True, text=True, cwd='/opt/glava'
)
print(result.stdout)
if result.returncode != 0:
    print("STDERR:", result.stderr[-2000:])
print("Exit:", result.returncode)

if result.returncode == 0:
    import glob
    for p in sorted(glob.glob('/opt/glava/*.pdf') + glob.glob('/opt/glava/exports/*.pdf')):
        if 'AGENTS' not in p and 'ИНСТРУКЦИЯ' not in p:
            print(f'  PDF создан: {p} ({os.path.getsize(p)//1024} KB)')
