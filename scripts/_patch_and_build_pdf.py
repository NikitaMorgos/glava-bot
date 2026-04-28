"""
Патчит сгенерированный layout-код и запускает сборку PDF.
"""
import sys, os, re
from pathlib import Path

os.chdir('/opt/glava')
src = Path('exports/karakulina_iter3_layout_code_20260330_105105.py')
code = src.read_text(encoding='utf-8')

# 1. Фикс импорта pt
code = code.replace(
    'from reportlab.lib.units import mm, pt',
    'from reportlab.lib.units import mm\npt = 1'
)

# 2. Фикс styles.add — заменяем на безопасную версию через try/except
# Паттерн: styles.add(ParagraphStyle(...)) может быть многострочным
# Проще: добавить хелпер в начало и заменить вызовы
helper = '''
def _safe_add_style(styles, style):
    try:
        styles.add(style)
    except KeyError:
        pass  # стиль уже есть, пропускаем

'''
# Вставляем хелпер после первого import
first_import_end = code.find('\n', code.find('import')) + 1
code = code[:first_import_end] + helper + code[first_import_end:]

# Заменяем styles.add( на _safe_add_style(styles,
code = code.replace('styles.add(ParagraphStyle(', '_safe_add_style(styles, ParagraphStyle(')
# Убираем лишние закрывающие скобки (было: styles.add(X) -> _safe_add_style(styles, X))
# Ничего убирать не нужно — ParagraphStyle(...) будет аргументом

dst = Path('/tmp/karakulina_layout_patched.py')
dst.write_text(code, encoding='utf-8')
print(f"Патч применён: {dst}")

# Запускаем
import subprocess
result = subprocess.run(
    ['/opt/glava/.venv/bin/python', str(dst)],
    capture_output=True, text=True, cwd='/opt/glava'
)
if result.stdout:
    print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr[-2000:])
print("Exit code:", result.returncode)
