"""
Читает чистый layout-код, патчит и сохраняет готовый к запуску файл.
"""
from pathlib import Path
import re

src = Path('exports/karakulina_iter3_layout_code_20260330_105105.py')
code = src.read_text(encoding='utf-8')

# 1. Фикс импорта pt
code = code.replace(
    'from reportlab.lib.units import mm, pt',
    'from reportlab.lib.units import mm\npt = 1'
)

# 2. Вставляем хелпер _safe_add_style после блока импортов
helper = (
    '\n\ndef _safe_add_style(ss, style):\n'
    '    try:\n        ss.add(style)\n'
    '    except KeyError:\n        pass\n\n'
)
# Ищем конец блока импортов (первая строка не начинающаяся с import/from)
lines = code.split('\n')
insert_at = 0
for i, ln in enumerate(lines):
    if ln.startswith('import ') or ln.startswith('from '):
        insert_at = i + 1
lines.insert(insert_at, helper)
code = '\n'.join(lines)

# 3. Заменяем styles.add(ParagraphStyle( → _safe_add_style(styles, ParagraphStyle(
code = code.replace('styles.add(ParagraphStyle(', '_safe_add_style(styles, ParagraphStyle(')

dst = Path('exports/karakulina_layout_ready.py')
dst.write_text(code, encoding='utf-8')
print(f'Сохранён: {dst}')

# Проверяем синтаксис
import py_compile, sys
try:
    py_compile.compile(str(dst), doraise=True)
    print('Синтаксис OK')
except py_compile.PyCompileError as e:
    print(f'Синтаксическая ошибка: {e}')
    sys.exit(1)
